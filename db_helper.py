import sqlite3
import os

class SQL:
    """
    Drop-in replacement for cs50.SQL using Python's built-in sqlite3.
    Matches the exact interface:
        db = SQL("sqlite:///neighborgrid.db")
        rows = db.execute("SELECT ... WHERE id = ?", user_id)
    Returns:
        - List of dicts for SELECT queries: [{'col1': val1, ...}]
        - lastrowid (int) for INSERT queries
        - rowcount (int) for UPDATE / DELETE queries
    """
    def __init__(self, url):
        if url.startswith("sqlite:///"):
            self.db_path = url[len("sqlite:///"):]
        elif url.startswith("sqlite://"):
            self.db_path = url[len("sqlite://"):]
        else:
            self.db_path = url

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def execute(self, sql, *args):
        # Flatten tuple if single tuple/list passed as positional argument
        params = args
        if len(args) == 1 and isinstance(args[0], (list, tuple)):
            params = args[0]

        sql_trimmed = sql.strip().upper()

        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            if sql_trimmed.startswith("SELECT") or sql_trimmed.startswith("WITH") or "RETURNING" in sql_trimmed:
                rows = [dict(row) for row in cursor.fetchall()]
                conn.commit()
                return rows
            elif sql_trimmed.startswith("INSERT"):
                last_id = cursor.lastrowid
                conn.commit()
                return last_id
            else:
                row_count = cursor.rowcount
                conn.commit()
                return row_count
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

# If cs50 library is available, use it; otherwise fallback to the pure sqlite3 SQL class
try:
    from cs50 import SQL as CS50_SQL
    SQL_PROVIDER = CS50_SQL
except ImportError:
    SQL_PROVIDER = SQL
