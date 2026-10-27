import sqlite3

from models import EPDRecord

SCHEMA = """
CREATE TABLE IF NOT EXISTS epds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    epd_number TEXT UNIQUE,
    product_name TEXT NOT NULL,
    manufacturer TEXT,
    declared_unit TEXT NOT NULL,
    gwp_a1_a3 REAL,
    gwp_total REAL,
    pdf_year INTEGER,
    valid_until TEXT,
    country TEXT,
    source_file TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
"""


def get_connection(db_path: str = "lca.db") -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute(SCHEMA)
    return conn


def insert_epd(conn: sqlite3.Connection, record: EPDRecord) -> int:
    data = record.model_dump()
    cols = ", ".join(data.keys())
    placeholders = ", ".join("?" for _ in data)
    cur = conn.execute(
        f"INSERT OR REPLACE INTO epds ({cols}) VALUES ({placeholders})",
        tuple(data.values()),
    )
    conn.commit()
    return cur.lastrowid


def list_epds(conn: sqlite3.Connection) -> list[dict]:
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM epds ORDER BY created_at DESC").fetchall()
    return [dict(r) for r in rows]
