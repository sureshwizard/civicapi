import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional

from .config import DB_PATH

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS bills (
        id TEXT PRIMARY KEY,
        vendor TEXT NOT NULL,
        amount REAL NOT NULL,
        due_date TEXT NOT NULL,
        status TEXT NOT NULL,
        note TEXT
    )
    """)
    conn.commit()
    conn.close()

def insert_bill(b: Dict[str, Any]):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO bills (id, vendor, amount, due_date, status, note)
        VALUES (:id, :vendor, :amount, :due_date, :status, :note)
    """, b)
    conn.commit()
    conn.close()

def list_bills(status: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_conn()
    cur = conn.cursor()
    if status:
        cur.execute("SELECT * FROM bills WHERE status = ? ORDER BY due_date ASC", (status,))
    else:
        cur.execute("SELECT * FROM bills ORDER BY due_date ASC")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

def get_bill(bill_id: str) -> Optional[Dict[str, Any]]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM bills WHERE id = ?", (bill_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None

def update_status(bill_id: str, status: str) -> bool:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE bills SET status = ? WHERE id = ?", (status, bill_id))
    conn.commit()
    ok = cur.rowcount > 0
    conn.close()
    return ok

