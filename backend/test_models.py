from google import genai
import os
from dotenv import load_dotenv

load_dotenv()
client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
print("Listing embedding models:")
for m in client.models.list():
    if "embed" in ",".join(m.supported_actions).lower():
        print(m.name, m.supported_actions)
