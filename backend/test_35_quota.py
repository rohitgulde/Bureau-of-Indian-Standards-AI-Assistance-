from google import genai
import os
from dotenv import load_dotenv

load_dotenv()
client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])

print("Testing gemini-3.5-flash")
try:
    response = client.models.generate_content(
        model="gemini-3.5-flash",
        contents='Hi'
    )
    print("SUCCESS! Output:", response.text)
except Exception as e:
    print("ERROR:", str(e))
