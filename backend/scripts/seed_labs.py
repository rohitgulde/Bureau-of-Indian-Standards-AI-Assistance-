"""
scripts/seed_labs.py
─────────────────────
Seeds the ``laboratories`` table with 20 realistic BIS-recognised /
NABL-accredited testing labs across Delhi, Mumbai, Bengaluru, Chennai,
and Kolkata.

Usage (run from backend/ with venv active)
-------------------------------------------
    python -m scripts.seed_labs            # safe: skips existing rows
    python -m scripts.seed_labs --reset    # wipe table, then re-seed
    python -m scripts.seed_labs --dry-run  # print rows without writing
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# Allow  python -m scripts.seed_labs  from backend/
_BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from app.database.session import SessionLocal, init_db
from app.models.db_models import Laboratory

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("seed_labs")


# ---------------------------------------------------------------------------
# Seed data — 20 realistic BIS-recognised / NABL labs
# ---------------------------------------------------------------------------
# Data is representative; contact details use plausible-but-fictional values.
# Replace with real data from the BIS Lab Portal before production use.

LAB_DATA: list[dict] = [

    # ── Delhi / NCR (5) ────────────────────────────────────────────────────

    {
        "name": "National Test House (NTH) — Northern Region",
        "state": "Delhi",
        "city": "New Delhi",
        "pincode": "110020",
        "address": "Block-B, CGO Complex, Lodhi Road, New Delhi – 110 003",
        "contact_email": "nth.north@gov.in",
        "phone": "+91-11-24360101",
        "website": "https://nth.gov.in",
        "accreditations": "NABL | BIS Recognised | Ministry of Consumer Affairs",
        "testing_scope": (
            "Steel, Cement, Packaged Drinking Water, Electrical Cables, "
            "Plastic Pipes, Paints & Varnishes, Automotive Accessories"
        ),
        "latitude": "28.5905",
        "longitude": "77.2281",
    },
    {
        "name": "Bureau of Indian Standards — Central Laboratory",
        "state": "Delhi",
        "city": "New Delhi",
        "pincode": "110002",
        "address": "Manak Bhavan, 9 Bahadur Shah Zafar Marg, New Delhi – 110 002",
        "contact_email": "centrallab@bis.gov.in",
        "phone": "+91-11-23230131",
        "website": "https://bis.gov.in",
        "accreditations": "NABL | ISO/IEC 17025:2017 | BIS Recognised",
        "testing_scope": (
            "Packaged Drinking Water, Helmets, Electrical Appliances, "
            "Toys, Pressure Cookers, LPG Cylinders, Fire Safety Equipment"
        ),
        "latitude": "28.6353",
        "longitude": "77.2400",
    },
    {
        "name": "Delhi Testing Laboratory (DTL)",
        "state": "Delhi",
        "city": "New Delhi",
        "pincode": "110035",
        "address": "D-Block, Lawrence Road Industrial Area, New Delhi – 110 035",
        "contact_email": "info@dtl.delhi.gov.in",
        "phone": "+91-11-27196000",
        "website": "https://dtl.delhi.gov.in",
        "accreditations": "NABL | BIS Recognised",
        "testing_scope": (
            "Textiles, Food Products, Pharmaceuticals, Pesticides, "
            "Building Materials, Water Quality"
        ),
        "latitude": "28.6982",
        "longitude": "77.1174",
    },
    {
        "name": "Electronics Regional Test Laboratory (ERTL) — North",
        "state": "Delhi",
        "city": "New Delhi",
        "pincode": "110020",
        "address": "Plot No. 2, Industrial Estate, Okhla Phase II, New Delhi – 110 020",
        "contact_email": "ertl.north@meity.gov.in",
        "phone": "+91-11-26387581",
        "website": "https://ertlindia.gov.in",
        "accreditations": "NABL | BIS Recognised | STQC",
        "testing_scope": (
            "IT Products, Electronic Components, LED Lights, "
            "Switchgear, Smart Meters, Telecom Equipment, EMC Testing"
        ),
        "latitude": "28.5357",
        "longitude": "77.2590",
    },
    {
        "name": "Central Pollution Control Board (CPCB) Laboratory",
        "state": "Delhi",
        "city": "New Delhi",
        "pincode": "110032",
        "address": "Parivesh Bhawan, East Arjun Nagar, Shahdara, Delhi – 110 032",
        "contact_email": "cpcblab@cpcb.nic.in",
        "phone": "+91-11-43102030",
        "website": "https://cpcb.nic.in",
        "accreditations": "NABL | MoEFCC Recognised",
        "testing_scope": (
            "Air Quality, Water Quality, Effluent, Noise, "
            "Solid Waste, Hazardous Chemicals, Stack Emissions"
        ),
        "latitude": "28.6729",
        "longitude": "77.3050",
    },

    # ── Mumbai / Maharashtra (4) ────────────────────────────────────────────

    {
        "name": "National Test House (NTH) — Western Region",
        "state": "Maharashtra",
        "city": "Mumbai",
        "pincode": "400030",
        "address": "Plot No. L-3, MIDC Industrial Area, Marol, Andheri (E), Mumbai – 400 093",
        "contact_email": "nth.west@gov.in",
        "phone": "+91-22-28366666",
        "website": "https://nth.gov.in",
        "accreditations": "NABL | BIS Recognised | Ministry of Consumer Affairs",
        "testing_scope": (
            "Steel, Cement, PVC Pipes, Electrical Cables, "
            "Safety Glass, Rubber Products, Chemical Products"
        ),
        "latitude": "19.1136",
        "longitude": "72.8697",
    },
    {
        "name": "Bombay Testing Laboratory (BTL)",
        "state": "Maharashtra",
        "city": "Mumbai",
        "pincode": "400019",
        "address": "4 & 5, Dr. Babasaheb Ambedkar Marg, Matunga (W), Mumbai – 400 019",
        "contact_email": "btl@mahalab.org",
        "phone": "+91-22-24156000",
        "website": "https://btl.maharashtra.gov.in",
        "accreditations": "NABL | BIS Recognised | ISO/IEC 17025:2017",
        "testing_scope": (
            "Textiles, Food Products, Beverages, Pharmaceuticals, "
            "Packaged Drinking Water, Plastic Products"
        ),
        "latitude": "19.0282",
        "longitude": "72.8541",
    },
    {
        "name": "Institute of Chemical Technology (ICT) — NABL Lab",
        "state": "Maharashtra",
        "city": "Mumbai",
        "pincode": "400019",
        "address": "Nathalal Parekh Marg, Matunga (E), Mumbai – 400 019",
        "contact_email": "nablab@ictmumbai.edu.in",
        "phone": "+91-22-33611111",
        "website": "https://ictmumbai.edu.in",
        "accreditations": "NABL | DST Recognised",
        "testing_scope": (
            "Paints, Varnishes, Adhesives, Polymers, "
            "Surface Coatings, Chemical Raw Materials, Solvents"
        ),
        "latitude": "19.0281",
        "longitude": "72.8691",
    },
    {
        "name": "Automotive Research Association of India (ARAI) — Type Approval",
        "state": "Maharashtra",
        "city": "Pune",
        "pincode": "411021",
        "address": "Survey No. 102, Vetal Hill, Off Paud Road, Kothrud, Pune – 411 038",
        "contact_email": "info@araiindia.com",
        "phone": "+91-20-30231111",
        "website": "https://araiindia.com",
        "accreditations": "NABL | BIS Recognised | AIS Certified | ISO/IEC 17025:2017",
        "testing_scope": (
            "Automotive Vehicles, Tyres, Helmets, Seatbelts, "
            "Emission Testing, Fuel Efficiency, Auto Components, Brake Systems"
        ),
        "latitude": "18.5018",
        "longitude": "73.8057",
    },

    # ── Bengaluru / Karnataka (4) ────────────────────────────────────────────

    {
        "name": "National Test House (NTH) — Southern Region",
        "state": "Karnataka",
        "city": "Bengaluru",
        "pincode": "560022",
        "address": "No. 1, I.I.Sc. Campus, CV Raman Road, Bengaluru – 560 012",
        "contact_email": "nth.south@gov.in",
        "phone": "+91-80-23600300",
        "website": "https://nth.gov.in",
        "accreditations": "NABL | BIS Recognised | Ministry of Consumer Affairs",
        "testing_scope": (
            "Steel, Cement, Electrical Equipment, Electronic Products, "
            "Packaged Food, Water Quality, Rubber Goods"
        ),
        "latitude": "13.0126",
        "longitude": "77.5655",
    },
    {
        "name": "Electronics Regional Test Laboratory (ERTL) — South",
        "state": "Karnataka",
        "city": "Bengaluru",
        "pincode": "560100",
        "address": "Block III, Electronic City Phase-I, Hosur Road, Bengaluru – 560 100",
        "contact_email": "ertl.south@meity.gov.in",
        "phone": "+91-80-28520320",
        "website": "https://ertlindia.gov.in",
        "accreditations": "NABL | BIS Recognised | STQC | ISO/IEC 17025:2017",
        "testing_scope": (
            "IT Hardware, Telecom Devices, LED Lighting, Power Supplies, "
            "EMI/EMC, Smart Meters, Semiconductors"
        ),
        "latitude": "12.8399",
        "longitude": "77.6770",
    },
    {
        "name": "Indian Institute of Science (IISc) — Testing Services",
        "state": "Karnataka",
        "city": "Bengaluru",
        "pincode": "560012",
        "address": "Sir CV Raman Avenue, IISc Campus, Bengaluru – 560 012",
        "contact_email": "testservices@iisc.ac.in",
        "phone": "+91-80-22932004",
        "website": "https://iisc.ac.in",
        "accreditations": "NABL | DST Recognised | ISO/IEC 17025:2017",
        "testing_scope": (
            "Advanced Materials, Aerospace Components, "
            "Metallurgy, High-Strength Steel, Composite Materials"
        ),
        "latitude": "13.0210",
        "longitude": "77.5697",
    },
    {
        "name": "Karnataka State Testing Laboratory (KSTL)",
        "state": "Karnataka",
        "city": "Bengaluru",
        "pincode": "560001",
        "address": "No. 49, 2nd Cross, Palace Road, Bengaluru – 560 001",
        "contact_email": "kstl@karnataka.gov.in",
        "phone": "+91-80-22867000",
        "website": "https://kstl.karnataka.gov.in",
        "accreditations": "NABL | BIS Recognised",
        "testing_scope": (
            "Food Products, Ayurvedic Products, Agri-Inputs, "
            "Soil Testing, Fertilisers, Pesticides"
        ),
        "latitude": "12.9824",
        "longitude": "77.5999",
    },

    # ── Chennai / Tamil Nadu (4) ─────────────────────────────────────────────

    {
        "name": "National Test House (NTH) — Eastern Region",
        "state": "Tamil Nadu",
        "city": "Chennai",
        "pincode": "600032",
        "address": "No. 21, Rajaji Salai (NSC Bose Road), Chennai – 600 001",
        "contact_email": "nth.east@gov.in",
        "phone": "+91-44-25221000",
        "website": "https://nth.gov.in",
        "accreditations": "NABL | BIS Recognised",
        "testing_scope": (
            "Steel, Cement, Electrical Cables, Automotive Parts, "
            "Plastic Pipes, Packaged Drinking Water"
        ),
        "latitude": "13.0851",
        "longitude": "80.2851",
    },
    {
        "name": "Council of Scientific & Industrial Research — CSIR-CLRI",
        "state": "Tamil Nadu",
        "city": "Chennai",
        "pincode": "600020",
        "address": "Adyar, Chennai – 600 020",
        "contact_email": "director@clri.res.in",
        "phone": "+91-44-24910846",
        "website": "https://clri.res.in",
        "accreditations": "NABL | CSIR | ISO/IEC 17025:2017",
        "testing_scope": (
            "Leather Goods, Footwear, Upholstery, "
            "Leather Chemicals, Effluent from Tanneries, Rubber"
        ),
        "latitude": "13.0049",
        "longitude": "80.2571",
    },
    {
        "name": "Tamil Nadu Water Supply & Drainage Board (TWAD) Laboratory",
        "state": "Tamil Nadu",
        "city": "Chennai",
        "pincode": "600002",
        "address": "TWAD House, 31, Kamarajar Salai, Chepauk, Chennai – 600 002",
        "contact_email": "chemlab@twadboard.gov.in",
        "phone": "+91-44-28520250",
        "website": "https://twadboard.gov.in",
        "accreditations": "NABL | BIS Recognised | IS 10500 Compliant",
        "testing_scope": (
            "Packaged Drinking Water, Potable Water, "
            "Sewage Analysis, Bore Well Water, Industrial Effluent"
        ),
        "latitude": "13.0633",
        "longitude": "80.2823",
    },
    {
        "name": "Southern Regional Testing Laboratory (SRTL)",
        "state": "Tamil Nadu",
        "city": "Chennai",
        "pincode": "600040",
        "address": "Taramani Institutional Area, CSIR Road, Chennai – 600 113",
        "contact_email": "srtl@tnlab.gov.in",
        "phone": "+91-44-22541500",
        "website": "https://srtl.tn.gov.in",
        "accreditations": "NABL | BIS Recognised",
        "testing_scope": (
            "Consumer Electronics, Electrical Toys, Kitchen Appliances, "
            "Inverters, Solar Panels, UPS Systems"
        ),
        "latitude": "12.9883",
        "longitude": "80.2481",
    },

    # ── Kolkata / West Bengal (3) ────────────────────────────────────────────

    {
        "name": "National Test House (NTH) — Kolkata (HQ)",
        "state": "West Bengal",
        "city": "Kolkata",
        "pincode": "700085",
        "address": "Block GN, Sector V, Salt Lake City, Kolkata – 700 091",
        "contact_email": "nth.hq@gov.in",
        "phone": "+91-33-23670000",
        "website": "https://nth.gov.in",
        "accreditations": "NABL | BIS Recognised | Ministry of Consumer Affairs | ISO/IEC 17025:2017",
        "testing_scope": (
            "Steel, Cement, Packaged Drinking Water, Electrical Equipment, "
            "Jute Products, Plastic Goods, Chemical Products, Textiles"
        ),
        "latitude": "22.5711",
        "longitude": "88.4343",
    },
    {
        "name": "Central Glass & Ceramic Research Institute (CGCRI) — CSIR",
        "state": "West Bengal",
        "city": "Kolkata",
        "pincode": "700032",
        "address": "196, Raja S.C. Mullick Road, Jadavpur, Kolkata – 700 032",
        "contact_email": "info@cgcri.res.in",
        "phone": "+91-33-24733496",
        "website": "https://cgcri.res.in",
        "accreditations": "NABL | CSIR | ISO/IEC 17025:2017",
        "testing_scope": (
            "Glass Products, Ceramics, Refractories, "
            "Safety Glass, Optical Fibres, Building Tiles, Sanitary Ware"
        ),
        "latitude": "22.4998",
        "longitude": "88.3651",
    },
    {
        "name": "West Bengal State Beverages Corporation Laboratory (WBSBC)",
        "state": "West Bengal",
        "city": "Kolkata",
        "pincode": "700064",
        "address": "Beltala Road, Park Circus Area, Kolkata – 700 064",
        "contact_email": "lab@wbsbc.in",
        "phone": "+91-33-22879000",
        "website": "https://wbsbc.gov.in",
        "accreditations": "NABL | FSSAI Recognised | BIS Recognised",
        "testing_scope": (
            "Beverages, Packaged Drinking Water, Mineral Water, "
            "Alcoholic Beverages, Soft Drinks, Fruit Juices"
        ),
        "latitude": "22.5373",
        "longitude": "88.3610",
    },
]


# ---------------------------------------------------------------------------
# Seeder
# ---------------------------------------------------------------------------

def seed(reset: bool = False, dry_run: bool = False) -> None:
    """
    Seed the laboratories table.

    Parameters
    ----------
    reset:
        If True, truncate the table before inserting.
    dry_run:
        If True, print the rows that *would* be inserted without writing.
    """
    if not dry_run:
        init_db()                          # ensures tables exist

    db = SessionLocal()
    try:
        if reset and not dry_run:
            deleted = db.query(Laboratory).delete()
            db.commit()
            logger.info("Cleared %d existing rows.", deleted)

        inserted = 0
        skipped  = 0

        for data in LAB_DATA:
            if dry_run:
                print(f"  [DRY RUN] Would insert: {data['name']} ({data['city']})")
                inserted += 1
                continue

            # Skip if already present (idempotent seeding)
            exists = (
                db.query(Laboratory.id)
                  .filter(Laboratory.name == data["name"])
                  .scalar()
            )
            if exists:
                logger.debug("Skip (already exists): %s", data["name"])
                skipped += 1
                continue

            lab = Laboratory(**data, is_active=True)
            db.add(lab)
            inserted += 1

        if not dry_run:
            db.commit()

        logger.info(
            "Seed complete — inserted: %d, skipped (duplicate): %d",
            inserted, skipped,
        )

    except Exception as exc:
        if not dry_run:
            db.rollback()
        logger.exception("Seeding failed: %s", exc)
        raise
    finally:
        db.close()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Seed the laboratories table with BIS-recognised lab data.",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Truncate the laboratories table before seeding.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print rows that would be inserted without touching the database.",
    )
    args = parser.parse_args(argv)

    seed(reset=args.reset, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())