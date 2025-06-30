import requests

class VirtualMicroClient:
    def __init__(self, host: str):
        # Приклад: http://127.0.0.1:5000
        self.host = host.rstrip('/')

    def play(self, audio_paths: list[str]) -> dict:
        """
        Надсилає список шляхів до WAV для відтворення.
        Повертає JSON-відповідь сервера.
        """
        url = f"{self.host}/api/play"
        resp = requests.post(url, json={"audio": audio_paths})
        resp.raise_for_status()
        return resp.json()

    def clear(self) -> dict:
        """
        Очищує чергу відтворення.
        """
        url = f"{self.host}/api/clear"
        resp = requests.post(url)
        resp.raise_for_status()
        return resp.json()

    def status(self) -> dict:
        """
        Повертає поточний статус: чи грає зараз щось і розмір черги.
        """
        url = f"{self.host}/api/status"
        resp = requests.get(url)
        resp.raise_for_status()
        return resp.json()
