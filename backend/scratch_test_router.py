import asyncio
from app.services.query_router import _classify_keywords, _classify_llm
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

load_dotenv()

async def main():
    queries = [
        "What are the guidelines for IS 13252?",
        "Provide Scheme Guidance for IS 13252",
        "Guidelines for IS 14585",
        "guidelines for this products",
    ]
    llm = ChatOpenAI(model="google/gemini-1.5-flash-8b", temperature=0)

    for q in queries:
        print("Query:", q)
        intent, conf = _classify_keywords(q)
        print("  Keyword Intent:", intent.name)
        if intent.name == "AMBIGUOUS":
            llm_intent, llm_conf = await _classify_llm(q, llm)
            print("  LLM Intent:", llm_intent.name)
        print("-" * 40)

asyncio.run(main())
