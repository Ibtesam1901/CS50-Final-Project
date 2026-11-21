import sqlite3
import sys

def init_db():
    conn = sqlite3.connect("neighborgrid.db")
    with open("schema.sql", "r", encoding="utf-8") as f:
        conn.executescript(f.read())

    cursor = conn.cursor()

    # 1. Ensure is_flagged column exists in posts table for moderation
    cursor.execute("PRAGMA table_info(posts);")
    columns = [col[1] for col in cursor.fetchall()]
    if "is_flagged" not in columns:
        try:
            cursor.execute("ALTER TABLE posts ADD COLUMN is_flagged INTEGER NOT NULL DEFAULT 0;")
        except Exception as e:
            print("Notice on is_flagged:", e)

    # Ensure updated_at column exists in posts table for live feed updates
    # SQLite does not allow non-constant expressions like CURRENT_TIMESTAMP in ALTER TABLE ADD COLUMN.
    if "updated_at" not in columns:
        try:
            cursor.execute("ALTER TABLE posts ADD COLUMN updated_at TIMESTAMP;")
            cursor.execute("UPDATE posts SET updated_at = created_at WHERE updated_at IS NULL;")
        except Exception as e:
            print("Notice on updated_at:", e)

    # 2. Ensure is_banned column exists in users table
    cursor.execute("PRAGMA table_info(users);")
    u_columns = [col[1] for col in cursor.fetchall()]
    if "is_banned" not in u_columns:
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN is_banned INTEGER NOT NULL DEFAULT 0;")
        except Exception as e:
            print("Notice on is_banned:", e)

    # 3. Ensure idempotency_key and read_at exist in messages table
    cursor.execute("PRAGMA table_info(messages);")
    m_columns = [col[1] for col in cursor.fetchall()]
    if "idempotency_key" not in m_columns:
        try:
            cursor.execute("ALTER TABLE messages ADD COLUMN idempotency_key TEXT;")
        except Exception as e:
            print("Notice on idempotency_key:", e)
    if "read_at" not in m_columns:
        try:
            cursor.execute("ALTER TABLE messages ADD COLUMN read_at TIMESTAMP;")
        except Exception as e:
            print("Notice on read_at:", e)

    # 4. Clean placeholder neighborhood values if present (Part B3 migration)
    try:
        cursor.execute("UPDATE posts SET neighborhood = 'Indiranagar, Bengaluru' WHERE neighborhood LIKE '%Current%' OR neighborhood LIKE '%Location%';")
        cursor.execute("UPDATE users SET neighborhood = 'Indiranagar, Bengaluru' WHERE neighborhood LIKE '%Current%' OR neighborhood LIKE '%Location%';")
    except Exception as e:
        print("Notice on cleanup:", e)

    # 5. Add performance indexes for live polling queries
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_posts_status ON posts(status);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_posts_category ON posts(category_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_posts_created ON posts(created_at);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_posts_updated ON posts(updated_at);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_posts_user ON posts(user_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_matches_post ON matches(post_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_matches_responder ON matches(responder_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_post ON messages(post_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_thread ON messages(post_id, id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_receiver ON messages(receiver_id, is_read);")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database schema migration completed successfully.")
