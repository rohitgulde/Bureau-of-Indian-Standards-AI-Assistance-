import requests

res = requests.post(
    "http://127.0.0.1:8000/api/chat",
    json={"question": "tell me about gold", "stream": False, "history": []}
)
print("Status:", res.status_code)
import json
try:
    data = res.json()
    print("Answer:")
    print(data.get('answer', '')[:1000])
except Exception as e:
    print("Error parsing JSON:", e)
    print("Raw text:", res.text[:1000])
