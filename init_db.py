import sqlite3
import sys

def init_db():
    conn = sqlite3.connect("neighborgrid.db")
    with open("schema.sql", "r", encoding="utf-8") as f:
        conn.executescript(f.read())

    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [r[0] for r in cursor.fetchall()]
    print("Tables:", tables)

    cursor.execute("SELECT count(*) FROM categories;")
    count = cursor.fetchone()[0]
    print("Categories seeded:", count)
    conn.close()

if __name__ == "__main__":
    init_db()
