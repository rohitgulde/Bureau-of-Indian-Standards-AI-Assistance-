"""
scripts/seed_reference_data.py
────────────────────────────────
Seeds certification_schemes and consumer_faqs with official BIS
operational guidelines.

Usage (run from backend/ with venv active)
------------------------------------------
    python -m scripts.seed_reference_data
    python -m scripts.seed_reference_data --reset
    python -m scripts.seed_reference_data --dry-run
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from app.database.session import SessionLocal, init_db
from app.models.db_models import CertificationScheme, ConsumerFAQ

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("seed_reference")


# ============================================================
# CERTIFICATION SCHEMES
# ============================================================

SCHEME_DATA: list[dict] = [
    {
        "scheme_name": "ISI Mark - Scheme I (Factory Licence)",
        "scheme_code": "ISI-I",
        "target_audience": "Domestic Manufacturer",
        "mandatory_or_voluntary": "Mandatory",
        "governing_regulation": "BIS Act 2016, Section 16 & 17; BIS (Conformity Assessment) Regulations 2018",
        "applicable_products": (
            "Cement, Steel Bars (TMT/HSD), LPG Cylinders, Electrical Cables, PVC Pipes, "
            "Helmets, Packaged Drinking Water (IS 10500), Pressure Cookers, Kitchen Appliances, "
            "Safety Matches, Automotive Accessories"
        ),
        "application_portal_url": "https://manakonline.in",
        "standard_turnaround_time": "60-90 working days (after complete documentation)",
        "fee_structure_note": (
            "Application fee: INR 1,000-10,000 (product-dependent); "
            "Annual licence fee: INR 500-50,000; "
            "Marking fee: per unit basis as per BIS rate schedule"
        ),
        "validity_period": "1 year (renewable annually)",
        "description": (
            "Scheme I is the primary ISI Mark pathway for domestic manufacturers. "
            "Process: (1) Apply online at Manakonline with factory details, test reports, and QA documents. "
            "(2) BIS scrutiny within 15 working days. "
            "(3) Factory audit by BIS officer. "
            "(4) Product samples tested at BIS-recognised labs. "
            "(5) Licence granted if audit and test results are satisfactory. "
            "(6) Post-licence: surprise visits and market surveillance by BIS."
        ),
    },
    {
        "scheme_name": "ISI Mark - Scheme II (Importer Licence)",
        "scheme_code": "ISI-II",
        "target_audience": "Importer",
        "mandatory_or_voluntary": "Mandatory",
        "governing_regulation": "BIS Act 2016, Section 17(2); Compulsory Registration Order (CRO)",
        "applicable_products": "All products notified under mandatory ISI regime that are imported into India",
        "application_portal_url": "https://manakonline.in",
        "standard_turnaround_time": "30-60 working days",
        "fee_structure_note": "Application fee: INR 1,000; marking fee per unit imported; random sampling by BIS",
        "validity_period": "1 year (renewable)",
        "description": (
            "Importers of ISI-mandatory products must obtain a BIS Importer Licence. "
            "Process: (1) Register on Manakonline as Importer. "
            "(2) Submit technical file: foreign manufacturer details, test reports, Declaration of Conformity. "
            "(3) BIS may require overseas factory audit or accept third-party reports. "
            "(4) Sample tested at BIS-recognised Indian lab. "
            "(5) Importer Licence granted; each consignment must carry BIS licence number."
        ),
    },
    {
        "scheme_name": "Compulsory Registration Scheme (CRS)",
        "scheme_code": "CRS",
        "target_audience": "Domestic Manufacturer, Importer",
        "mandatory_or_voluntary": "Mandatory",
        "governing_regulation": "Electronics & IT Goods (Requirements for Compulsory Registration) Order 2012 (amended 2021); BIS Act 2016",
        "applicable_products": (
            "LED Lights, Mobile Phones, Laptops, Tablets, Power Banks, Set-Top Boxes, "
            "Smart Meters, UPS, Invertors, Visual Display Units, Microwave Ovens, "
            "Washing Machines, Air Conditioners, Refrigerators"
        ),
        "application_portal_url": "https://crsbis.in",
        "standard_turnaround_time": "15-30 working days (self-declaration model)",
        "fee_structure_note": "Registration fee: INR 1,000 per product model; test report required; no annual fee",
        "validity_period": "2 years (renewable; model-linked)",
        "description": (
            "CRS covers electronic/IT products under the Compulsory Registration Order. "
            "Unlike ISI Mark (factory audit-based), CRS is a self-declaration + test-report model. "
            "Process: (1) Test product at authorised lab. "
            "(2) Register on https://crsbis.in with test report and product details. "
            "(3) BIS issues Registration Certificate with unique R-number. "
            "(4) R-number and BIS logo must appear on product/packaging. "
            "Foreign manufacturers must appoint an Authorised Indian Representative (AIR)."
        ),
    },
    {
        "scheme_name": "Foreign Manufacturers Certification Scheme (FMCS)",
        "scheme_code": "FMCS",
        "target_audience": "Foreign Manufacturer",
        "mandatory_or_voluntary": "Mandatory",
        "governing_regulation": "BIS Act 2016, Section 17(3); BIS (Foreign Manufacturers Certification) Scheme 2019",
        "applicable_products": (
            "All ISI-mandatory products manufactured outside India: "
            "Steel, Cement, Electrical Equipment, Helmets, Toys, LPG Equipment"
        ),
        "application_portal_url": "https://manakonline.in",
        "standard_turnaround_time": "90-120 working days (includes overseas factory audit)",
        "fee_structure_note": "Application fee: USD 300 (non-refundable); overseas audit costs borne by applicant; annual licence fee as per BIS schedule",
        "validity_period": "1 year (renewable)",
        "description": (
            "FMCS allows foreign manufacturers to obtain direct BIS certification. "
            "Process: (1) Apply on Manakonline with factory and QMS details. "
            "(2) BIS scrutinises documents; USD 300 application fee. "
            "(3) BIS deputes officers for overseas factory audit - applicant pays all travel costs. "
            "(4) Samples tested at BIS-recognised Indian labs. "
            "(5) Licence granted; manufacturer affixes ISI Mark on products shipped to India."
        ),
    },
    {
        "scheme_name": "BIS Hallmarking - Jeweller Registration",
        "scheme_code": "HM-J",
        "target_audience": "Jeweller",
        "mandatory_or_voluntary": "Mandatory",
        "governing_regulation": "BIS (Hallmarking) Regulations 2018; BIS Act 2016; Gold & Silver Hallmarking Order (Mandatory) 2021",
        "applicable_products": "Gold Jewellery (14, 18, 22 Karat), Silver Articles (above specified weight threshold)",
        "application_portal_url": "https://huidonline.bis.gov.in",
        "standard_turnaround_time": "7-15 working days",
        "fee_structure_note": "Registration fee: INR 5,000 (5-year validity); HUID fee: INR 35 per article at AHSC",
        "validity_period": "5 years (renewable)",
        "description": (
            "All jewellers selling gold jewellery above 2g must sell BIS-hallmarked articles with HUID since 2021. "
            "Process: (1) Register on https://huidonline.bis.gov.in with KYC documents. "
            "(2) BIS assigns Jeweller Registration Number (JRN). "
            "(3) Submit articles to BIS-recognised AHSC for assaying and hallmarking. "
            "(4) HUID (6-character alphanumeric) assigned to each article. "
            "(5) Consumers verify HUID on BIS Care App. "
            "Selling non-hallmarked jewellery is a punishable offence under BIS Act 2016."
        ),
    },
    {
        "scheme_name": "BIS Hallmarking - Assaying & Hallmarking Centre (AHSC)",
        "scheme_code": "HM-AHSC",
        "target_audience": "Assaying & Hallmarking Centre",
        "mandatory_or_voluntary": "Mandatory",
        "governing_regulation": "BIS (Hallmarking) Regulations 2018; IS 1417 (Gold Fineness); IS 2112 (Silver)",
        "applicable_products": "Gold Jewellery, Silver Articles",
        "application_portal_url": "https://huidonline.bis.gov.in",
        "standard_turnaround_time": "45-60 working days (includes equipment audit)",
        "fee_structure_note": "Application fee: INR 25,000; Annual AHSC renewal: INR 10,000",
        "validity_period": "1 year (renewable)",
        "description": (
            "An AHSC is a BIS-authorised centre that assays and hallmarks gold/silver articles. "
            "Eligibility: calibrated XRF spectrometer + fire assay equipment, trained staff, QA plan. "
            "Process: (1) Apply on HUID Online with equipment and premises details. "
            "(2) BIS officer inspects facility against IS 1417/IS 2112. "
            "(3) Proficiency test with blind samples. "
            "(4) AHSC code allotted; hallmarking operations commence. "
            "BIS conducts regular proficiency tests and surprise inspections."
        ),
    },
    {
        "scheme_name": "Eco Mark Scheme",
        "scheme_code": "ECO",
        "target_audience": "Domestic Manufacturer, Importer",
        "mandatory_or_voluntary": "Voluntary",
        "governing_regulation": "Environment (Protection) Act 1986; Eco Mark Scheme Notification 1991 (MoEFCC + BIS joint)",
        "applicable_products": "Soaps, Detergents, Paper, Plastics, Textiles, Batteries, Lubricating Oils, Paints, Electronics",
        "application_portal_url": "https://manakonline.in",
        "standard_turnaround_time": "60-120 working days",
        "fee_structure_note": "Application fee: INR 5,000; Annual: INR 10,000 (SME) / INR 25,000 (large)",
        "validity_period": "3 years (renewable)",
        "description": (
            "Voluntary environmental label awarded to products meeting both IS quality and MoEFCC environmental criteria. "
            "Products must first hold an ISI Licence. "
            "Process: (1) Hold or apply for ISI Licence. "
            "(2) Apply on Manakonline with environmental criteria compliance evidence. "
            "(3) BIS + MoEFCC jointly evaluate; third-party environmental audit may be required. "
            "(4) Eco Mark certificate issued alongside ISI Mark."
        ),
    },
    {
        "scheme_name": "Voluntary BIS Certification Scheme (Scheme V)",
        "scheme_code": "VOL-V",
        "target_audience": "Domestic Manufacturer, Importer",
        "mandatory_or_voluntary": "Voluntary",
        "governing_regulation": "BIS Act 2016, Section 16(1); BIS Certification Marks Regulations 2018",
        "applicable_products": "Any product with a published IS that is NOT notified as mandatory — furniture, sports equipment, stationery",
        "application_portal_url": "https://manakonline.in",
        "standard_turnaround_time": "45-75 working days",
        "fee_structure_note": "Application fee: INR 1,000; annual and marking fees at lower voluntary scheme rates",
        "validity_period": "1 year (renewable)",
        "description": (
            "Manufacturers of any IS-standard product may voluntarily seek BIS certification "
            "to improve consumer trust and qualify for government tenders. "
            "Process mirrors Scheme I (ISI-I) but is manufacturer-initiated. "
            "The ISI Mark on voluntary products indicates IS conformance and periodic BIS surveillance."
        ),
    },
]

# ============================================================
# CONSUMER FAQs
# ============================================================

FAQ_DATA: list[dict] = [
    {
        "topic": "HUID Verification - How to verify gold jewellery authenticity",
        "category": "Hallmarking",
        "keywords": "HUID, hallmark, gold, verify, authentic, BIS Care, 6-digit code",
        "question": "I bought gold jewellery with a 6-character code stamped on it. How do I verify it is genuine BIS-hallmarked?",
        "resolution_steps": (
            "**Verifying HUID on BIS-Hallmarked Jewellery**\n\n"
            "1. **Locate the HUID**: Find the 6-character alphanumeric code (e.g. AB1234) engraved on the article.\n"
            "2. **Open BIS Care App**: Download from Google Play or Apple App Store (search 'BIS Care').\n"
            "3. **Select 'Verify HUID'**: Tap Verify HUID on the app home screen.\n"
            "4. **Enter the 6-digit HUID**: Type the code exactly as engraved.\n"
            "5. **Review results**: App displays article type, fineness (e.g. 916 = 22K), AHSC name, and hallmarking date.\n"
            "6. **Alternatively**: Visit https://bis.gov.in -> HUID Verification and enter HUID.\n"
            "7. **Red flag**: If HUID returns 'Not Found', the article may be fake - file a complaint.\n\n"
            "HUID verification is mandatory for gold jewellery sold in India since April 2023. "
            "Jewellers selling non-HUID jewellery face fines up to INR 1 lakh under BIS Act 2016."
        ),
        "related_url": "https://bis.gov.in/product-certification/hallmarking/",
        "related_scheme": "HM-J",
        "sort_order": 10,
    },
    {
        "topic": "Spurious ISI Mark Complaint - Reporting fake ISI-marked products",
        "category": "Complaints",
        "keywords": "fake ISI, spurious, complaint, report, counterfeit, BIS enforcement",
        "question": "I purchased a product with an ISI Mark but it seems substandard or fake. How do I report it to BIS?",
        "resolution_steps": (
            "**Reporting a Spurious or Fake ISI Mark**\n\n"
            "1. **Collect evidence**: Keep the product, packaging, invoice, and photos of the ISI Mark and CM/L licence number.\n"
            "2. **Verify on BIS Portal**: Visit https://bis.gov.in -> 'Verify Licence' -> enter CM/L number to check validity.\n"
            "3. **Use BIS Care App**: Open app -> 'Verify Product' -> scan barcode or enter licence number.\n"
            "4. **Lodge complaint online**: Go to https://bis.gov.in -> 'Consumer Services' -> 'Lodge Complaint'. "
            "Fill product name, manufacturer/seller details, CM/L number, purchase location, and upload evidence.\n"
            "5. **Lodge complaint offline**: Write to the Head of nearest BIS Regional/Branch Office.\n"
            "6. **Helpline**: Call **1800-11-4000** (Toll-Free, Mon-Fri, 9am-5pm).\n"
            "7. **BIS action**: Enforcement officers seize samples, test them, and initiate prosecution.\n\n"
            "Penalty for fake ISI Mark: imprisonment up to 2 years and/or fine up to INR 2 lakh (BIS Act 2016, Section 29)."
        ),
        "related_url": "https://bis.gov.in/consumer-services/lodge-complaint/",
        "related_scheme": "ISI-I",
        "sort_order": 20,
    },
    {
        "topic": "BIS Care App - Features and usage guide",
        "category": "General",
        "keywords": "BIS Care App, verify, product, hallmark, HUID, scan, download, mobile",
        "question": "What is the BIS Care App and what can it do for me as a consumer?",
        "resolution_steps": (
            "**BIS Care App - Consumer Guide**\n\n"
            "Free official app by BIS. Download from Google Play / Apple App Store (search 'BIS Care').\n\n"
            "**Key Features**:\n"
            "1. **Verify ISI Licence**: Enter CM/L number to check if an ISI licence is valid.\n"
            "2. **Verify HUID**: Enter 6-character HUID to confirm gold jewellery is genuinely hallmarked.\n"
            "3. **Verify CRS Registration**: Enter Registration Number to check an electronics product.\n"
            "4. **Scan QR Code/Barcode**: Point camera at product QR for instant verification.\n"
            "5. **Lodge Complaint**: Report fake ISI Mark, spurious hallmark, or unlicensed products with photo evidence.\n"
            "6. **Find Nearby Labs**: Locate BIS-recognised testing labs near your pincode.\n"
            "7. **IS Standard Lookup**: Search Indian Standards by number or keyword.\n\n"
            "Available in English and Hindi. Requires internet for real-time verification."
        ),
        "related_url": "https://bis.gov.in/consumer-services/bis-care-app/",
        "related_scheme": None,
        "sort_order": 5,
    },
    {
        "topic": "Mandatory vs Voluntary BIS Certification - Key differences",
        "category": "General",
        "keywords": "mandatory, voluntary, ISI Mark, compulsory, optional, BIS certification",
        "question": "Which products must mandatorily carry the BIS ISI Mark and which can have it optionally?",
        "resolution_steps": (
            "**Mandatory vs Voluntary BIS Certification**\n\n"
            "**Mandatory Products** (ISI Mark required by law - over 500 product categories):\n"
            "- Cement (IS 269, IS 1489)\n"
            "- Steel bars / TMT bars (IS 1786)\n"
            "- Packaged Drinking Water (IS 14543)\n"
            "- LPG Cylinders (IS 3196)\n"
            "- Electrical Cables (IS 694, IS 1554)\n"
            "- Helmets (IS 4151)\n"
            "- Pressure Cookers (IS 2347)\n"
            "- LED Luminaires (under CRS)\n\n"
            "Full list: https://bis.gov.in -> 'Certification' -> 'Compulsory Certification Products'\n\n"
            "**Voluntary Products**: Manufacturers of products with a published IS (not notified as mandatory) "
            "may voluntarily seek BIS certification to improve consumer trust, qualify for government tenders, "
            "and facilitate export documentation.\n\n"
            "**Penalty for missing mandatory ISI Mark**: Fine up to INR 2 lakh and/or imprisonment up to 2 years "
            "(BIS Act 2016, Section 29)."
        ),
        "related_url": "https://bis.gov.in/product-certification/compulsory-certification/",
        "related_scheme": "ISI-I",
        "sort_order": 15,
    },
    {
        "topic": "CRS Product Registration - How importers register electronics",
        "category": "CRS",
        "keywords": "CRS, electronics, import, registration, LED, mobile phone, laptop, IT products",
        "question": "I am importing LED bulbs and mobile phones. How do I register them under the Compulsory Registration Scheme (CRS)?",
        "resolution_steps": (
            "**CRS Registration for Importers - Step-by-Step**\n\n"
            "1. **Confirm product is covered**: Check CRS-notified product list at https://crsbis.in -> 'Product List'.\n"
            "2. **Get product tested**: Submit samples to a BIS-recognised/NABL lab against the relevant IS/IEC standard. "
            "Example: LED Bulbs -> IS 16103; Mobile Phones -> IS 13252.\n"
            "3. **Appoint Authorised Indian Representative (AIR)**: Foreign importers must have an AIR in India.\n"
            "4. **Create account on CRS Portal**: Register at https://crsbis.in as 'Importer'.\n"
            "5. **Submit per-model application**: Each model requires separate application with test report, "
            "product specs, photographs, and AIR declaration.\n"
            "6. **Pay registration fee**: INR 1,000 per model (online payment).\n"
            "7. **Receive Registration Certificate (RC)**: BIS issues RC with Registration Number (R-XXXXXXXXXXXXXXXX).\n"
            "8. **Mark products**: R-number and BIS logo must appear on product/packaging before import clearance.\n"
            "9. **Renewal**: Registration valid for 2 years.\n\n"
            "Importing CRS-notified products without valid registration is prohibited - customs authorities may reject consignments."
        ),
        "related_url": "https://crsbis.in",
        "related_scheme": "CRS",
        "sort_order": 25,
    },
    {
        "topic": "ISI Licence Renewal - Process and deadlines",
        "category": "ISI Mark",
        "keywords": "renewal, ISI licence, expired, CM/L, annual, lapse, extension",
        "question": "My ISI licence (CM/L number) is expiring next month. What is the renewal process and what happens if it lapses?",
        "resolution_steps": (
            "**ISI Licence Renewal - Step-by-Step**\n\n"
            "Apply at least **30-45 days before expiry**.\n\n"
            "1. **Log in to Manakonline**: https://manakonline.in -> My Licences -> select licence to renew.\n"
            "2. **Check dues**: Ensure no outstanding marking fees or audit non-conformances.\n"
            "3. **Submit renewal application**: Confirm factory details, QA records, and test reports are current.\n"
            "4. **Pay annual licence fee**: As per BIS rate schedule for your product category.\n"
            "5. **BIS review**: May conduct renewal audit or accept self-declaration based on compliance history.\n"
            "6. **Renewal certificate issued**: Download from Manakonline.\n\n"
            "**If the licence lapses**:\n"
            "- Stop using the ISI Mark immediately.\n"
            "- Fresh application required (treated as new applicant).\n"
            "- Products bearing ISI Mark after expiry are considered spurious - liable to prosecution.\n"
            "- BIS may seize stock manufactured after expiry date.\n\n"
            "BIS does not provide an automatic grace period - apply before expiry date."
        ),
        "related_url": "https://manakonline.in",
        "related_scheme": "ISI-I",
        "sort_order": 30,
    },
    {
        "topic": "Hallmarking Complaint - Incorrect karat or purity mismatch",
        "category": "Hallmarking",
        "keywords": "wrong karat, hallmark wrong, purity, 22K, 18K, AHSC complaint, refund",
        "question": "The jewellery I bought is hallmarked 22K (916) but an independent assay shows it is only 18K. What are my rights?",
        "resolution_steps": (
            "**Reporting Incorrect Hallmarking (Wrong Purity/Karat)**\n\n"
            "Under BIS Act 2016 and Consumer Protection Act 2019, you are entitled to a full refund or replacement.\n\n"
            "1. **Get independent assay**: Visit any BIS-recognised AHSC (not the original one) and request a purity test. Keep the assay report.\n"
            "2. **Complain to jeweller first**: Present independent assay report and demand refund/replacement in writing.\n"
            "3. **Report to BIS online**: https://bis.gov.in -> Lodge Complaint -> select 'Hallmarking Complaint'. "
            "Submit HUID, AHSC code, jeweller details, and assay reports.\n"
            "4. **BIS action on AHSC**: BIS inspects the AHSC, retests blind samples, and may suspend/cancel AHSC authorisation.\n"
            "5. **Consumer Forum**: If jeweller refuses refund, file at District Consumer Disputes Redressal Commission (DCDRC).\n"
            "6. **National Consumer Helpline**: Call 1915 (Toll-Free) or file at https://consumerhelpline.gov.in.\n\n"
            "AHSCs are legally liable for incorrect hallmarking and must compensate for losses."
        ),
        "related_url": "https://bis.gov.in/product-certification/hallmarking/",
        "related_scheme": "HM-AHSC",
        "sort_order": 12,
    },
    {
        "topic": "FMCS Application - Foreign manufacturer getting BIS certification",
        "category": "ISI Mark",
        "keywords": "FMCS, foreign manufacturer, overseas, factory audit, import India",
        "question": "We manufacture steel pipes in South Korea and want to export to India. Do we need BIS certification?",
        "resolution_steps": (
            "**FMCS Application Guide for Foreign Manufacturers**\n\n"
            "Yes - if steel pipes are notified as mandatory ISI products, they must carry ISI Mark.\n\n"
            "1. **Check mandatory status**: https://bis.gov.in -> Compulsory Certification Products.\n"
            "2. **Create account on Manakonline**: Register as 'Foreign Manufacturer'.\n"
            "3. **Submit application with**: Factory details, plant layout, QMS (ISO 9001 preferred), "
            "technical file, test reports from accredited overseas lab.\n"
            "4. **Pay application fee**: USD 300 (non-refundable, via wire transfer).\n"
            "5. **BIS overseas factory audit**: BIS deputes 2 officers to your facility. "
            "You pay all travel, visa, accommodation, and per diem costs in advance.\n"
            "6. **Sample testing**: BIS draws samples at factory; tested at BIS-recognised Indian lab.\n"
            "7. **Licence issued**: Affix ISI Mark on products exported to India.\n"
            "8. **Annual renewal**: Valid 1 year; renew with updated test reports.\n\n"
            "Alternative: Appoint an Indian importer who obtains an ISI Importer Licence (ISI-II) - "
            "this shifts compliance responsibility to the Indian entity."
        ),
        "related_url": "https://manakonline.in",
        "related_scheme": "FMCS",
        "sort_order": 35,
    },
    {
        "topic": "IS Standard Purchase - How to buy Indian Standards documents",
        "category": "General",
        "keywords": "buy IS standard, purchase standard, PDF, document, Manak Online, price",
        "question": "Where can I purchase the full text of an Indian Standard (IS) document like IS 10500 or IS 1786?",
        "resolution_steps": (
            "**How to Purchase Indian Standard (IS) Documents**\n\n"
            "BIS sells IS documents in physical and PDF formats (INR 100 to INR 2,000).\n\n"
            "**Option 1 - Online PDF (instant delivery)**:\n"
            "1. Go to https://standardsbis.bsbedge.com\n"
            "2. Search by IS number or keyword -> Add to cart -> Pay via UPI/card.\n"
            "3. PDF available for immediate download.\n\n"
            "**Option 2 - BIS Sales Counter**: Visit nearest BIS Regional/Branch Office with DD/cash payable to 'Bureau of Indian Standards'.\n\n"
            "**Option 3 - Institutional Subscription**: Contact subscription@bis.gov.in for bulk access.\n\n"
            "**Free access**: BIS Reading Room at Regional Offices (on-premises only); "
            "some standards available free at https://bis.gov.in -> 'Free Standards'.\n\n"
            "Downloading IS standards from unofficial/pirated sources violates copyright."
        ),
        "related_url": "https://standardsbis.bsbedge.com",
        "related_scheme": None,
        "sort_order": 40,
    },
    {
        "topic": "Eco Mark - What it means and how to verify",
        "category": "General",
        "keywords": "Eco Mark, green, environment, eco-friendly, label, verify, sustainable",
        "question": "I see products with an Eco Mark alongside the ISI Mark. What does it mean and is it reliable?",
        "resolution_steps": (
            "**Understanding the BIS Eco Mark**\n\n"
            "Voluntary environmental label jointly operated by BIS and MoEFCC. "
            "Indicates a product meets both IS quality AND environmental criteria.\n\n"
            "**What it guarantees**:\n"
            "- Product holds a valid ISI Licence (quality assured).\n"
            "- Product meets environmental criteria: lower toxicity, recyclability, biodegradability, or energy efficiency.\n\n"
            "**How to verify**:\n"
            "1. Check the product also carries a valid ISI Mark (mandatory prerequisite).\n"
            "2. Verify the ISI licence number on BIS Care App or https://bis.gov.in.\n"
            "3. Contact BIS to confirm Eco Mark validity: ecomark@bis.gov.in\n\n"
            "**Product categories**: Soaps, detergents, paper, plastic bags, paints, batteries, lubricants, food, electronics.\n\n"
            "Choosing Eco-marked products is especially relevant for procurement under government green initiatives "
            "and for environmentally conscious consumers."
        ),
        "related_url": "https://bis.gov.in/product-certification/eco-mark/",
        "related_scheme": "ECO",
        "sort_order": 45,
    },
]


# ============================================================
# Seeder
# ============================================================

def seed(reset: bool = False, dry_run: bool = False) -> None:
    if not dry_run:
        init_db()

    db = SessionLocal()
    try:
        if reset and not dry_run:
            db.query(CertificationScheme).delete()
            db.query(ConsumerFAQ).delete()
            db.commit()
            logger.info("Tables cleared.")

        schemes_ins = schemes_skip = 0
        for data in SCHEME_DATA:
            if dry_run:
                print(f"  [SCHEME] {data['scheme_code']:10s} {data['scheme_name']}")
                schemes_ins += 1
                continue
            exists = db.query(CertificationScheme.id).filter(
                CertificationScheme.scheme_code == data["scheme_code"]
            ).scalar()
            if exists:
                schemes_skip += 1
                continue
            db.add(CertificationScheme(**data, is_active=True))
            schemes_ins += 1

        faqs_ins = faqs_skip = 0
        for data in FAQ_DATA:
            if dry_run:
                print(f"  [FAQ]    [{data['category']:15s}] {data['topic']}")
                faqs_ins += 1
                continue
            exists = db.query(ConsumerFAQ.id).filter(
                ConsumerFAQ.topic == data["topic"]
            ).scalar()
            if exists:
                faqs_skip += 1
                continue
            db.add(ConsumerFAQ(**data, is_published=True))
            faqs_ins += 1

        if not dry_run:
            db.commit()

        logger.info("Schemes  -- inserted: %d, skipped: %d", schemes_ins, schemes_skip)
        logger.info("FAQs     -- inserted: %d, skipped: %d", faqs_ins, faqs_skip)

    except Exception as exc:
        if not dry_run:
            db.rollback()
        logger.exception("Seeding failed: %s", exc)
        raise
    finally:
        db.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Seed certification_schemes and consumer_faqs.",
    )
    parser.add_argument("--reset",   action="store_true",
                        help="Truncate both tables before seeding.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview rows without writing to DB.")
    args = parser.parse_args(argv)
    seed(reset=args.reset, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
