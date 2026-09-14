"""
scripts/seed_demo_data.py
--------------------------
End-to-end demo seeder for the BIS Knowledge Portal.

Stage 1 - Generate realistic BIS reference PDFs into data/raw_pdfs/
    * IS_10500_Drinking_Water.pdf
    * IS_9873_Safety_of_Toys.pdf
    * IS_15885_LED_Drivers.pdf

Stage 2 - Run the ingestion pipeline (parse -> embed -> upsert)
    Uses the same code path as scripts/ingest_standards.py so the
    Qdrant vector store is instantly query-ready.

Usage
-----
    # From the backend/ root (venv activated)
    python -m scripts.seed_demo_data

    # Skip PDF generation (re-use existing PDFs) and re-ingest
    python -m scripts.seed_demo_data --skip-generate

    # Wipe the vector store then re-ingest
    python -m scripts.seed_demo_data --recreate

    # Only generate PDFs without ingesting
    python -m scripts.seed_demo_data --no-ingest

    # Dry-run: generate PDFs + parse without hitting Gemini/Qdrant
    python -m scripts.seed_demo_data --dry-run

    # Overwrite existing PDFs
    python -m scripts.seed_demo_data --overwrite-pdfs

Environment variables
---------------------
GOOGLE_API_KEY  : required (unless --dry-run)
QDRANT_PATH     : local storage path (default data/qdrant_storage)
"""

from __future__ import annotations

import argparse
import logging
import os
import re as _re
import sys
import time as _time
from pathlib import Path

from dotenv import load_dotenv

# ---- Path setup: allow  python -m scripts.seed_demo_data  from backend/ ----
_BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

load_dotenv(_BACKEND_ROOT / ".env", override=True)

# ---- Logging ----------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("seed_demo")

# ---- Constants --------------------------------------------------------------
DEFAULT_PDF_DIR = _BACKEND_ROOT / "data" / "raw_pdfs"


# =============================================================================
#  STAGE 1 - PDF GENERATION
# =============================================================================

def _make_pdf_builder():
    """
    Return a build_pdf() callable using reportlab.
    All reportlab imports are local so the module can be loaded without it.
    """
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
    )

    W, _H = A4
    MARGIN = 25 * mm

    DARK_BLUE  = colors.HexColor("#003366")
    MID_BLUE   = colors.HexColor("#1a5276")
    GOLD       = colors.HexColor("#b7950b")
    LIGHT_GREY = colors.HexColor("#f2f3f4")
    BORDER     = colors.HexColor("#aab7b8")

    base = getSampleStyleSheet()

    h_brand = ParagraphStyle("HBrand", parent=base["Normal"],
        fontSize=11, leading=14, textColor=GOLD, spaceAfter=4,
        alignment=TA_CENTER, fontName="Helvetica-Bold")
    h_title = ParagraphStyle("HTitle", parent=base["Title"],
        fontSize=20, leading=26, textColor=DARK_BLUE,
        spaceAfter=6, alignment=TA_CENTER)
    h_sub = ParagraphStyle("HSub", parent=base["Normal"],
        fontSize=12, leading=16, textColor=MID_BLUE,
        spaceAfter=8, alignment=TA_CENTER)
    h_code = ParagraphStyle("HCode", parent=base["Normal"],
        fontSize=11, leading=14, textColor=GOLD, spaceAfter=4,
        alignment=TA_CENTER, fontName="Helvetica-Bold")
    h1 = ParagraphStyle("BH1", parent=base["Heading1"],
        fontSize=13, leading=17, textColor=DARK_BLUE,
        spaceBefore=14, spaceAfter=4)
    h2 = ParagraphStyle("BH2", parent=base["Heading2"],
        fontSize=11, leading=15, textColor=MID_BLUE,
        spaceBefore=10, spaceAfter=3)
    body = ParagraphStyle("BBody", parent=base["Normal"],
        fontSize=9.5, leading=13.5, textColor=colors.black,
        spaceBefore=2, spaceAfter=4, alignment=TA_JUSTIFY)
    note = ParagraphStyle("BNote", parent=base["Normal"],
        fontSize=8.5, leading=12, textColor=colors.HexColor("#555555"),
        leftIndent=10, spaceBefore=2, spaceAfter=4,
        fontName="Helvetica-Oblique")
    t_cap = ParagraphStyle("TCap", parent=base["Normal"],
        fontSize=9.5, leading=13, textColor=DARK_BLUE,
        spaceBefore=8, spaceAfter=4, fontName="Helvetica-Bold")

    STYLES = dict(h1=h1, h2=h2, body=body, note=note, t_cap=t_cap)

    def _make_table(caption, headers, rows):
        elems = [Paragraph(caption, t_cap)]
        data = [headers] + rows
        ncol = len(headers)
        cw = (W - 2 * MARGIN) / ncol
        tbl = Table(data, colWidths=[cw] * ncol, repeatRows=1)
        tbl.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, 0),  DARK_BLUE),
            ("TEXTCOLOR",     (0, 0), (-1, 0),  colors.white),
            ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
            ("FONTSIZE",      (0, 0), (-1, 0),  8.5),
            ("ALIGN",         (0, 0), (-1, 0),  "CENTER"),
            ("TOPPADDING",    (0, 0), (-1, 0),  6),
            ("BOTTOMPADDING", (0, 0), (-1, 0),  6),
            ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, LIGHT_GREY]),
            ("FONTNAME",      (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE",      (0, 1), (-1, -1), 8),
            ("ALIGN",         (0, 1), (-1, -1), "LEFT"),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING",    (0, 1), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 1), (-1, -1), 3),
            ("LEFTPADDING",   (0, 0), (-1, -1), 5),
            ("GRID",          (0, 0), (-1, -1), 0.4, BORDER),
            ("BOX",           (0, 0), (-1, -1), 0.8, DARK_BLUE),
        ]))
        elems.append(tbl)
        elems.append(Spacer(1, 4 * mm))
        return elems

    def build_pdf(out_path, title, subtitle, is_code, content_fn):
        out_path.parent.mkdir(parents=True, exist_ok=True)
        doc = SimpleDocTemplate(str(out_path), pagesize=A4,
            leftMargin=MARGIN, rightMargin=MARGIN,
            topMargin=MARGIN, bottomMargin=MARGIN)

        story = [
            Spacer(1, 8 * mm),
            Paragraph("BUREAU OF INDIAN STANDARDS", h_brand),
            HRFlowable(width="100%", thickness=2, color=GOLD),
            Spacer(1, 6 * mm),
            Paragraph(title, h_title),
            Paragraph(subtitle, h_sub),
            Paragraph(is_code, h_code),
            HRFlowable(width="100%", thickness=1, color=BORDER),
            Spacer(1, 10 * mm),
        ]
        story.extend(content_fn(STYLES, _make_table))
        doc.build(story)
        logger.info("  Written: %s  (%d KB)",
                    out_path.name, out_path.stat().st_size // 1024)

    return build_pdf


# ---------------------------------------------------------------------------
# IS 10500 : 2012  -- Drinking Water
# ---------------------------------------------------------------------------

def _doc_drinking_water(S, mt):
    from reportlab.platypus import Paragraph, Spacer
    from reportlab.lib.units import mm

    def p(t, s="body"): return Paragraph(t, S[s])
    def sp(h=4):        return Spacer(1, h * mm)

    e = []

    # 1  Scope
    e += [
        p("1  Scope", "h1"),
        p("1.1  This standard lays down the requirements for drinking water "
          "supplied to the consumer. It specifies physical, chemical, "
          "organoleptic, bacteriological and radiological requirements that "
          "drinking water shall conform to in order to be safe and suitable "
          "for human consumption.", "body"),
        p("1.2  The limits specified in this standard are applicable to all "
          "piped and packaged drinking water intended for human consumption, "
          "including water treated at household level.", "body"),
        p("NOTE  For water from natural springs and mineral water, refer to "
          "IS 13428.", "note"),
        sp(),
    ]

    # 2  References
    e += [
        p("2  References", "h1"),
        p("The following Indian Standards contain provisions which, through "
          "reference in this text, constitute provisions of this standard. "
          "All standards are subject to revision and parties to agreements "
          "based on this standard are encouraged to apply the most recent "
          "editions of the standards listed below.", "body"),
        p("IS 3025 (Part 4) : 1983  -  Methods of sampling and test for "
          "water and wastewater: Measurement of pH.", "body"),
        p("IS 3025 (Part 17) : 1984  -  Acidity of water.", "body"),
        p("IS 3025 (Part 21) : 1983  -  Hardness.", "body"),
        sp(),
    ]

    # 3  Terminology
    e += [
        p("3  Terminology", "h1"),
        p("3.1  Acceptable Limit  -  The value below which no adverse health "
          "effect is expected for lifetime consumption. Values above the "
          "acceptable limit but below the permissible limit may be used if no "
          "better source is available.", "body"),
        p("3.2  Permissible Limit  -  The value below which water may be used "
          "in absence of any better alternative source. Above this limit, the "
          "water is considered hazardous to health.", "body"),
        p("3.3  Essential Characteristic  -  Any requirement whose "
          "non-compliance would render the water unacceptable for human "
          "consumption regardless of circumstances.", "body"),
        sp(),
    ]

    # 4  Requirements
    e += [p("4  Requirements", "h1")]

    e += [
        p("4.1  General", "h2"),
        p("4.1.1  Drinking water shall be free from suspended solids, "
          "pathogens, toxic chemicals, and radioactive substances at levels "
          "that could constitute a hazard to health. The water shall be "
          "clear, colourless, odourless and pleasant in taste.", "body"),
        p("4.1.2  Emergency Provisions  -  In emergency situations, some "
          "parameters may be relaxed by the competent authority provided "
          "adequate public health measures are in place.", "body"),
        sp(),
    ]

    e += [
        p("4.2  Organoleptic and Physical Characteristics", "h2"),
        p("4.2.1  The organoleptic and physical parameters of drinking water "
          "shall conform to the requirements given in Table 1.", "body"),
        p("4.2.2  Colour shall be determined by the method specified in "
          "IS 3025 (Part 4). Turbidity shall be measured in Nephelometric "
          "Turbidity Units (NTU).", "body"),
    ]
    e += mt(
        "Table 1  Organoleptic and Physical Requirements  (IS 10500:2012)",
        ["Sl. No.", "Characteristic", "Acceptable Limit", "Permissible Limit", "Method of Test"],
        [
            ["1", "Colour, Hazen units, Max",        "5",         "15",        "IS 3025 (Pt 4)"],
            ["2", "Odour",                            "Agreeable", "Agreeable", "IS 3025 (Pt 5)"],
            ["3", "Taste",                            "Agreeable", "Agreeable", "Organoleptic"],
            ["4", "Turbidity, NTU, Max",              "1",         "5",         "IS 3025 (Pt 10)"],
            ["5", "pH value",                         "6.5 to 8.5","No relax.", "IS 3025 (Pt 11)"],
            ["6", "Total Dissolved Solids, mg/L Max", "500",       "2000",      "IS 3025 (Pt 16)"],
            ["7", "Total Hardness as CaCO3, mg/L Max","200",       "600",       "IS 3025 (Pt 21)"],
            ["8", "Calcium as Ca, mg/L Max",          "75",        "200",       "IS 3025 (Pt 40)"],
            ["9", "Magnesium as Mg, mg/L Max",        "30",        "100",       "IS 3025 (Pt 46)"],
        ],
    )

    e += [
        p("4.3  Chemical Requirements - Non-toxic Substances", "h2"),
        p("4.3.1  The chemical (non-toxic) requirements shall conform to the "
          "limits specified. Substances listed are not toxic in themselves "
          "but can affect palatability or corrode distribution systems if "
          "present above the specified limits.", "body"),
        p("4.3.2  Iron (IS 3025 Part 53)  -  Max 0.3 mg/L acceptable; "
          "1.0 mg/L permissible. Excessive iron causes discolouration and "
          "an unpleasant metallic taste.", "body"),
        p("4.3.3  Chloride as Cl (IS 3025 Part 32)  -  Max 250 mg/L "
          "acceptable; 1000 mg/L permissible.", "body"),
        sp(),
    ]

    # 5  Bacteriological
    e += [
        p("5  Bacteriological Requirements", "h1"),
        p("5.1  Treated water entering the distribution system", "h2"),
        p("5.1.1  Escherichia coli or thermotolerant coliform bacteria must "
          "not be detectable in any 100 mL sample.", "body"),
        p("5.1.2  Total coliform bacteria must not be detectable in any "
          "100 mL sample.", "body"),
        sp(),
        p("5.2  Treated water in the distribution system", "h2"),
        p("5.2.1  E. coli or thermotolerant coliform bacteria must not be "
          "detectable in any 100 mL sample.", "body"),
        p("5.2.2  Coliform bacteria shall not be detectable in 95 percent "
          "of samples taken throughout the year in any 12-month period for "
          "large supplies.", "body"),
        sp(),
    ]

    # 6  Radiological
    e += [
        p("6  Radiological Requirements", "h1"),
        p("6.1  Gross Alpha Activity  -  The indicative dose for gross alpha "
          "activity shall not exceed 0.1 Bq/litre.", "body"),
        p("6.2  Gross Beta Activity  -  The indicative dose for gross beta "
          "activity shall not exceed 1.0 Bq/litre.", "body"),
        p("6.3  Where either of the above screening values is exceeded, a "
          "more detailed radiological analysis shall be conducted for "
          "specific radionuclides before the water is deemed unsafe.", "body"),
        sp(),
    ]

    # Table 2  Toxic substances
    e += mt(
        "Table 2  Toxic Substances - Maximum Permissible Concentrations  (IS 10500:2012)",
        ["Sl. No.", "Substance", "Max. Permissible Limit (mg/L)", "Method of Test (IS 3025)"],
        [
            ["1",  "Arsenic (As)",     "0.01",  "Part 37"],
            ["2",  "Cadmium (Cd)",     "0.003", "Part 41"],
            ["3",  "Chromium (Cr-VI)", "0.05",  "Part 52"],
            ["4",  "Cyanide (CN)",     "0.05",  "Part 27"],
            ["5",  "Fluoride (F)",     "1.0",   "Part 60"],
            ["6",  "Lead (Pb)",        "0.01",  "Part 47"],
            ["7",  "Mercury (Hg)",     "0.001", "Part 48"],
            ["8",  "Nitrate (NO3)",    "45",    "Part 34"],
            ["9",  "Nitrite (NO2)",    "0.02",  "Part 34"],
            ["10", "Selenium (Se)",    "0.01",  "Part 62"],
            ["11", "Barium (Ba)",      "0.7",   "Part 63"],
            ["12", "Antimony (Sb)",    "0.005", "Part 64"],
            ["13", "Bromate (BrO3)",   "0.01",  "Part 65"],
        ],
    )

    return e


# ---------------------------------------------------------------------------
# IS 9873 : 2017  -- Safety of Toys
# ---------------------------------------------------------------------------

def _doc_toys_safety(S, mt):
    from reportlab.platypus import Paragraph, Spacer
    from reportlab.lib.units import mm

    def p(t, s="body"): return Paragraph(t, S[s])
    def sp(h=4):        return Spacer(1, h * mm)

    e = []

    e += [
        p("1  Scope", "h1"),
        p("1.1  This standard specifies requirements and test methods for "
          "toys intended for children up to 14 years of age. The purpose is "
          "to protect children from hazards that may arise from toys during "
          "use, foreseeable misuse, or ingestion of parts.", "body"),
        p("1.2  This standard covers mechanical and physical properties, "
          "flammability characteristics, chemical requirements, electrical "
          "properties, and hygiene requirements.", "body"),
        p("NOTE  The following products are excluded from scope: sports "
          "equipment (skates, skateboards), bicycles, video game consoles, "
          "and collectible scale models.", "note"),
        sp(),
        p("2  Definitions", "h1"),
        p("2.1  Toy  -  Any product or material designed or clearly intended "
          "for use in play by children under 14 years of age.", "body"),
        p("2.2  Small Part  -  Any part or component of a toy that is "
          "completely enclosed in the small parts cylinder as specified in "
          "Clause 5.2 when tested according to the method therein.", "body"),
        p("2.3  Small Part Cylinder  -  A cylinder 57.1 mm long and 31.7 mm "
          "in internal diameter, open at one end, with the closed end formed "
          "by a cylinder inclined at 45 degrees.", "body"),
        p("2.4  Accessible  -  Able to be contacted by a test probe as "
          "specified in Annex A of this standard.", "body"),
        sp(),
        p("3  Age Grading", "h1"),
        p("3.1  The manufacturer shall specify the intended age range for "
          "each toy. Age grading shall be based on developmental stage, "
          "including cognitive, physical and emotional development.", "body"),
        p("3.2  Toys intended for children under 36 months (3 years) shall "
          "be labelled accordingly and shall comply with the enhanced "
          "requirements specified in Clause 4.3.", "body"),
        sp(),
        p("4  Mechanical and Physical Requirements", "h1"),
        p("4.1  General", "h2"),
        p("4.1.1  Toys and their components shall withstand the mechanical "
          "and physical tests specified in this clause without giving rise "
          "to hazards. Hazards to be prevented include sharp edges and "
          "sharp points, small parts that could be swallowed, strangulation "
          "risks from long cords and loops, and projectile hazards.", "body"),
        sp(),
        p("4.2  Sharp Edges and Points", "h2"),
        p("4.2.1  After the drop test and torque test, toys shall not have "
          "accessible edges that present a cutting hazard when assessed by "
          "the edge tester defined in IS 9873 (Part 1).", "body"),
        p("4.2.2  Rigid wire or rod-type accessible points shall not "
          "penetrate to the bottom of the Point Test Gauge.", "body"),
        p("4.2.3  The edge tester shall apply a force of 1 N +/- 0.1 N in "
          "the direction perpendicular to the edge.", "body"),
    ]
    e += mt(
        "Table 1  Mechanical Test Summary - Applicable Age Groups  (IS 9873:2017)",
        ["Test", "Method Clause", "< 18 months", "18-36 months", "3-6 years", "7-14 years"],
        [
            ["Drop Test",           "5.3", "Yes", "Yes", "Yes", "Optional"],
            ["Torque Test",         "5.4", "Yes", "Yes", "Yes", "No"],
            ["Tension/Compression", "5.5", "Yes", "Yes", "No",  "No"],
            ["Sharp Edge Check",    "5.6", "Yes", "Yes", "Yes", "Yes"],
            ["Sharp Point Check",   "5.7", "Yes", "Yes", "Yes", "Yes"],
            ["Small Parts Check",   "5.8", "Yes", "Yes", "No",  "No"],
            ["Bite Test",           "5.9", "Yes", "No",  "No",  "No"],
        ],
    )

    e += [
        p("4.3  Requirements for Toys for Children Under 36 Months", "h2"),
        p("4.3.1  Small parts  -  Toys intended for children under 36 months "
          "shall not include small parts that fit entirely within the small "
          "parts cylinder.", "body"),
        p("4.3.2  Squeeze toys  -  Squeeze toys that can be mouthed shall "
          "not present a suffocation risk. The minimum opening of any "
          "aperture after compression shall not exceed 10 mm.", "body"),
        p("4.3.3  Long flexible parts  -  Cords, strings, and elastic shall "
          "not exceed 300 mm in free length for toys for children under "
          "36 months.", "body"),
        sp(),
        p("5  Flammability", "h1"),
        p("5.1  General Requirements", "h2"),
        p("5.1.1  Toys shall not constitute a fire or burn hazard by "
          "themselves or when exposed to other ignition sources normally "
          "present in children play environments.", "body"),
        p("5.1.2  Materials used in the construction of toys shall comply "
          "with at least one of the categories specified in Table 2.", "body"),
    ]
    e += mt(
        "Table 2  Flammability Categories and Burning Rate Limits  (IS 9873:2017)",
        ["Category", "Material Type", "Max Burning Rate (mm/s)", "Test Method"],
        [
            ["F1", "Pile fabrics and napped textiles",  "30", "IS 9873 (Pt 2) Cl. 6.1"],
            ["F2", "Solid non-metallic materials",       "50", "IS 9873 (Pt 2) Cl. 6.2"],
            ["F3", "Hair, beard, moustache materials",   "30", "IS 9873 (Pt 2) Cl. 6.3"],
            ["F4", "Thin flexible non-metallic sheet",   "50", "IS 9873 (Pt 2) Cl. 6.4"],
            ["F5", "Costumes and fancy dress outfits",   "30", "IS 9873 (Pt 2) Cl. 6.5"],
        ],
    )
    e += [
        p("5.2  Specific Prohibitions", "h2"),
        p("5.2.1  Cellulose nitrate shall not be used in the construction "
          "of toys.", "body"),
        p("5.2.2  Toys shall not contain flammable liquid propellants.", "body"),
        sp(),
        p("6  Chemical Requirements", "h1"),
        p("6.1  Migration Limits for Accessible Substrate Materials", "h2"),
        p("6.1.1  The limits specified in Table 3 shall not be exceeded "
          "when tested per IS 9873 (Part 3).", "body"),
    ]
    e += mt(
        "Table 3  Element Migration Limits - Accessible Toy Materials (mg/kg)  (IS 9873:2017)",
        ["Element", "Scraped-off Material", "Dry / Brittle Material", "Liquid / Sticky Material"],
        [
            ["Aluminium (Al)",  "5625",  "1406",  "70000"],
            ["Antimony (Sb)",   "45",    "11.3",  "560"],
            ["Arsenic (As)",    "3.8",   "0.9",   "47"],
            ["Barium (Ba)",     "4500",  "1125",  "56000"],
            ["Boron (B)",       "1200",  "300",   "15000"],
            ["Cadmium (Cd)",    "1.9",   "0.5",   "23"],
            ["Chromium III",    "37.5",  "9.4",   "460"],
            ["Chromium VI",     "0.02",  "0.005", "0.2"],
            ["Cobalt (Co)",     "10.5",  "2.6",   "130"],
            ["Lead (Pb)",       "2.0",   "0.5",   "23"],
            ["Mercury (Hg)",    "7.5",   "1.9",   "94"],
            ["Nickel (Ni)",     "75",    "18.8",  "930"],
            ["Selenium (Se)",   "37.5",  "9.4",   "460"],
            ["Strontium (Sr)",  "4500",  "1125",  "56000"],
            ["Tin (Sn)",        "15000", "3750",  "180000"],
        ],
    )

    return e


# ---------------------------------------------------------------------------
# IS 15885 : 2021  -- LED Drivers (CRS Electronics Standard)
# ---------------------------------------------------------------------------

def _doc_led_drivers(S, mt):
    from reportlab.platypus import Paragraph, Spacer
    from reportlab.lib.units import mm

    def p(t, s="body"): return Paragraph(t, S[s])
    def sp(h=4):        return Spacer(1, h * mm)

    e = []

    e += [
        p("1  Scope", "h1"),
        p("1.1  This standard specifies safety and performance requirements "
          "for electronic control gear (drivers) for LED modules and LED "
          "lamps intended for use with supply voltages up to 1000 V AC or "
          "1500 V DC at frequencies up to 1000 Hz.", "body"),
        p("1.2  This standard applies to LED drivers for general lighting "
          "purposes in indoor and outdoor luminaires. It covers both "
          "constant-voltage (CV) and constant-current (CC) driver types.", "body"),
        p("1.3  This standard forms part of the Compulsory Registration "
          "Scheme (CRS) for electronics and IT goods under the Bureau of "
          "Indian Standards Act 2016. Compliance is mandatory before placing "
          "products on the Indian market.", "body"),
        p("NOTE  LED modules and luminaires containing integral drivers are "
          "covered in IS 10322 (Part 5). This standard applies only to the "
          "driver unit tested as a separate component.", "note"),
        sp(),
        p("2  Normative References", "h1"),
        p("IS 302 (Part 1) : 2008  -  Safety of household and similar "
          "electrical appliances: General Requirements.", "body"),
        p("IS 15111 : 2012  -  Safety of transformers, reactors, power "
          "supply units and combinations - General requirements and tests.", "body"),
        p("IS 16024 : 2012  -  LED modules for general lighting - Safety "
          "specifications.", "body"),
        p("IEC 61347-1 : 2015  -  Lamp controlgear - Part 1: General and "
          "safety requirements.", "body"),
        sp(),
        p("3  Definitions", "h1"),
        p("3.1  LED Driver  -  An electronic device that regulates the power "
          "delivered to an LED module or LED array; it may incorporate "
          "dimming, thermal management, and power factor correction.", "body"),
        p("3.2  Constant Current (CC) Driver  -  A driver that maintains a "
          "constant output current over a specified range of output voltage.", "body"),
        p("3.3  Constant Voltage (CV) Driver  -  A driver that maintains a "
          "constant output voltage over a specified range of output current.", "body"),
        p("3.4  Rated Output Current  -  The nominal value of the output "
          "current declared by the manufacturer.", "body"),
        p("3.5  Power Factor (PF)  -  The ratio of active power consumed to "
          "the apparent power; the minimum PF is specified in Table 1 "
          "according to rated output power.", "body"),
        sp(),
        p("4  Classification", "h1"),
        p("4.1  LED drivers shall be classified by: output type (CC or CV); "
          "rated output power bracket; protection class (Class I, II, or III); "
          "and degree of protection (IP20, IP44, IP65, IP67).", "body"),
        sp(),
        p("5  General Requirements", "h1"),
        p("5.1  Marking and Documentation", "h2"),
        p("5.1.1  Each LED driver shall be permanently and legibly marked "
          "with: supply voltage and frequency; rated output current or "
          "voltage; protection class symbol; IP rating; manufacturer name "
          "or trademark; and ISI mark confirming compliance with this "
          "standard.", "body"),
        p("5.1.2  The BIS Registration Number obtained under the CRS Order "
          "shall be clearly marked on the driver or its immediate "
          "packaging.", "body"),
        sp(),
        p("5.2  Electrical Safety Requirements", "h2"),
        p("5.2.1  Dielectric strength  -  LED drivers shall withstand a "
          "dielectric strength test at 1500 V AC (or 2125 V DC) for "
          "1 minute between input and output circuits without breakdown.", "body"),
        p("5.2.2  Insulation resistance  -  Insulation resistance between "
          "live parts and accessible metal parts shall not be less than "
          "2 MOhm when measured with a 500 V DC instrument.", "body"),
        p("5.2.3  Earth continuity  -  For Class I constructions, the "
          "resistance between the earth terminal and any accessible metal "
          "part shall not exceed 0.1 Ohm.", "body"),
        sp(),
        p("6  Performance Requirements", "h1"),
        p("6.1  Efficiency and Power Factor", "h2"),
        p("6.1.1  The minimum efficiency and power factor shall comply with "
          "the values given in Table 1 at rated input voltage and rated "
          "output load.", "body"),
    ]
    e += mt(
        "Table 1  Minimum Efficiency and Power Factor Requirements  (IS 15885:2021)",
        ["Rated Output Power (W)", "Min. Efficiency (%)", "Min. Power Factor", "Test Condition"],
        [
            ["5 or less",           "70", "0.50", "Full load, 230 V, 50 Hz"],
            ["More than 5 to 10",   "75", "0.70", "Full load, 230 V, 50 Hz"],
            ["More than 10 to 25",  "80", "0.90", "Full load, 230 V, 50 Hz"],
            ["More than 25 to 50",  "85", "0.90", "Full load, 230 V, 50 Hz"],
            ["More than 50 to 100", "87", "0.92", "Full load, 230 V, 50 Hz"],
            ["More than 100",       "88", "0.95", "Full load, 230 V, 50 Hz"],
        ],
    )

    e += [
        p("6.2  Output Regulation", "h2"),
        p("6.2.1  Current regulation  -  For CC drivers, the output current "
          "shall not deviate by more than 5 percent of the rated output "
          "current when the input voltage varies from 90 percent to 110 "
          "percent of rated supply voltage.", "body"),
        p("6.2.2  Voltage regulation  -  For CV drivers, the output voltage "
          "shall not deviate by more than 5 percent of the rated output "
          "voltage across 0 to 100 percent of rated output current.", "body"),
        sp(),
        p("6.3  Thermal Requirements", "h2"),
        p("6.3.1  The temperature at any accessible surface of the driver "
          "shall not exceed the limits given in Table 2 during steady-state "
          "operation at rated conditions.", "body"),
    ]
    e += mt(
        "Table 2  Maximum Accessible Surface Temperature Limits  (IS 15885:2021)",
        ["Surface / Location", "Max Temperature (deg C)", "Test Method"],
        [
            ["Metal surfaces (unintentionally touchable)",    "60",  "Clause 8.3"],
            ["Non-metal surfaces (unintentionally touchable)","75",  "Clause 8.3"],
            ["Surfaces intended to be touched",              "48",  "Clause 8.3"],
            ["Internal winding - Class E",                   "120", "Clause 8.4"],
            ["Internal winding - Class B",                   "130", "Clause 8.4"],
            ["Internal winding - Class F",                   "155", "Clause 8.4"],
            ["Internal winding - Class H",                   "180", "Clause 8.4"],
        ],
    )

    e += [
        p("6.4  Electromagnetic Compatibility (EMC)", "h2"),
        p("6.4.1  Conducted emission limits for Class B equipment as per "
          "IS 13252 (Part 1) shall be met when tested over the frequency "
          "range 150 kHz to 30 MHz.", "body"),
        p("6.4.2  Harmonic current limits shall comply with IS 16604 "
          "(equivalent to IEC 61000-3-2 Class C) for rated active input "
          "power above 25 W.", "body"),
        sp(),
        p("7  Compulsory Registration Scheme (CRS) Requirements", "h1"),
        p("7.1  Registration obligation  -  LED drivers covered by this "
          "standard fall under the Electronics and Information Technology "
          "Goods (Compulsory Registration) Order. No such product may be "
          "imported, sold, or stocked for sale in India without a valid "
          "BIS Registration Certificate.", "body"),
        p("7.2  Testing laboratory  -  All tests required for registration "
          "shall be conducted at a BIS-recognised test laboratory or "
          "NABL-accredited laboratory with the relevant scope.", "body"),
        p("7.3  Factory inspection  -  BIS shall carry out factory "
          "inspections and market surveillance as deemed necessary. The "
          "registered applicant shall maintain quality records as specified "
          "in Annex B for a minimum period of five years.", "body"),
        p("7.4  Self-Declaration of Conformity (SDoC) based on this "
          "standard does NOT satisfy the CRS requirement; mandatory "
          "third-party certification by BIS is required.", "body"),
        sp(),
        p("8  Test Methods", "h1"),
        p("8.1  Sample size  -  Unless otherwise specified, tests shall be "
          "performed on a minimum of three samples representative of the "
          "production batch.", "body"),
        p("8.2  Input conditions  -  Tests shall be carried out at "
          "230 V +/- 2 percent, 50 Hz +/- 1 percent unless otherwise "
          "specified in the relevant test clause.", "body"),
        p("8.3  Surface temperature measurement  -  Measure using calibrated "
          "thermocouples or calibrated non-contact infrared thermometer at "
          "thermal steady state (temperature variation less than 1 deg C "
          "over 30 min).", "body"),
        p("8.4  Winding temperature measurement  -  Determine winding "
          "temperature by the resistance method as specified in IS 15111.", "body"),
    ]

    return e


# ---------------------------------------------------------------------------
# PDF spec list
# ---------------------------------------------------------------------------

_PDF_SPECS = [
    {
        "filename":   "IS_10500_Drinking_Water.pdf",
        "title":      "Drinking Water - Specification",
        "subtitle":   "Fifth Revision",
        "is_code":    "IS 10500 : 2012",
        "content_fn": _doc_drinking_water,
    },
    {
        "filename":   "IS_9873_Safety_of_Toys.pdf",
        "title":      "Safety of Toys",
        "subtitle":   "Part 1: Mechanical and Physical Properties, Part 2: Flammability",
        "is_code":    "IS 9873 : 2017",
        "content_fn": _doc_toys_safety,
    },
    {
        "filename":   "IS_15885_LED_Drivers.pdf",
        "title":      "Safety of Electronic Control Gear for LED Modules (LED Drivers)",
        "subtitle":   "CRS Compulsory Registration Scheme - Electronics Standard",
        "is_code":    "IS 15885 : 2021",
        "content_fn": _doc_led_drivers,
    },
]


def generate_pdfs(pdf_dir: Path, overwrite: bool = False) -> list[Path]:
    """Generate all demo BIS PDFs into pdf_dir. Returns list of paths written."""
    build_pdf = _make_pdf_builder()  # raises ImportError if reportlab missing

    written: list[Path] = []
    pdf_dir.mkdir(parents=True, exist_ok=True)

    for spec in _PDF_SPECS:
        out = pdf_dir / spec["filename"]
        if out.exists() and not overwrite:
            logger.info("  Skipping (exists): %s", spec["filename"])
            continue
        logger.info("  Generating: %s ...", spec["filename"])
        build_pdf(
            out_path=out,
            title=spec["title"],
            subtitle=spec["subtitle"],
            is_code=spec["is_code"],
            content_fn=spec["content_fn"],
        )
        written.append(out)

    return written


# =============================================================================
#  STAGE 2 - INGESTION PIPELINE
# =============================================================================

# Category hints - covers three new demo standards plus the originals
_CATEGORY_HINTS: dict[str, str] = {
    "10500": "Drinking Water",
    "9873":  "Safety of Toys",
    "15885": "LED Drivers",
    "2062":  "Structural Steel",
    "12778": "Helmets",
    "1786":  "High Strength Deformed Steel Bars",
    "432":   "Mild Steel",
    "3696":  "Safety Matches",
    "1844":  "Rubber Hoses",
    "8183":  "Bonded Mineral Fibre",
    "14846": "Household LPG Regulators",
    "4246":  "Pressure Cookers",
    "302":   "Household Electrical Appliances",
    "616":   "Incandescent Lamps",
    "694":   "PVC Insulated Cables",
    "9431":  "Jute Sacking Bags",
    "1077":  "Common Burnt Clay Bricks",
}


def _infer_category(code: str) -> str:
    m = _re.search(r"IS\s+([\d]+)", code, _re.IGNORECASE)
    if m:
        return _CATEGORY_HINTS.get(m.group(1), code)
    return code


def _build_embed_text(chunk: dict) -> str:
    parts = []
    if chunk.get("standard_code"):
        parts.append(chunk["standard_code"])
    if chunk.get("clause_number") and chunk.get("clause_title"):
        parts.append(f"§ {chunk['clause_number']} {chunk['clause_title']}")
    elif chunk.get("clause_number"):
        parts.append(f"§ {chunk['clause_number']}")
    if chunk.get("content"):
        parts.append(chunk["content"])
    return "\n".join(parts)


def _embed_batch(client, texts: list[str]) -> list[list[float]]:
    from google.genai import types as genai_types
    BATCH = int(os.getenv("EMBED_BATCH_SIZE", "50"))
    all_vecs: list[list[float]] = []
    total = len(texts)
    for start in range(0, total, BATCH):
        batch = texts[start: start + BATCH]
        logger.info("  Embedding %d-%d of %d ...", start + 1, start + len(batch), total)
        try:
            resp = client.models.embed_content(
                model="text-embedding-004",
                contents=batch,
                config=genai_types.EmbedContentConfig(
                    task_type="RETRIEVAL_DOCUMENT",
                    output_dimensionality=768,
                ),
            )
            all_vecs.extend([e.values for e in resp.embeddings])
        except Exception as exc:
            logger.error("Embedding API error: %s", exc)
            all_vecs.extend([[0.0] * 768] * len(batch))
        _time.sleep(0.5)  # rate-limit safety
    return all_vecs


def run_ingestion(pdf_dir: Path, recreate: bool, dry_run: bool) -> int:
    """
    Parse -> embed -> upsert pipeline for all PDFs in pdf_dir.
    Returns exit code (0 = success, 1 = errors).
    """
    from app.utils.pdf_parser import parse_is_document
    from app.services.vector_service import VectorService

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key and not dry_run:
        logger.error(
            "GOOGLE_API_KEY is not set.\n"
            "  Windows: set GOOGLE_API_KEY=your-key\n"
            "  Linux/macOS: export GOOGLE_API_KEY=your-key"
        )
        return 1

    pdfs = sorted(pdf_dir.glob("*.pdf"))
    if not pdfs:
        logger.warning("No PDFs found in %s - nothing to ingest.", pdf_dir)
        return 0
    logger.info("Found %d PDF(s) to ingest in %s", len(pdfs), pdf_dir)

    # Initialise clients
    gemini = None
    vector_svc = None

    if not dry_run:
        from google import genai
        gemini = genai.Client(api_key=api_key)
        logger.info("Gemini client initialised (model: text-embedding-004)")

        vector_svc = VectorService.from_env()
        if recreate:
            logger.warning("--recreate: dropping existing Qdrant collection ...")
            vector_svc.recreate_collection()
        info = vector_svc.get_collection_info()
        logger.info("Qdrant collection '%s' - %d existing points",
                    info["name"], info["points_count"])

    # Process each PDF
    total_parsed = 0
    total_upserted = 0
    failed: list[str] = []
    t0 = _time.perf_counter()

    for pdf_path in pdfs:
        logger.info("--- Processing: %s", pdf_path.name)

        try:
            chunks = parse_is_document(pdf_path)
        except Exception as exc:
            logger.error("Parse error on '%s': %s", pdf_path.name, exc)
            failed.append(pdf_path.name)
            continue

        if not chunks:
            logger.warning("No chunks from '%s' - skipping.", pdf_path.name)
            continue

        logger.info("  Parsed %d clause chunks.", len(chunks))
        total_parsed += len(chunks)

        std_code = chunks[0].get("standard_code", "") if chunks else ""
        category = _infer_category(std_code)
        for c in chunks:
            c["product_category"] = category
            c["source_file"] = pdf_path.name

        if dry_run:
            logger.info("  [DRY RUN] Skipping embedding (category=%s).", category)
            continue

        embed_texts = [_build_embed_text(c) for c in chunks]
        vectors = _embed_batch(gemini, embed_texts)

        if len(vectors) != len(chunks):
            logger.error("Vector/chunk mismatch for '%s' - skipping upsert.", pdf_path.name)
            failed.append(pdf_path.name)
            continue

        upserted = vector_svc.upsert_chunks(chunks, vectors)
        total_upserted += upserted
        logger.info("  OK  Upserted %d vectors  [category: %s]", upserted, category)

    elapsed = _time.perf_counter() - t0

    # Summary
    logger.info("=" * 60)
    logger.info("Ingestion complete in %.1f s", elapsed)
    logger.info("  PDFs processed : %d", len(pdfs) - len(failed))
    logger.info("  Chunks parsed  : %d", total_parsed)
    if not dry_run:
        logger.info("  Vectors stored : %d", total_upserted)
        if vector_svc:
            info = vector_svc.get_collection_info()
            logger.info("  Collection total: %d points", info["points_count"])
    if failed:
        logger.warning("  Failed files   : %s", ", ".join(failed))

    return 1 if failed else 0


# =============================================================================
#  ENTRY POINT
# =============================================================================

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate demo BIS PDFs and ingest them into Qdrant.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--pdf-dir", default=str(DEFAULT_PDF_DIR), metavar="DIR",
        help=f"Directory for PDF files (default: {DEFAULT_PDF_DIR})")
    parser.add_argument("--skip-generate", action="store_true",
        help="Skip PDF generation - reuse any existing PDFs.")
    parser.add_argument("--overwrite-pdfs", action="store_true",
        help="Overwrite existing PDFs during generation.")
    parser.add_argument("--no-ingest", action="store_true",
        help="Only generate PDFs; do NOT run the ingestion pipeline.")
    parser.add_argument("--recreate", action="store_true",
        help="Drop and recreate the Qdrant collection before ingesting.")
    parser.add_argument("--dry-run", action="store_true",
        help="Generate PDFs + parse + build embed texts, but make no API calls.")
    args = parser.parse_args(argv)

    pdf_dir = Path(args.pdf_dir)

    # Stage 1: Generate PDFs
    if not args.skip_generate:
        logger.info("=" * 60)
        logger.info("STAGE 1  Generating BIS reference PDFs into: %s", pdf_dir)
        logger.info("=" * 60)
        try:
            written = generate_pdfs(pdf_dir, overwrite=args.overwrite_pdfs)
            if written:
                logger.info("Generated %d new PDF(s).", len(written))
            else:
                logger.info("All PDFs already exist "
                            "(pass --overwrite-pdfs to regenerate).")
        except ImportError:
            logger.error("reportlab not found. Install with:  pip install reportlab")
            return 1
        except Exception as exc:
            logger.error("PDF generation failed: %s", exc)
            return 1
    else:
        logger.info("--skip-generate: skipping PDF generation.")

    # Stage 2: Ingest
    if args.no_ingest:
        logger.info("--no-ingest: stopping after PDF generation.")
        return 0

    logger.info("=" * 60)
    logger.info("STAGE 2  Ingesting PDFs into Qdrant vector store ...")
    logger.info("=" * 60)
    return run_ingestion(
        pdf_dir=pdf_dir,
        recreate=args.recreate,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    sys.exit(main())
