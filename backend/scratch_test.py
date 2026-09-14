import asyncio
from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv

load_dotenv()

llm = ChatOpenAI(model='google/gemini-2.5-flash', api_key=os.environ['GOOGLE_API_KEY'], base_url='https://openrouter.ai/api/v1', max_tokens=200)

_REFORMULATE_PROMPT = '''\
Given a chat history and the latest user question, formulate a standalone question that can be understood without the chat history.
Do NOT answer the question, just reformulate it if needed.
If the question is already clear, return it exactly as is.

Chat History:
User: find labs for LED in mumbai
Assistant: No BIS-recognized labs found for 'led' in 'Mumbai'.

Latest Question: find labs for dahi in mumbai

Standalone Question:'''

async def main():
    resp = await llm.ainvoke(_REFORMULATE_PROMPT)
    print('Reformulated:', resp.content)

asyncio.run(main())
