from google import genai
import os
from dotenv import load_dotenv

load_dotenv()
client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
print("Testing gemini-3.5-flash")
try:
    response = client.models.generate_content(
        model='gemini-3.5-flash',
        contents='Tell me a joke.'
    )
    print(response.text)
except Exception as e:
    print(e)
