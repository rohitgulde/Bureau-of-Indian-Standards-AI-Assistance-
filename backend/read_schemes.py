import sys; sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from app.database.session import SessionLocal
from app.models.db_models import CertificationScheme

db = SessionLocal()
schemes = db.query(CertificationScheme).all()
for s in schemes:
    products = (s.applicable_products or "")[:100]
    print(f"{s.scheme_code} | {s.scheme_name}")
    print(f"  Audience: {s.target_audience}  Type: {s.mandatory_or_voluntary}")
    print(f"  Products: {products}")
    print(f"  TAT: {s.standard_turnaround_time}")
    print()
db.close()
print(f"Total schemes: {len(schemes)}")
