import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from app.utils.pdf_parser import parse_is_document
from app.services.vector_service import get_vector_service
from google import genai
from google.genai import types as genai_types

async def main():
    api_key = os.getenv("GOOGLE_API_KEY", "")
    gemini_client = genai.Client(api_key=api_key)
    vector_svc = get_vector_service()

    pdf_dir = Path(r"c:\Users\rohit\OneDrive\Desktop\sih\backend\data\raw_pdfs")
    pdf_paths = [p for p in pdf_dir.glob("*.pdf")]

    for pdf_path in pdf_paths:
        print(f"Processing {pdf_path.name}...")
        chunks = parse_is_document(pdf_path)
        if not chunks:
            continue
            
        for chunk in chunks:
            chunk["source_file"] = pdf_path.name
            
        embed_texts = []
        for chunk in chunks:
            parts = []
            if chunk.get("standard_code"):
                parts.append(chunk["standard_code"])
            if chunk.get("clause_number") and chunk.get("clause_title"):
                parts.append(f"§ {chunk['clause_number']} {chunk['clause_title']}")
            elif chunk.get("clause_number"):
                parts.append(f"§ {chunk['clause_number']}")
            if chunk.get("content"):
                parts.append(chunk["content"])
            embed_texts.append("\n".join(parts))
            
        all_vectors = []
        batch_size = 50
        num_batches = (len(embed_texts) + batch_size - 1) // batch_size
        
        for batch_idx in range(num_batches):
            start = batch_idx * batch_size
            batch = embed_texts[start: start + batch_size]
            response = gemini_client.models.embed_content(
                model="gemini-embedding-2",
                contents=batch,
                config=genai_types.EmbedContentConfig(
                    task_type="RETRIEVAL_DOCUMENT",
                    output_dimensionality=768,
                ),
            )
            all_vectors.extend([emb.values for emb in response.embeddings])
            await asyncio.sleep(0.5)
            
        upserted = vector_svc.upsert_chunks(chunks, all_vectors)
        print(f"Upserted {upserted} chunks for {pdf_path.name}")

if __name__ == "__main__":
    asyncio.run(main())
