from google import genai
from google.genai import types
import os
from dotenv import load_dotenv

load_dotenv()
client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])

for model_name in ["models/gemini-embedding-001", "models/gemini-embedding-2"]:
    try:
        response = client.models.embed_content(
            model=model_name,
            contents=["Hello", "World"],
            config=types.EmbedContentConfig(output_dimensionality=768)
        )
        print(f"{model_name} returned {len(response.embeddings)} embeddings")
    except Exception as e:
        print(f"Error for {model_name}: {e}")
