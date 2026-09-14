import re

with open("app/routers/ingest.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update stream_ingest imports
stream_imports_old = """    from google import genai
    from google.genai import types as genai_types
    from app.utils.pdf_parser import parse_is_document
    from app.services.vector_service import get_vector_service

    gemini_client = genai.Client(api_key=api_key)"""

stream_imports_new = """    from fastembed import TextEmbedding
    from app.utils.pdf_parser import parse_is_document
    from app.services.vector_service import get_vector_service

    embedding_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")"""

content = content.replace(stream_imports_old, stream_imports_new)

# 2. Update upload_and_ingest imports
upload_imports_old = """    from google import genai
    from google.genai import types as genai_types
    from app.utils.pdf_parser import parse_is_document
    from app.services.vector_service import get_vector_service

    gemini_client = genai.Client(api_key=api_key)"""

upload_imports_new = """    from fastembed import TextEmbedding
    from app.utils.pdf_parser import parse_is_document
    from app.services.vector_service import get_vector_service

    embedding_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")"""

content = content.replace(upload_imports_old, upload_imports_new)

# 3. Update stream_ingest loop
stream_loop_old = """            try:
                response = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda b=batch: gemini_client.models.embed_content(
                        model=EMBEDDING_MODEL,
                        contents=b,
                        config=genai_types.EmbedContentConfig(
                            task_type="RETRIEVAL_DOCUMENT",
                            output_dimensionality=768,
                        ),
                    ),
                )
                all_vectors.extend([emb.values for emb in response.embeddings])
            except Exception as exc:
                yield sse(f"   ⚠️  Embedding error on batch {batch_idx + 1}: {exc}")
                all_vectors.extend([[0.0] * 768] * len(batch))
            await asyncio.sleep(0.5)  # rate-limit"""

stream_loop_new = """            try:
                # FastEmbed runs synchronously and fast
                embeddings = list(embedding_model.embed(batch))
                all_vectors.extend([list(emb) for emb in embeddings])
            except Exception as exc:
                yield sse(f"   ⚠️  Embedding error on batch {batch_idx + 1}: {exc}")
                all_vectors.extend([[0.0] * 384] * len(batch))"""

content = content.replace(stream_loop_old, stream_loop_new)

# 4. Update upload_and_ingest loop
upload_loop_old = """            try:
                response = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda b=batch: gemini_client.models.embed_content(
                        model=EMBEDDING_MODEL,
                        contents=b,
                        config=genai_types.EmbedContentConfig(
                            task_type="RETRIEVAL_DOCUMENT",
                            output_dimensionality=768,
                        ),
                    ),
                )
                all_vectors.extend([emb.values for emb in response.embeddings])
            except Exception as exc:
                if "429" in str(exc) or "RESOURCE_EXHAUSTED" in str(exc):
                    logger.warning(f"Hit Google API 429 rate limit on batch {batch_idx+1}. Sleeping 60s before retry...")
                    await asyncio.sleep(60)
                    try:
                        response = await asyncio.get_event_loop().run_in_executor(
                            None,
                            lambda b=batch: gemini_client.models.embed_content(
                                model=EMBEDDING_MODEL,
                                contents=b,
                                config=genai_types.EmbedContentConfig(
                                    task_type="RETRIEVAL_DOCUMENT",
                                    output_dimensionality=768,
                                ),
                            ),
                        )
                        all_vectors.extend([emb.values for emb in response.embeddings])
                    except Exception as retry_exc:
                        return JSONResponse(status_code=500, content={"error": f"Embedding error (after 60s retry): {retry_exc}"})
                else:
                    return JSONResponse(status_code=500, content={"error": f"Embedding error: {exc}"})
            
            # Enforce strict <15 Requests Per Minute (RPM) to stay under Google Free Tier quota
            await asyncio.sleep(4.5)"""

upload_loop_new = """            try:
                embeddings = list(embedding_model.embed(batch))
                all_vectors.extend([list(emb) for emb in embeddings])
            except Exception as exc:
                return JSONResponse(status_code=500, content={"error": f"Embedding error: {exc}"})"""

content = content.replace(upload_loop_old, upload_loop_new)

with open("app/routers/ingest.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Ingest router successfully updated to use fastembed!")
