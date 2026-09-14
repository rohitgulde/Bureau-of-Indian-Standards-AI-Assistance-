import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

# Check for OpenRouter API Key (either explicit or fallback to GOOGLE_API_KEY)
api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("GOOGLE_API_KEY")

if not api_key:
    print("X OPENROUTER_API_KEY is missing from your .env file!")
    exit(1)

model_name = os.getenv("GEMINI_MODEL", "google/gemini-2.5-flash")

print(f"Testing OpenRouter API with model: {model_name}...")
print(f"Using API Key: {api_key[:12]}...")

try:
    llm = ChatOpenAI(
        model=model_name,
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
        max_retries=1,
        max_tokens=2048
    )
    
    response = llm.invoke("Hi! Are you connected to OpenRouter? Reply with a short sentence.")
    print("SUCCESS! Connected to OpenRouter.")
    print(f"Response: {response.content}")
except Exception as e:
    print(f"ERROR: Failed to connect to OpenRouter.\nDetails: {str(e)}")
