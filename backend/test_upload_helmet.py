import requests
import io
import os

filename = 'helmet standard.pdf'
filepath = r'c:\Users\rohit\OneDrive\Desktop\sih\backend\data\raw_pdfs\helmet standard.pdf'

print(f"Uploading {filename} to endpoint...")
with open(filepath, 'rb') as f:
    pdf_content = f.read()

res = requests.post(
    "http://127.0.0.1:8000/api/ingest/upload",
    files={"files": (filename, pdf_content, "application/pdf")}
)
print("Status:", res.status_code)
print(res.content)
