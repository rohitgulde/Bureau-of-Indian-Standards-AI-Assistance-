import sys
sys.path.append(r"C:\Users\rohit\OneDrive\Desktop\sih\backend")
from app.database.session import SessionLocal
from app.models.db_models import ConsumerFAQ
import re

db = SessionLocal()
faqs = db.query(ConsumerFAQ).filter(ConsumerFAQ.is_published == True).all()

query = "The jewellery I bought is hallmarked 22K (916) but an independent assay shows it is only 18K. What are my rights?"
tokens = set(re.findall(r"\b\w{3,}\b", query.lower()))
stop_words = {"the", "and", "for", "that", "this", "with", "from", "your", "what", "how", "are", "but", "only"}
tokens = tokens - stop_words
print("Tokens:", tokens)

def _faq_score(f):
    haystack = " ".join([
        (f.topic or ""), (f.keywords or ""),
        (f.question or ""), (f.category or ""),
    ]).lower()
    return sum(1 for t in tokens if t in haystack)

for f in sorted(faqs, key=_faq_score, reverse=True):
    print(f"ID: {f.id}, Score: {_faq_score(f)}, Topic: {f.topic}")

db.close()
