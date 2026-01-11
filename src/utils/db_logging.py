import sqlite3
from datetime import datetime


def ensure_log_table(conn: sqlite3.Connection):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS ingestion_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            pipeline TEXT,
            table_name TEXT,
            action TEXT,
            rows INTEGER,
            status TEXT,
            details TEXT
        )
        """
    )


def log_event(conn: sqlite3.Connection, pipeline: str, table: str, action: str, rows: int, status: str = 'ok', details: str = ''):
    ensure_log_table(conn)
    ts = datetime.utcnow().isoformat()
    conn.execute(
        "INSERT INTO ingestion_log (timestamp, pipeline, table_name, action, rows, status, details) VALUES (?,?,?,?,?,?,?)",
        (ts, pipeline, table, action, int(rows or 0), status, details)
    )
    conn.commit()
