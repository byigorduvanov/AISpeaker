# service.py

import os
import shutil
import threading
import configparser
from typing import List
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from tts_client import split_into_subtitles, TTSClient
from virtualmicro_client import VirtualMicroClient


#  1) Зчитуємо налаштування з config.ini
cfg = configparser.ConfigParser()
cfg.read("config.ini", encoding="utf-8")
tts_cfg = cfg["tts"]              # розділ з параметрами TTS
vm_cfg  = cfg["virtualmicro"]     # розділ з параметрами VirtualMicro

#  Ініціалізуємо клієнта для TTS
tts = TTSClient(
    host=tts_cfg.get("host"),                # URL TTS-сервісу
    model=tts_cfg.get("model"),              # модель озвучки
    speaker=tts_cfg.get("speaker"),          # вибраний голос
    language=tts_cfg.get("language"),        # мова озвучки
    speed=tts_cfg.getfloat("speed"),         # швидкість відтворення
)
#  Ініціалізуємо клієнта для VirtualMicro
vm = VirtualMicroClient(vm_cfg.get("host"))  # URL VirtualMicro-сервера

#  2) Змінні для керування фоновим потоком генерації
worker_thread = None               # обʼєкт фонового потоку
cancel_event  = threading.Event()  # прапорець для зупинки потоку
lock          = threading.Lock()   # блокування під час перезапуску
OUT_DIR       = "out_chunks"       # папка для збережених чанків


# Опис моделей даних запитів/відповідей

class TtsRequest(BaseModel):
    """Вхідна модель для POST /api/tts"""
    text: str

class StatusResponse(BaseModel):
    """Модель відповіді для GET /api/status"""
    generating: bool  # чи триває генерація зараз
    queue_size: int   # скільки файлів у черзі VirtualMicro


app = FastAPI(title="TTS Chunked Service")

def cleanup_outdir():
    """
    Очищає папку OUT_DIR перед новою генерацією:
    видаляє старі чанки і створює чисту директорію.
    """
    if os.path.exists(OUT_DIR):
        shutil.rmtree(OUT_DIR)
    os.makedirs(OUT_DIR, exist_ok=True)

def generation_worker(text: str):
    """
    Фоновий воркер, який:
      1. Очищає папку чанків
      2. Розбиває текст на сегменти (subtitles)
      3. Для кожного сегмента генерує WAV через TTSClient
      4. Одразу відправляє створений файл до VirtualMicro
      5. Перевіряє cancel_event на відміну
    """
    cleanup_outdir()

    # Розбиваємо текст на сегменти за реченнями
    segments = split_into_subtitles(text)
    total = len(segments)

    for idx, seg in enumerate(segments, start=1):
        # якщо прийшла команда скасування — виходимо
        if cancel_event.is_set():
            print("🛑 Генерація відмінена")
            return

        # формуємо імʼя для чанка
        fname   = f"chunk_{idx-1:03d}.wav"
        outpath = os.path.join(OUT_DIR, fname)

        # генеруємо аудіо для цього сегмента
        tts._call_generate(seg, outpath)
        print(f"[{idx}/{total}] Згенеровано: {outpath}")

        # надсилаємо файл до VM для відтворення
        abs_path = os.path.abspath(outpath)
        resp = vm.play([abs_path])
        print(f"      → Відправлено у VM (черга={resp['queue_size']})")

    print("✅ Всі сегменти згенеровано й надіслано")


@app.post("/api/tts", summary="Запустити TTS-генерацію", response_model=dict)
def api_tts(req: TtsRequest):
    """
    Ендпоінт для запуску озвучки.
    Очікує JSON з полем `text`.
    При новому виклику:
      - відміняє поточний воркер (якщо є)
      - очищає чергу VirtualMicro
      - запускає нового воркера з новим текстом
    Повертає список кількість очікуваних чанків.
    """
    global worker_thread, cancel_event

    text = req.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Поле 'text' не може бути порожнім")

    with lock:
        # якщо вже триває генерація — скасовуємо її
        if worker_thread and worker_thread.is_alive():
            cancel_event.set()
            worker_thread.join()

        # очищуємо чергу VirtualMicro
        vm.clear()

        # скидаємо прапорець відміни
        cancel_event.clear()
        # створюємо й запускаємо новий фоновий потік
        worker_thread = threading.Thread(target=generation_worker, args=(text,))
        worker_thread.daemon = True
        worker_thread.start()

    # скільки сегментів буде згенеровано
    chunks_estimate = len(split_into_subtitles(text))
    return {"status": "started", "chunks_estimate": chunks_estimate}


@app.post("/api/clear", summary="Очистити генерацію та VM-чергу", response_model=dict)
def api_clear():
    """
    Ендпоінт для скасування поточної генерації й очищення
    черги відтворення у VirtualMicro.
    """
    global worker_thread, cancel_event

    with lock:
        # зупиняємо воркер, якщо він працює
        if worker_thread and worker_thread.is_alive():
            cancel_event.set()
            worker_thread.join()
        # очищуємо чергу σε VM
        vm.clear()

    return {"status": "cleared"}


@app.get("/api/status", summary="Статус генерації та VM-черги", response_model=StatusResponse)
def api_status():
    """
    Ендпоінт, що повертає поточний стан:
      - generating: чи ще генерується хоча б один чанок
      - queue_size: розмір черги у VirtualMicro
    """
    is_busy = bool(worker_thread and worker_thread.is_alive())
    vm_stat = vm.status()
    return StatusResponse(generating=is_busy, queue_size=vm_stat["queue_size"])


if __name__ == "__main__":
    import uvicorn
    print("Запускаємо FastAPI-сервіс на http://0.0.0.0:7000")
    # стартуємо Uvicorn з автоматичним релоудом
    uvicorn.run("service:app", host="0.0.0.0", port=7000, reload=True)
