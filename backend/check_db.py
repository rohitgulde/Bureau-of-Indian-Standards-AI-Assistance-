import sqlite3
import json
from qdrant_client import QdrantClient

def check_sqlite():
    print("=== SQLITE DATABASE (bis_master.db) ===")
    conn = sqlite3.connect('app/database/bis_master.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row['name'] for row in cursor.fetchall()]
    print(f"Tables: {tables}")
    
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
        count = cursor.fetchone()['count']
        cursor.execute(f"PRAGMA table_info({table})")
        columns = [row['name'] for row in cursor.fetchall()]
        print(f"\nTable: {table}")
        print(f"Row count: {count}")
        print(f"Columns: {columns}")
        
        if count > 0:
            cursor.execute(f"SELECT * FROM {table} LIMIT 1")
            row = dict(cursor.fetchone())
            print(f"Sample row: {json.dumps(row, default=str)}")
            
    conn.close()

def check_qdrant():
    print("\n=== QDRANT VECTOR DATABASE ===")
    try:
        client = QdrantClient(path="data/qdrant_storage")
        collections = client.get_collections().collections
        print(f"Collections: {[c.name for c in collections]}")
        for c in collections:
            count = client.count(c.name).count
            print(f"Collection: {c.name}")
            print(f"Point count (Vectors/Documents): {count}")
    except Exception as e:
        print(f"Qdrant Error: {e}")

if __name__ == "__main__":
    check_sqlite()
    check_qdrant()
