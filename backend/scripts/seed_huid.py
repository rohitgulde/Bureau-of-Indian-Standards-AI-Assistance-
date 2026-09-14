import sys
from pathlib import Path
from datetime import datetime, timedelta
import logging

# Ensure the backend directory is in the python path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.database.session import Base, engine, SessionLocal
from app.models.db_models import HuidRecord

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def seed_huid_records():
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    # Check if records already exist
    if db.query(HuidRecord).count() > 0:
        logger.info("HUID records already exist. Skipping seed.")
        db.close()
        return

    sample_records = [
        HuidRecord(
            huid="AB1234",
            jeweller_name="Tanishq Jewellers",
            jeweller_reg_no="BIS/J/12345",
            ahc_name="Delhi Assaying & Hallmarking Centre",
            ahc_location="Karol Bagh, New Delhi",
            article_type="Gold Necklace",
            purity_karat="22K",
            purity_fineness="916",
            hallmarking_date=datetime.now() - timedelta(days=15),
            status="Active"
        ),
        HuidRecord(
            huid="JK7890",
            jeweller_name="Malabar Gold & Diamonds",
            jeweller_reg_no="BIS/J/67890",
            ahc_name="Mumbai Hallmarking Lab",
            ahc_location="Zaveri Bazaar, Mumbai",
            article_type="Gold Bangle",
            purity_karat="18K",
            purity_fineness="750",
            hallmarking_date=datetime.now() - timedelta(days=45),
            status="Active"
        ),
        HuidRecord(
            huid="HG5432",
            jeweller_name="Kalyan Jewellers",
            jeweller_reg_no="BIS/J/11223",
            ahc_name="Chennai Hallmarking Center",
            ahc_location="T. Nagar, Chennai",
            article_type="Gold Ring",
            purity_karat="14K",
            purity_fineness="585",
            hallmarking_date=datetime.now() - timedelta(days=120),
            status="Active"
        ),
        HuidRecord(
            huid="KL9988",
            jeweller_name="Joyalukkas",
            jeweller_reg_no="BIS/J/99887",
            ahc_name="Bangalore Assaying Center",
            ahc_location="Jayanagar, Bengaluru",
            article_type="Gold Earring",
            purity_karat="22K",
            purity_fineness="916",
            hallmarking_date=datetime.now() - timedelta(days=5),
            status="Active"
        ),
        HuidRecord(
            huid="XY5566",
            jeweller_name="PC Jeweller",
            jeweller_reg_no="BIS/J/55667",
            ahc_name="Delhi Assaying & Hallmarking Centre",
            ahc_location="Karol Bagh, New Delhi",
            article_type="Gold Chain",
            purity_karat="22K",
            purity_fineness="916",
            hallmarking_date=datetime.now() - timedelta(days=200),
            status="Active"
        ),
        HuidRecord(
            huid="MN3344",
            jeweller_name="Senco Gold",
            jeweller_reg_no="BIS/J/33445",
            ahc_name="Kolkata Hallmarking Services",
            ahc_location="Bowbazar, Kolkata",
            article_type="Gold Pendant",
            purity_karat="22K",
            purity_fineness="916",
            hallmarking_date=datetime.now() - timedelta(days=80),
            status="Active"
        ),
        HuidRecord(
            huid="PQ1122",
            jeweller_name="Bhima Jewellers",
            jeweller_reg_no="BIS/J/11221",
            ahc_name="Kochi Assaying Center",
            ahc_location="MG Road, Kochi",
            article_type="Gold Bracelet",
            purity_karat="18K",
            purity_fineness="750",
            hallmarking_date=datetime.now() - timedelta(days=10),
            status="Active"
        ),
        HuidRecord(
            huid="RS8877",
            jeweller_name="Reliance Jewels",
            jeweller_reg_no="BIS/J/88776",
            ahc_name="Ahmedabad Hallmarking Lab",
            ahc_location="CG Road, Ahmedabad",
            article_type="Gold Coin",
            purity_karat="24K",
            purity_fineness="999",
            hallmarking_date=datetime.now() - timedelta(days=30),
            status="Active"
        ),
        HuidRecord(
            huid="TU6655",
            jeweller_name="GRT Jewellers",
            jeweller_reg_no="BIS/J/66554",
            ahc_name="Hyderabad Assaying Bureau",
            ahc_location="Somajiguda, Hyderabad",
            article_type="Gold Necklace",
            purity_karat="22K",
            purity_fineness="916",
            hallmarking_date=datetime.now() - timedelta(days=300),
            status="Active"
        ),
        HuidRecord(
            huid="VW4433",
            jeweller_name="Thangamayil Jewellery",
            jeweller_reg_no="BIS/J/44332",
            ahc_name="Madurai Hallmarking Center",
            ahc_location="Netaji Road, Madurai",
            article_type="Gold Studs",
            purity_karat="22K",
            purity_fineness="916",
            hallmarking_date=datetime.now() - timedelta(days=2),
            status="Active"
        )
    ]

    db.add_all(sample_records)
    db.commit()
    logger.info(f"Successfully seeded {len(sample_records)} HUID records.")
    db.close()

if __name__ == "__main__":
    seed_huid_records()
