from app.services.vector_service import get_vector_service
from google import genai
import os
from dotenv import load_dotenv

load_dotenv()
client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
emb = client.models.embed_content(
    model="models/gemini-embedding-001",
    contents="tell me about gold",
    config={"task_type": "RETRIEVAL_QUERY", "output_dimensionality": 768}
)

v = get_vector_service()
chunks = v.search(emb.embeddings[0].values, top_k=3, score_threshold=0.1)
print(f"Retrieved {len(chunks)} chunks")
for i, c in enumerate(chunks):
    print(f"--- Chunk {i} ---")
    for k, v in c.items():
        if k == 'content':
            print(f"{k}: {str(v)[:100]}")
        else:
            print(f"{k}: {v}")
