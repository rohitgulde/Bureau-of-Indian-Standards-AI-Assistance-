import requests
import io
import os

print("Uploading LED standards.pdf to endpoint...")
with open(r'c:\Users\rohit\OneDrive\Desktop\sih\backend\data\raw_pdfs\LED standards.pdf', 'rb') as f:
    pdf_content = f.read()

res = requests.post(
    "http://127.0.0.1:8000/api/ingest/upload",
    files={"files": ("LED standards.pdf", pdf_content, "application/pdf")}
)
print("Status:", res.status_code)
print(res.text)
