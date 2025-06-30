from request import get_voice
import asyncio
import os
import pygame
from typing import List
import time

class AudioPlayer:
    def __init__(self):
        pygame.init()
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)
        self._stop_playback = False
        self._current_playing = None
        self.volume = 0.5

    async def play_files(self, file_paths: List[str]):
        """Play audio files without locking them"""
        self._stop_playback = False
        
        for file_path in file_paths:
            if self._stop_playback:
                break
                
            print(f"Waiting for: {os.path.basename(file_path)}")
            
            # Ожидание файла без блокировки
            waited = 0
            while not self._file_available(file_path) and not self._stop_playback:
                await asyncio.sleep(0.1)  # Проверяем каждые 100мс
                waited += 0.1
                if waited > 30:  # Таймаут 30 секунд
                    print(f"Timeout waiting for {os.path.basename(file_path)}")
                    break
                    
            if self._stop_playback or not self._file_available(file_path):
                continue
                
            try:
                self._current_playing = file_path
                print(f"Playing: {os.path.basename(file_path)}")
                
                # Быстрая загрузка и воспроизведение без блокировки
                pygame.mixer.music.load(file_path)
                pygame.mixer.music.set_volume(self.volume)
                pygame.mixer.music.play()
                
                # Ожидание окончания
                while pygame.mixer.music.get_busy() and not self._stop_playback:
                    await asyncio.sleep(0.05)
                    
            except Exception as e:
                print(f"Error playing {os.path.basename(file_path)}: {str(e)}")
            finally:
                self._current_playing = None
                
        pygame.mixer.music.stop()
        print("Playback finished" if not self._stop_playback else "Playback stopped")

    def _file_available(self, file_path: str) -> bool:
        """Проверка доступности файла без блокировки"""
        try:
            # Просто проверка существования и размера без открытия файла
            return os.path.exists(file_path) and os.path.getsize(file_path) > 0
        except:
            return False

    def stop_playback(self):
        """Остановка воспроизведения"""
        self._stop_playback = True
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()

async def main():
    req = input("Input file path or command: ")
    res = await get_voice(req)
    
    if res and len(res) > 3 and isinstance(res[3], list):
        file_list = [f for f in res[3] if isinstance(f, str) and f.endswith('.mp3')]
        print(f"Found {len(file_list)} audio files")
        
        player = AudioPlayer()
        playback_task = asyncio.create_task(player.play_files(file_list))
        
        # Для остановки по таймауту:
        # await asyncio.sleep(10)
        # player.stop_playback()
        
        await playback_task
    else:
        print("No valid audio files found")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nPlayback interrupted")
    finally:
        pygame.mixer.quit()
        pygame.quit()