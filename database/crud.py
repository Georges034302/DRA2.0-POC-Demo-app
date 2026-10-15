import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

PATH = lambda: os.getenv("DATABASE_PATH", "/data/tasks.db")
SCHEMA = Path(__file__).with_name("schema.sql").read_text()

@contextmanager
def connection():
    path = PATH()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=10)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA busy_timeout=10000")
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def init():
    with connection() as db:
        db.executescript(SCHEMA)

def listing(status=None, priority=None):
    sql = "SELECT * FROM tasks WHERE 1=1"
    args = []
    if status:
        sql += " AND status=?"
        args.append(status)
    if priority:
        sql += " AND priority=?"
        args.append(priority)
    sql += " ORDER BY id DESC"
    with connection() as db:
        return [dict(row) for row in db.execute(sql, args).fetchall()]

def find(task_id):
    with connection() as db:
        row = db.execute("SELECT * FROM tasks WHERE id=?",(task_id,)).fetchone()
        return dict(row) if row else None

def insert(fields):
    with connection() as db:
        cursor = db.execute("INSERT INTO tasks(title,description,priority,status) VALUES(?,?,?,?)",
            (fields['title'],fields['description'],fields['priority'],fields['status']))
        pk=cursor.lastrowid
    return find(pk)

def update(task_id,fields):
    with connection() as db:
        existing=db.execute("SELECT id FROM tasks WHERE id=?",(task_id,)).fetchone()
        if not existing: return None
        db.execute("UPDATE tasks SET title=?, description=?, priority=?, status=?, updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE id=?",
            (fields['title'],fields['description'],fields['priority'],fields['status'],task_id))
    return find(task_id)

def delete(task_id):
    with connection() as db:
        return db.execute("DELETE FROM tasks WHERE id=?",(task_id,)).rowcount > 0
