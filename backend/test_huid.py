import requests
import json

try:
    data = {"question": "How do I verify gold?"}
    res = requests.post("http://localhost:8000/api/chat/", json=data)
    print("--- Verify Gold ---")
    print(json.dumps(res.json(), indent=2))

    data = {"question": "Can you check AB1234?"}
    res = requests.post("http://localhost:8000/api/chat/", json=data)
    print("\n--- Check AB1234 ---")
    print(json.dumps(res.json(), indent=2))

    data = {"question": "Is XX9999 valid?"}
    res = requests.post("http://localhost:8000/api/chat/", json=data)
    print("\n--- Check XX9999 ---")
    print(json.dumps(res.json(), indent=2))
except Exception as e:
    print(e)
