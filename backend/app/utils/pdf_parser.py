"""
app/utils/pdf_parser.py
───────────────────────
Parser for Indian Standard (IS) PDF documents.

Extracts structured chunks using:
  • PyMuPDF  (fitz)      – fast per-page text + font-size metadata
  • pdfplumber            – precise table cell extraction

Output schema per chunk
-----------------------
{
    "standard_code": "IS 10500:2012",
    "clause_number": "4.2.1",
    "clause_title":  "Bacteriological Quality",
    "content":       "...",   # plain text or markdown table
    "page_number":   7,
}
"""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import TypedDict

import fitz          # PyMuPDF
import pdfplumber

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Output schema
# ---------------------------------------------------------------------------

class ISChunk(TypedDict):
    standard_code: str
    clause_number: str
    clause_title: str
    content: str
    page_number: int


# ---------------------------------------------------------------------------
# Internal representation
# ---------------------------------------------------------------------------

@dataclass
class _Block:
    """A raw block of text or a table extracted from one PDF page."""
    page_number: int
    text: str
    is_table: bool = False


@dataclass
class _RawClause:
    number: str
    title: str
    content_lines: list = field(default_factory=list)
    page_number: int = 0
    kind: str = "clause"   # "clause" | "annex" | "table" | "figure"


# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

# IS header: "IS 10500 : 2012", "IS/IEC 62305-1 : 2010", "IS 875 (Part 1) : 1987"
_IS_HEADER_RE = re.compile(
    r"\bIS(?:/[A-Z]+)?\s+[\d]+(?:\s*\([^)]+\))?\s*(?::\s*\d{4})?\b",
    re.IGNORECASE,
)

# Clause patterns — ordered most-specific to least-specific
_CLAUSE_PATTERNS = [
    ("annex",  re.compile(r"^Annex\s+([A-Z](?:\s*\([^)]+\))?)\s*$", re.MULTILINE)),
    ("table",  re.compile(r"^Table\s+([\dA-Z][\d\-\.]*)\b", re.MULTILINE)),
    ("figure", re.compile(r"^Fig(?:ure)?\.?\s+([\dA-Z][\d\-\.]*)\b", re.MULTILINE)),
    ("clause", re.compile(r"^(\d+(?:\.\d+){2,})\s+(.+)", re.MULTILINE)),   # 4.2.3.1
    ("clause", re.compile(r"^(\d+\.\d+)\s+(.+)", re.MULTILINE)),            # 4.2
    ("clause", re.compile(r"^(\d+)\s{2,}(.+)", re.MULTILINE)),              # 4  Title
]

_IS_CODE_NORMALISE_RE = re.compile(r"\s*:\s*")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalise_is_code(raw: str) -> str:
    return _IS_CODE_NORMALISE_RE.sub(":", raw.strip())


def _detect_standard_code(text: str) -> str:
    m = _IS_HEADER_RE.search(text)
    return _normalise_is_code(m.group()) if m else ""


def _table_to_markdown(table: list) -> str:
    """Convert a pdfplumber table to a GitHub-style markdown grid."""
    if not table:
        return ""

    cleaned = []
    for row in table:
        cleaned.append([
            str(cell).replace("\n", " ").strip() if cell is not None else ""
            for cell in row
        ])

    col_count = max(len(r) for r in cleaned)
    widths = [0] * col_count
    for row in cleaned:
        for i, cell in enumerate(row):
            if i < col_count:
                widths[i] = max(widths[i], len(cell))

    def fmt_row(row):
        padded = [
            row[i].ljust(widths[i]) if i < len(row) else " " * widths[i]
            for i in range(col_count)
        ]
        return "| " + " | ".join(padded) + " |"

    separator = "| " + " | ".join("-" * w for w in widths) + " |"

    lines = [fmt_row(cleaned[0]), separator]
    for row in cleaned[1:]:
        lines.append(fmt_row(row))
    return "\n".join(lines)


def _extract_tables_by_page(pdf_path: Path) -> dict:
    """Return {page_number: [markdown_table, ...]} via pdfplumber."""
    result = {}
    try:
        with pdfplumber.open(str(pdf_path)) as pdf:
            for idx, page in enumerate(pdf.pages, start=1):
                raw_tables = page.extract_tables(
                    table_settings={
                        "vertical_strategy":   "lines",
                        "horizontal_strategy": "lines",
                        "snap_tolerance":      3,
                        "join_tolerance":      3,
                        "min_words_vertical":  1,
                        "min_words_horizontal": 1,
                    }
                )
                md = [_table_to_markdown(t) for t in raw_tables if t]
                if md:
                    result[idx] = md
    except Exception as exc:
        logger.warning("pdfplumber error: %s", exc)
    return result


def _extract_text_blocks(pdf_path: Path) -> list:
    """Return [_Block, ...] one per page via PyMuPDF."""
    blocks = []
    try:
        doc = fitz.open(str(pdf_path))
        for idx, page in enumerate(doc, start=1):
            raw = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]
            lines = []
            for blk in raw:
                if blk.get("type") != 0:
                    continue
                for ln in blk.get("lines", []):
                    line_text = "".join(
                        span.get("text", "") for span in ln.get("spans", [])
                    )
                    lines.append(line_text)
            text = "\n".join(lines).strip()
            if text:
                blocks.append(_Block(page_number=idx, text=text))
        doc.close()
    except Exception as exc:
        logger.error("PyMuPDF error: %s", exc)
    return blocks


# ---------------------------------------------------------------------------
# Clause splitting
# ---------------------------------------------------------------------------

def _split_into_clauses(page_text: str, page_number: int) -> list:
    """Parse one page of text into _RawClause fragments."""
    lines = page_text.splitlines()
    clauses = []
    current = None

    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        matched = False

        for kind, pattern in _CLAUSE_PATTERNS:
            m = pattern.match(line)
            if not m:
                continue

            if current is not None:
                clauses.append(current)

            if kind == "annex":
                number = "Annex " + m.group(1).strip()
                title = ""
                if i + 1 < len(lines) and lines[i + 1].strip():
                    i += 1
                    title = lines[i].strip()
                current = _RawClause(number=number, title=title,
                                     page_number=page_number, kind="annex")

            elif kind == "table":
                number = "Table " + m.group(1).strip()
                rest = line[m.end():].strip()
                if not rest and i + 1 < len(lines):
                    i += 1
                    rest = lines[i].strip()
                current = _RawClause(number=number, title=rest,
                                     page_number=page_number, kind="table")

            elif kind == "figure":
                number = "Figure " + m.group(1).strip()
                rest = line[m.end():].strip()
                current = _RawClause(number=number, title=rest,
                                     page_number=page_number, kind="figure")

            else:   # numbered clause
                number = m.group(1).strip()
                title  = m.group(2).strip() if len(m.groups()) > 1 else ""
                current = _RawClause(number=number, title=title,
                                     page_number=page_number, kind="clause")

            matched = True
            break

        if not matched:
            if current is not None:
                current.content_lines.append(line)
            else:
                current = _RawClause(
                    number="0",
                    title="Preamble",
                    page_number=page_number,
                    kind="clause",
                    content_lines=[line],
                )
        i += 1

    if current is not None:
        clauses.append(current)

    return clauses


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def parse_is_document(pdf_path) -> list:
    """
    Parse an Indian Standard PDF and return a list of ISChunk dicts.

    Parameters
    ----------
    pdf_path : str | Path
        Path to the IS document PDF.

    Returns
    -------
    list[ISChunk]
        Structured chunks with keys: standard_code, clause_number,
        clause_title, content, page_number.

    Raises
    ------
    FileNotFoundError
        If the file does not exist.
    RuntimeError
        If no text could be extracted.

    Example
    -------
    >>> chunks = parse_is_document("data/IS_10500_2012.pdf")
    >>> print(chunks[0])
    {
        "standard_code": "IS 10500:2012",
        "clause_number": "1",
        "clause_title":  "Scope",
        "content":       "This standard prescribes ...",
        "page_number":   1
    }
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    logger.info("Parsing IS document: %s", pdf_path.name)

    # 1. Extract tables via pdfplumber
    tables_by_page = _extract_tables_by_page(pdf_path)

    # 2. Extract text via PyMuPDF
    text_blocks = _extract_text_blocks(pdf_path)
    if not text_blocks:
        raise RuntimeError(f"No text extracted from {pdf_path}")

    # 3. Auto-detect IS standard code from first 3 pages
    standard_code = ""
    for blk in text_blocks[:3]:
        code = _detect_standard_code(blk.text)
        if code:
            standard_code = code
            break
    logger.info("Detected standard code: %r", standard_code)

    # 4. Split each page into clause fragments
    all_raw: list = []
    for blk in text_blocks:
        all_raw.extend(_split_into_clauses(blk.text, blk.page_number))

    # 5. Merge consecutive fragments sharing the same clause number
    #    (clauses often span multiple pages)
    merged: list = []
    for raw in all_raw:
        if (
            merged
            and merged[-1].number == raw.number
            and raw.number not in ("0",)
        ):
            merged[-1].content_lines.extend([""] + raw.content_lines)
        else:
            merged.append(raw)

    # 6. Inject pdfplumber markdown tables into the nearest preceding clause
    for page_num, md_tables in tables_by_page.items():
        target = None
        for raw in reversed(merged):
            if raw.page_number == page_num:
                target = raw
                break
        if target is None:
            target = _RawClause(
                number="Table",
                title="Extracted Table",
                page_number=page_num,
                kind="table",
            )
            merged.append(target)
        for md in md_tables:
            target.content_lines.append("")
            target.content_lines.append(md)

    # 7. Build final ISChunk list
    chunks: list = []
    for raw in merged:
        content = "\n".join(raw.content_lines).strip()
        # Skip empty preamble noise / very short boilerplate
        if not content and raw.kind == "clause" and raw.number == "0":
            continue
        if len(content) < 10 and not raw.title:
            continue

        chunks.append(
            ISChunk(
                standard_code=standard_code,
                clause_number=raw.number,
                clause_title=raw.title,
                content=content,
                page_number=raw.page_number,
            )
        )

    logger.info("Extracted %d chunks from %s", len(chunks), pdf_path.name)
    return chunks


# ---------------------------------------------------------------------------
# CLI convenience
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import json
    import sys

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    if len(sys.argv) < 2:
        print("Usage: python -m app.utils.pdf_parser <path/to/IS_document.pdf>")
        sys.exit(1)

    results = parse_is_document(sys.argv[1])
    print(json.dumps(results, indent=2, ensure_ascii=False))