import sqlite3
import sys

def init_db():
    conn = sqlite3.connect("neighborgrid.db")
    with open("schema.sql", "r", encoding="utf-8") as f:
        conn.executescript(f.read())

    cursor = conn.cursor()

    # Ensure is_flagged column exists in posts table for moderation
    cursor.execute("PRAGMA table_info(posts);")
    columns = [col[1] for col in cursor.fetchall()]
    if "is_flagged" not in columns:
        try:
            cursor.execute("ALTER TABLE posts ADD COLUMN is_flagged INTEGER NOT NULL DEFAULT 0;")
        except Exception:
            pass

    # Ensure is_banned column exists in users table
    cursor.execute("PRAGMA table_info(users);")
    u_columns = [col[1] for col in cursor.fetchall()]
    if "is_banned" not in u_columns:
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN is_banned INTEGER NOT NULL DEFAULT 0;")
        except Exception:
            pass

    # Add useful performance indexes on frequently queried columns
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_posts_status ON posts(status);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_posts_category ON posts(category_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_posts_created ON posts(created_at);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_posts_user ON posts(user_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_matches_post ON matches(post_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_post ON messages(post_id);")

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [r[0] for r in cursor.fetchall()]
    print("Tables:", tables)

    cursor.execute("SELECT count(*) FROM categories;")
    count = cursor.fetchone()[0]
    print("Categories seeded:", count)
    conn.close()

if __name__ == "__main__":
    init_db()
