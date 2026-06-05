import sqlite3

DB_FILE = "lobster.db"

conn = sqlite3.connect(DB_FILE)
cursor = conn.cursor()

cursor.execute(
    "INSERT INTO memories(content) VALUES(?)",
    ("我正在測試 SQLite 記憶系統",)
)

conn.commit()

cursor.execute("SELECT id, content, created_at FROM memories")
rows = cursor.fetchall()

for row in rows:
    print(row)

conn.close()
