import os
from dotenv import load_dotenv
load_dotenv()
os.system(r"venv\Scripts\python scripts\ingest_standards.py --recreate")
