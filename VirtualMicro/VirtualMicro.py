import numpy as np
import queue
import threading
import time
from flask import Flask, request, jsonify
import io
from pydub import AudioSegment
import sounddevice as sd

app = Flask(__name__)

# Очередь для хранения аудиоданных
audio_queue = queue.Queue()
current_audio = None
stop_playback = False
playback_thread = None

# Конфигурация виртуального устройства (VB-CABLE требует именно эти параметры)
TARGET_CHANNELS = 2      # VB-CABLE работает только в стерео
TARGET_SAMPLERATE = 44100  # Стандартная частота дискретизации
TARGET_DTYPE = 'float32'  # Тип данных для sounddevice

def find_vb_cable_output():
    """Находим выходное устройство VB-CABLE"""
    devices = sd.query_devices()
    for i, dev in enumerate(devices):
        if "VB-Audio Virtual Cable" in dev['name'] and dev['max_output_channels'] >= TARGET_CHANNELS:
            return i
    raise RuntimeError("VB-CABLE выходное устройство не найдено или не поддерживает нужное количество каналов")

def find_vb_cable_output_device():
    """Находим выходное устройство VB-CABLE (CABLE Input)"""
    devices = sd.query_devices()
    for i, dev in enumerate(devices):
        if "CABLE Input" in dev['name'] and dev['max_output_channels'] >= TARGET_CHANNELS:
            return i
    raise RuntimeError("CABLE Input не найден или не поддерживает нужное количество выходных каналов")

vb_cable_id = find_vb_cable_output_device()
print(f"Используем виртуальное устройство с ID: {vb_cable_id}")

def audio_playback_worker():
    global current_audio, stop_playback
    
    while True:
        if not audio_queue.empty() and current_audio is None:
            path = audio_queue.get()


            stop_playback = False
            
            try:
                with open(path, 'rb') as audio_file:
                    audio_data = audio_file.read()
                    format = path.split('.')[-1].lower()
                    current_audio = convert_audio_file(audio_data, format)

                print(f"Начинаем воспроизведение: {len(current_audio)} samples")
                
                with sd.OutputStream(
                    device=vb_cable_id,
                    channels=TARGET_CHANNELS,
                    samplerate=TARGET_SAMPLERATE,
                    dtype=TARGET_DTYPE
                ) as stream:
                    blocksize = 4096
                    for i in range(0, len(current_audio), blocksize):
                        block = current_audio[i:i+blocksize]
                        stream.write(block)
                        time.sleep(round(blocksize / TARGET_SAMPLERATE))
            except Exception as e:
                print(f"Ошибка воспроизведения: {str(e)}")
                requeue_at_front(audio_queue, path)
                time.sleep(0.1)
            finally:
                current_audio = None
                print("Воспроизведение завершено")
        else:
            time.sleep(0.01)

def requeue_at_front(queue, item):
    items = []
    while not queue.empty():
        items.append(queue.get())
    queue.put(item)  # Кладем наш элемент первым
    for existing_item in items:
        queue.put(existing_item)  # Возвращаем остальные элементы

def convert_audio_file(audio_data, format='wav'):
    """Конвертирует аудио в совместимый формат для VB-CABLE"""
    audio = AudioSegment.from_file(io.BytesIO(audio_data), format=format)
    
    # Приводим к нужным параметрам
    audio = audio.set_frame_rate(TARGET_SAMPLERATE)
    audio = audio.set_channels(TARGET_CHANNELS)
    
    # Конвертируем в numpy array
    samples = np.array(audio.get_array_of_samples())
    
    # Нормализация для разных битностей
    if audio.sample_width == 1:  # 8-bit
        samples = samples.astype(np.float32) / 128.0 - 1.0
    elif audio.sample_width == 2:  # 16-bit
        samples = samples.astype(np.float32) / 32768.0
    elif audio.sample_width == 3:  # 24-bit
        samples = samples.astype(np.float32) / 8388608.0
    elif audio.sample_width == 4:  # 32-bit
        samples = samples.astype(np.float32) / 2147483648.0
    
    # Решейпим в (N, 2) для стерео
    return samples.reshape(-1, TARGET_CHANNELS)

@app.route('/api/play', methods=['POST'])
def play_audio():
    """Добавить аудио в очередь воспроизведения"""
    if not request.json or 'audio' not in request.json:
        return jsonify({"error": "Необходимо передать JSON с массивом путей к аудиофайлам"}), 400
    
    try:
        audio_paths = request.json['audio']
        
        if not isinstance(audio_paths, list):
            return jsonify({"error": "Параметр 'audio' должен быть массивом"}), 400
            
        for path in audio_paths:
            audio_queue.put(path)

        return jsonify({
            "status": "success",
            "queue_size": audio_queue.qsize(),
            "added_files": audio_paths
        })
    except Exception as e:
        print(f"Серверная ошибка: {str(e)}")
        return jsonify({"error": f"Серверная ошибка: {str(e)}"}), 500

@app.route('/api/clear', methods=['POST'])
def clear_queue():
    """Очистить очередь воспроизведения"""
    global audio_queue
    
    with audio_queue.mutex:
        audio_queue.queue.clear()
    
    return jsonify({"status": "queue cleared", "queue_size": 0})

@app.route('/api/status', methods=['GET'])
def get_status():
    """Получить статус воспроизведения"""
    return jsonify({
        "is_playing": current_audio is not None,
        "queue_size": audio_queue.qsize()
    })

def start_playback_thread():
    global playback_thread
    
    playback_thread = threading.Thread(target=audio_playback_worker)
    playback_thread.daemon = True
    playback_thread.start()

if __name__ == '__main__':
    # Проверка доступных устройств
    print("Доступные аудиоустройства:")
    for i, dev in enumerate(sd.query_devices()):
        print(f"{i}: {dev['name']} (in:{dev['max_input_channels']} out:{dev['max_output_channels']})")
    
    start_playback_thread()
    app.run(host='0.0.0.0', port=5000, debug=True)