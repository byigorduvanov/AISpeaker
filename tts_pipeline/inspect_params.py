# inspect_params.py
from gradio_client import Client

client = Client("http://127.0.0.1:8010/")

print("Available endpoints (fn_index → api_name):")
for idx, ep in client.endpoints.items():
    # ep.api_name містить строку виду "/generate_audio"
    print(f"  {idx:2} → {ep.api_name}")
