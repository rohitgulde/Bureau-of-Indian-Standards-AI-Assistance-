import sqlite3
import os

db_path = os.path.join("app", "database", "bis_master.db")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

query = """
SELECT 
    p.product_name,
    s.is_number,
    SUBSTR(s.title, 1, 30) || '...' AS title_preview,
    k.clause_number,
    SUBSTR(k.text, 1, 40) || '...' AS text_preview
FROM products p
LEFT JOIN product_standard ps ON p.product_id = ps.product_id
LEFT JOIN standards s ON ps.standard_id = s.standard_id
LEFT JOIN knowledge_chunks k ON s.standard_id = k.standard_id
WHERE LOWER(p.product_name) = LOWER('LED Lamp')
  AND LOWER(ps.relationship_type) = LOWER('Product Standard')
ORDER BY s.is_number, k.page_number
LIMIT 5;
"""

print("Executing Relational JOIN Query (exactly matching your pgAdmin screenshot):\n")
cursor.execute(query)
rows = cursor.fetchall()

print(f"{'Product':<12} | {'IS Number':<25} | {'Title':<35} | {'Clause':<8} | Text Preview")
print("-" * 120)
for row in rows:
    print(f"{str(row[0]):<12} | {str(row[1]):<25} | {str(row[2]):<35} | {str(row[3]):<8} | {str(row[4])}")
conn.close()

