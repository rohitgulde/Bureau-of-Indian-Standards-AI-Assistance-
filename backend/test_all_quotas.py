from google import genai
import os
from dotenv import load_dotenv
import time

load_dotenv()
client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])

models_to_test = [
    "gemini-flash-latest",
    "gemini-flash-lite-latest",
    "gemini-2.5-flash-lite",
    "gemini-3.7-flash"
]

print("Testing quotas...")
for model in models_to_test:
    print(f"\n--- Testing {model} ---")
    try:
        response = client.models.generate_content(
            model=model,
            contents='Hi'
        )
        print("SUCCESS! Output:", response.text)
    except Exception as e:
        print("ERROR:", str(e))
    time.sleep(1)
