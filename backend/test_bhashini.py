import asyncio
from app.services.bhashini_service import BhashiniService

async def main():
    b = BhashiniService.from_env()
    fwd = await b.full_pipeline("tell me about dahi")
    print("Detected:", fwd.detected_lang)
    print("English text:", fwd.english_text)

asyncio.run(main())
