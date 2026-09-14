import asyncio
import os
from dotenv import load_dotenv

load_dotenv()
from app.services.rag_service import RAGService

async def main():
    rag = RAGService.from_env()
    res = await rag.query("tell me about gold")
    print(f"Retrieved {len(res.retrieved_chunks)} chunks")
    for chunk in res.retrieved_chunks:
        print(f"Score: {chunk.get('score')} | Keys: {chunk.keys()}")
        print(f"Content length: {len(str(chunk.get('content')))}")
    
    print("\nAnswer:", res.answer)

if __name__ == "__main__":
    asyncio.run(main())
