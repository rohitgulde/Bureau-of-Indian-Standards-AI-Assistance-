import sys
from pathlib import Path
from datetime import datetime, timedelta

backend_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_dir))

from app.database.session import SessionLocal
from app.models.db_models import HuidRecord

db = SessionLocal()
record = HuidRecord(
    huid="2JP8FC",
    jeweller_name="Joyalukkas India Ltd",
    jeweller_reg_no="BIS/J/492934",
    ahc_name="Kochi Assaying Center",
    ahc_location="Ernakulam, Kerala",
    article_type="Gold Bangle",
    purity_karat="22K",
    purity_fineness="916",
    hallmarking_date=datetime.now() - timedelta(days=2),
    status="Active"
)
db.add(record)
db.commit()
db.close()
print("Inserted 2JP8FC")
