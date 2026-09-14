import re

with open("app/services/rag_service.py", "r", encoding="utf-8") as f:
    content = f.read()

# Remove GoogleGenerativeAIEmbeddings and add fastembed
content = content.replace("from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings", "from langchain_google_genai import ChatGoogleGenerativeAI\nfrom fastembed import TextEmbedding")

# Remove EMBEDDING_MODEL constant
content = content.replace('EMBEDDING_MODEL:     str = "models/gemini-embedding-001"', 'EMBEDDING_MODEL:     str = "BAAI/bge-small-en-v1.5"')

# Replace embedding instantiation
old_embed_init = """        self._embeddings = GoogleGenerativeAIEmbeddings(
            model=EMBEDDING_MODEL,
            google_api_key=api_key,
            task_type="retrieval_query",
            output_dimensionality=768,
        )"""
new_embed_init = """        self._embeddings = TextEmbedding(model_name=EMBEDDING_MODEL)"""
content = content.replace(old_embed_init, new_embed_init)

# Replace embed_query call
old_embed_call = """        query_vector: list[float] = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self._embeddings.embed_query(question),
        )"""
new_embed_call = """        query_vector: list[float] = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: list(next(self._embeddings.embed([question]))),
        )"""
content = content.replace(old_embed_call, new_embed_call)

with open("app/services/rag_service.py", "w", encoding="utf-8") as f:
    f.write(content)

print("rag_service updated successfully")
