curl -X POST http://127.0.0.1:5000/api/play -H "Content-Type: application/json" -d "{\"audio\": [\"C:/Users/Povelitel/Downloads/Telegram Desktop/00_00_00_000-00_00_03_000_output_RAY.wav\", \"C:/Users/Povelitel/Downloads/Telegram Desktop/00_00_03_000-00_00_05_000_output_RAY.wav\", \"C:/Users/Povelitel/Downloads/Telegram Desktop/00_00_05_000-00_00_08_000_output_RAY.wav\"]}"
Передавать массив путей к аудио для воспроизведения

curl -X POST http://127.0.0.1:5000/api/clear
остановить

curl -X GET http://127.0.0.1:5000/api/status
Получить статус воспроизведения