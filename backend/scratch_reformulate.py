import asyncio
import os
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

load_dotenv()

async def main():
    llm = ChatGoogleGenerativeAI(model='gemini-1.5-flash', temperature=0.0)
    prompt = """\
Given a chat history and the latest user question, formulate a standalone question that can be understood without the chat history.
Do NOT answer the question, just reformulate it if needed.
If the question is already clear, return it exactly as is.

Chat History:
User: Find labs for cement
Assistant: To find a testing laboratory, please tell me the product you want to test and your State or City.

Latest Question: delhi

Standalone Question:"""
    resp = await llm.ainvoke(prompt)
    print(resp.content)

asyncio.run(main())
