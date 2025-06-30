# main.py

import configparser
import os
import shutil
from tts_client import split_into_subtitles, TTSClient
from virtualmicro_client import VirtualMicroClient

def main():
    # 1) Читаємо конфіг
    cfg = configparser.ConfigParser()
    cfg.read("config.ini", encoding="utf-8")
    tts_cfg = cfg["tts"]
    vm_cfg  = cfg["virtualmicro"]

    # 2) Ініціалізуємо TTS та VirtualMicro клієнти
    tts = TTSClient(
        host=tts_cfg.get("host"),
        model=tts_cfg.get("model"),
        speaker=tts_cfg.get("speaker"),
        language=tts_cfg.get("language"),
        speed=tts_cfg.getfloat("speed"),
    )
    vm = VirtualMicroClient(vm_cfg.get("host"))

    # 3) Запит шляху до текстового файлу
    path = input("Введи шлях до текстового файлу (.txt): ").strip()
    if not os.path.isfile(path):
        print(f"Файл не знайдено: {path}")
        return

    # 4) Читаємо увесь текст
    with open(path, encoding="utf-8") as f:
        text = f.read()

    # 5) Підготовка папки для вихідних WAV
    out_dir = "out_chunks"
    if os.path.exists(out_dir):
        shutil.rmtree(out_dir)
    os.makedirs(out_dir, exist_ok=True)

    # 6) Розбиваємо на сегменти та починаємо пайплайн
    segments = split_into_subtitles(text)
    total = len(segments)
    print(f"Найдено {total} сегментів. Починаємо генерацію та відтворення…\n")

    for idx, seg in enumerate(segments, start=1):
        # 6.1) Згенерувати WAV для поточного сегмента
        fname     = f"chunk_{idx-1:03d}.wav"
        full_path = os.path.join(out_dir, fname)
        tts._call_generate(seg, full_path)

        # 6.2) Вивести статус
        print(f"[{idx}/{total}] Згенеровано: {full_path}")

        # 6.3) Надіслати тільки-но створений файл в VirtualMicro
        abs_path = os.path.abspath(full_path)
        resp = vm.play([abs_path])
        print(f"      → Відправлено в VM: {abs_path}  (черга: {resp['queue_size']})\n")

    print("Усі сегменти згенеровані й надіслані в VirtualMicro.")

if __name__ == "__main__":
    main()
