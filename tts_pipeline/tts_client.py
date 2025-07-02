# tts_client.py

import os
import re
import shutil
from pathlib import Path
from gradio_client import Client
from pydub import AudioSegment

def split_into_subtitles(text: str) -> list[str]:
    """
    Розбиває текст на сегменти за допомогою розділення тільки по кінцю речення:
    крапка (.), знак оклику (!) або питання (?). Зап’яптую та інші знаки ігнорує.
    """
    # 1) Переводимо \n в пробіли, прибираємо зайві пробіли на початку/кінці
    norm = text.replace('\n', ' ').strip()
    # 2) Ділити тільки після ., ! або ? та наступних пробілів
    parts = re.split(r'(?<=[\.!\?])\s+', norm)
    # 3) Обрізати і відкинути пусті рядки
    return [p.strip() for p in parts if p.strip()]




class TTSClient:
    """
    Клієнт для звернення до Gradio-TTS-сервісу.
    Забезпечує:
      - перемикання моделі
      - генерацію одного сегмента в WAV
      - розбивку великого тексту на чанки та їх поетапну генерацію
    """

    def __init__(self, host, model, speaker, language, speed):
        # Ініціалізуємо HTTP-клієнт Gradio
        self.client = Client(host)

        # Одноразове переключення на потрібну модель TTS (fn_index=16 — endpoint /reload_model)
        self.client.predict(fn_index=16, model=model)

        # Після цього для генерації використовуємо fn_index=0 (/generate_audio)
        self.fn_index = 0

        # Значення за замовчуванням, які передаватимемо в кожному запиті
        self.defaults = {
            'languages': language,             # мова озвучки
            'speaker_value_text': speaker,     # обраний голос
            'speed': speed,                    # швидкість відтворення
            'output_type': 'wav',              # формат вихідного аудіо
            # Порожні значення для batch-режимів (не використовуються тут)
            'batch_generation': [],
            'batch_generation_path': '',
            'ref_speakers': '',
            'batch_sub_generation': [],
            'batch_sub_generation_path': '',
            # Налаштування для RVC (якщо не використовуємо — залишаться дефолтні)
            'rvc_settings_model_name': None,
            'rvc_settings_model_path': '',
            'rvc_settings_index_path': '',
        }

    def _call_generate(self, text, out_path, **overrides):
        """
        Генерує один WAV-файл для заданого шматка text і зберігає його в out_path.
        overrides — додаткові параметри (наприклад, для fine-tuning).
        Повертає шлях до створеного файлу.
        """
        # 1) Формуємо аргументи запиту
        args = {'text': text}
        args.update(self.defaults)    # додаємо значення за замовчуванням
        args.update(overrides)        # накладаємо можливі перезаписи

        # 2) Викликаємо Gradio TTS (fn_index=0)
        result = self.client.predict(fn_index=self.fn_index, **args)

        # 3) У відповіді result[1] — шлях до тимчасового WAV, який створив Gradio
        audio_path = result[1]

        # 4) Створюємо директорію під out_path, якщо її немає
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)

        # 5) Копіюємо з тимчасового місця в потрібний файл out_path
        shutil.copy2(audio_path, out_path)
        return out_path

    def generate_subtitle_chunks(
        self,
        text: str,
        out_dir: str = "chunks",
        prefix: str = "chunk",
        **overrides
    ) -> list[str]:
        """
        Розбиває текст на сегменти (split_into_subtitles), потім для кожного сегмента
        викликає _call_generate і зберігає файл у out_dir/prefix_XXX.wav.
        Друкує прогрес у консоль та повертає список шляхів до всіх згенерованих файлів.
        """
        # 1) Розбиваємо текст
        segments = split_into_subtitles(text)
        total = len(segments)
        out_paths = []

        # 2) Генеруємо кожен сегмент окремим WAV
        for idx, seg in enumerate(segments, start=1):
            # формуємо ім’я chunk_000.wav, chunk_001.wav тощо
            fname = f"{prefix}_{idx-1:03d}.wav"
            full_path = os.path.join(out_dir, fname)

            # викликаємо приватний метод для генерації
            self._call_generate(seg, full_path, **overrides)

            # виводимо статус
            print(f"Файл {idx}/{total} створено: {full_path}")

            out_paths.append(full_path)

        return out_paths
