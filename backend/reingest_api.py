import requests
import os
from pathlib import Path

pdf_dir = Path(r"c:\Users\rohit\OneDrive\Desktop\sih\backend\data\raw_pdfs")
pdf_paths = [p for p in pdf_dir.glob("*.pdf")]

for pdf_path in pdf_paths:
    print(f"Uploading {pdf_path.name}...")
    with open(pdf_path, 'rb') as f:
        pdf_content = f.read()

    res = requests.post(
        "http://127.0.0.1:8000/api/ingest/upload",
        files={"files": (pdf_path.name, pdf_content, "application/pdf")}
    )
    print(f"Status: {res.status_code}")
    print(f"Response: {res.text}")
    print("-" * 40)
