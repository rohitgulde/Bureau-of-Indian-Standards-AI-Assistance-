import requests
import json

try:
    data = {"question": "Hello, how are you?"}
    res = requests.post("http://localhost:8000/api/chat/", json=data)
    print("--- Hello ---")
    print(json.dumps(res.json(), indent=2))

    data = {"question": "I bought gold jewelry"}
    res = requests.post("http://localhost:8000/api/chat/", json=data)
    print("\n--- Gold Jewelry ---")
    print(json.dumps(res.json(), indent=2))
except Exception as e:
    print(e)
