import re

with open("app/services/rag_service.py", "r", encoding="utf-8") as f:
    content = f.read()

# Replace import
old_import = "from langchain_google_genai import ChatGoogleGenerativeAI"
new_import = "from langchain_openai import ChatOpenAI"
content = content.replace(old_import, new_import)

# Replace LLM instantiation
old_llm_init = """        self._llm = ChatGoogleGenerativeAI(
            model=self._model_name,
            google_api_key=api_key,
            temperature=temperature,
            # Safety: keep responses grounded; lower these if needed
            convert_system_message_to_human=False,
        )"""

new_llm_init = """        self._llm = ChatOpenAI(
            model=self._model_name,
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
            temperature=temperature,
        )"""
content = content.replace(old_llm_init, new_llm_init)

# Replace API key fetch logic if they put it in OPENROUTER_API_KEY
old_api_fetch = """        api_key = google_api_key or os.environ.get("GOOGLE_API_KEY", "")"""
new_api_fetch = """        api_key = google_api_key or os.environ.get("OPENROUTER_API_KEY", os.environ.get("GOOGLE_API_KEY", ""))"""
content = content.replace(old_api_fetch, new_api_fetch)

# Update model default
old_default = 'DEFAULT_MODEL_FLASH: str = "gemini-1.5-flash"'
new_default = 'DEFAULT_MODEL_FLASH: str = "google/gemini-2.5-flash"'  # OpenRouter uses google/gemini-2.5-flash or google/gemini-flash-1.5
content = content.replace(old_default, new_default)

with open("app/services/rag_service.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Updated rag_service.py for OpenRouter successfully!")
