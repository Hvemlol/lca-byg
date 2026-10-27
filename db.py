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

CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    location TEXT,
    description TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS line_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    epd_id INTEGER NOT NULL REFERENCES epds(id),
    description TEXT,
    quantity REAL NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
"""


def get_connection(db_path: str = "lca.db") -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    conn.row_factory = sqlite3.Row
    return conn


# --- EPDs ---

def insert_epd(conn: sqlite3.Connection, record: EPDRecord) -> int:
    # Upsert that preserves the row id: INSERT OR REPLACE would delete and
    # re-insert, changing the id and breaking line_items.epd_id references.
    if record.epd_number:
        existing = conn.execute(
            "SELECT id FROM epds WHERE epd_number = ?", (record.epd_number,)
        ).fetchone()
        if existing:
            data = record.model_dump()
            assignments = ", ".join(f"{col} = ?" for col in data)
            cur = conn.execute(
                f"UPDATE epds SET {assignments} WHERE id = ?",
                (*data.values(), existing["id"]),
            )
            conn.commit()
            return existing["id"]
    data = record.model_dump()
    cols = ", ".join(data.keys())
    placeholders = ", ".join("?" for _ in data)
    cur = conn.execute(
        f"INSERT INTO epds ({cols}) VALUES ({placeholders})",
        tuple(data.values()),
    )
    conn.commit()
    return cur.lastrowid


def list_epds(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute("SELECT * FROM epds ORDER BY created_at DESC").fetchall()
    return [dict(r) for r in rows]


# --- Projects ---

def create_project(conn: sqlite3.Connection, name: str, location: str = "", description: str = "") -> int:
    cur = conn.execute(
        "INSERT INTO projects (name, location, description) VALUES (?, ?, ?)",
        (name, location, description),
    )
    conn.commit()
    return cur.lastrowid


def list_projects(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute("SELECT * FROM projects ORDER BY created_at DESC").fetchall()
    return [dict(r) for r in rows]


def get_project(conn: sqlite3.Connection, project_id: int) -> dict | None:
    row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    return dict(row) if row else None


def delete_project(conn: sqlite3.Connection, project_id: int) -> None:
    conn.execute("DELETE FROM line_items WHERE project_id = ?", (project_id,))
    conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    conn.commit()


# --- Line items ---

def add_line_item(conn: sqlite3.Connection, project_id: int, epd_id: int, quantity: float, description: str = "") -> int:
    cur = conn.execute(
        "INSERT INTO line_items (project_id, epd_id, description, quantity) VALUES (?, ?, ?, ?)",
        (project_id, epd_id, description, quantity),
    )
    conn.commit()
    return cur.lastrowid


def list_line_items(conn: sqlite3.Connection, project_id: int) -> list[dict]:
    rows = conn.execute(
        """
        SELECT li.id, li.project_id, li.epd_id, li.description, li.quantity,
               e.product_name, e.manufacturer, e.declared_unit,
               e.gwp_a1_a3, e.gwp_total, e.epd_number,
               li.quantity * e.gwp_a1_a3 AS gwp_contribution
        FROM line_items li
        JOIN epds e ON e.id = li.epd_id
        WHERE li.project_id = ?
        ORDER BY li.id
        """,
        (project_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def delete_line_item(conn: sqlite3.Connection, line_item_id: int) -> None:
    conn.execute("DELETE FROM line_items WHERE id = ?", (line_item_id,))
    conn.commit()


def project_total_gwp(conn: sqlite3.Connection, project_id: int) -> float:
    row = conn.execute(
        """
        SELECT COALESCE(SUM(li.quantity * e.gwp_a1_a3), 0) AS total
        FROM line_items li
        JOIN epds e ON e.id = li.epd_id
        WHERE li.project_id = ?
        """,
        (project_id,),
    ).fetchone()
    return row["total"]
