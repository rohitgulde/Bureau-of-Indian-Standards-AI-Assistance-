import asyncio
from app.services.query_router import _classify_llm, ChatGoogleGenerativeAI
from dotenv import load_dotenv
import os

load_dotenv()
api_key = os.environ.get("GOOGLE_API_KEY")
model_name = os.environ.get("GEMINI_MODEL", "gemini-3.6-flash")
llm = ChatGoogleGenerativeAI(model=model_name, google_api_key=api_key, temperature=0.0)

async def main():
    intent, conf = await _classify_llm("tell me about dahi", llm)
    print(f"Result: {intent.name}, Confidence: {conf}")

asyncio.run(main())
