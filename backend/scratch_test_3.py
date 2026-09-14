import asyncio
from app.services.query_router import QueryRouter
from app.api.endpoints import _reformulate_query, ConversationMessage
import os
from dotenv import load_dotenv

load_dotenv()

qr = QueryRouter.from_env()

history = [
    ConversationMessage(role='user', content='find labs for LED in mumbai'),
    ConversationMessage(role='assistant', content="No BIS-recognized labs found for 'led' in 'Mumbai'.")
]

async def main():
    q = await _reformulate_query('find labs for dahi in mumbai', history, qr)
    print('REFORMULATED QUERY:', q)
    
    # Let's also test _handle_lab_search with this query
    from app.services.lab_service import _handle_lab_search # Wait it's in query_router
    # actually let's just do classify
    classification = await qr.classify(q)
    print("CLASSIFIED:", classification)
    
    from app.services.query_router import _LAB_SEARCH_EXTRACTION_PROMPT
    prompt = _LAB_SEARCH_EXTRACTION_PROMPT.format(query=q)
    resp = await qr._classifier_llm.ainvoke(prompt)
    print("EXTRACTED:", resp.content)

asyncio.run(main())
