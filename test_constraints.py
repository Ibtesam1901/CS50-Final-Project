import sqlite3

def test_constraints():
    conn = sqlite3.connect("neighborgrid.db")
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")

    # 1. Test duplicate username constraint
    try:
        cursor.execute("INSERT INTO users (username, email, hash, neighborhood) VALUES ('alice', 'alice@test.com', 'hash', 'Downtown');")
        cursor.execute("INSERT INTO users (username, email, hash, neighborhood) VALUES ('alice', 'alice2@test.com', 'hash', 'Downtown');")
        print("FAIL: duplicate username did not raise IntegrityError")
    except sqlite3.IntegrityError:
        print("PASS: duplicate username properly rejected")

    # 2. Test invalid post_type check constraint
    try:
        cursor.execute("INSERT INTO posts (user_id, post_type, category_id, title, description, neighborhood) VALUES (1, 'invalid_type', 1, 'Test', 'Test desc', 'Downtown');")
        print("FAIL: invalid post_type did not raise IntegrityError")
    except sqlite3.IntegrityError:
        print("PASS: invalid post_type check constraint properly rejected")

    # 3. Test duplicate matches from the same user on one post
    try:
        cursor.execute("INSERT INTO users (username, email, hash, neighborhood) VALUES ('bob', 'bob@test.com', 'hash', 'Downtown');")
        cursor.execute("INSERT INTO posts (user_id, post_type, category_id, title, description, neighborhood) VALUES (1, 'request', 1, 'Need a ladder', 'Desc', 'Downtown');")
        post_id = cursor.lastrowid
        cursor.execute("INSERT INTO matches (post_id, responder_id, message) VALUES (?, 2, 'I can help');", (post_id,))
        cursor.execute("INSERT INTO matches (post_id, responder_id, message) VALUES (?, 2, 'Duplicate offer');", (post_id,))
        print("FAIL: duplicate match did not raise IntegrityError")
    except sqlite3.IntegrityError:
        print("PASS: duplicate match constraint properly rejected")

    conn.rollback() # don't persist test rows
    conn.close()

if __name__ == "__main__":
    test_constraints()
