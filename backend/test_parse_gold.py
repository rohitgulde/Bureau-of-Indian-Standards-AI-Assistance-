import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))
from app.utils.pdf_parser import parse_is_document

pdf_path = Path("data/raw_pdfs/gold standard.pdf")
chunks = parse_is_document(pdf_path)
print(f"Extracted {len(chunks)} chunks")
if chunks:
    print(f"Keys in first chunk: {chunks[0].keys()}")
    for i, c in enumerate(chunks[:3]):
        print(f"--- Chunk {i} ---")
        for k, v in c.items():
            print(f"{k}: {str(v)[:100]}")
