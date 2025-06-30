@echo off
REM Використовуємо власну тимчасову теку
SET TEMP=temp

REM Активуємо вірт. оточення (Windows-шлях до activate.bat)
call venv\Scripts\activate.bat

REM Запускаємо TTS-сервер на всіх інтерфейсах порту 8010 і даємо опцію шарингу
python app.py --deepspeed --rvc --host 0.0.0.0 --port 8010 --share

pause
