import asyncio
from dotenv import load_dotenv
load_dotenv()
from app.services.rag_service import RAGService
from app.services.vector_service import get_vector_service

async def test_search():
    vs = get_vector_service()
    rag = RAGService(vector_service=vs)
    query = "what are the standard of electrical food mixture"
    augmented = (
        f"Which Indian Standard (IS) code applies to the following product or use-case? "
        f"List the standard number, its title, and key clauses. Query: {query}"
    )
    
    # Let's test the embedding directly
    print(f"Query: {augmented}")
    
    # Call rag
    resp = await rag.query(augmented)
    print("\n--- Answer ---")
    print(resp.answer)
    
    print("\n--- Retrieved Chunks ---")
    print(f"Total retrieved: {len(resp.retrieved_chunks)}")
    for i, chunk in enumerate(resp.retrieved_chunks):
        print(f"[{i}] Score: {chunk.get('score', 'N/A')}")
        print(f"    Source: {chunk.get('source_file')}")
        print(f"    Content snippet: {chunk.get('content', '')[:100]}...")

if __name__ == "__main__":
    asyncio.run(test_search())
