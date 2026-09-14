import requests
import json

data = {
    "question": "maharashtra",
    "history": [
        {"role": "user", "content": "Lab locations for product testing"},
        {"role": "assistant", "content": "To find a testing laboratory, please tell me the product you want to test and your State or City."}
    ],
    "stream": False
}
res = requests.post("http://localhost:8000/api/chat", json=data)
print(json.dumps(res.json(), indent=2))
