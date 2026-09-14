import asyncio
from app.services.query_router import QueryRouter
import json

async def main():
    router = QueryRouter.from_env()
    for q in ["what is bis?", "how are you?", "random query", "what is hallmark?"]:
        res = await router.classify(q)
        print(f"'{q}' -> {res.intent.value} ({res.stage})")

if __name__ == "__main__":
    asyncio.run(main())
