import asyncio
from langchain_openai import ChatOpenAI
import os
import json
from dotenv import load_dotenv

load_dotenv()

llm = ChatOpenAI(model='google/gemini-2.5-flash', api_key=os.environ['GOOGLE_API_KEY'], base_url='https://openrouter.ai/api/v1', max_tokens=200)

_LAB_SEARCH_EXTRACTION_PROMPT = """\
Extract the city/state and the specific product/material from the following query to search a laboratory database.
CRITICAL INSTRUCTIONS:
1. NORMALIZE the city or state name to its standard spelling (e.g., "tamilnadu" -> "Tamil Nadu", "delhi" -> "Delhi").
2. If a field is not mentioned, use actual JSON null (not the string "NULL").
Return a valid JSON object ONLY: {{"city": "City or State Name", "product": "Product Name"}}

Query: "{query}"
"""

async def main():
    prompt = _LAB_SEARCH_EXTRACTION_PROMPT.format(query="find labs for dahi in mumbai")
    resp = await llm.ainvoke(prompt)
    print('Extracted:', resp.content)

asyncio.run(main())
