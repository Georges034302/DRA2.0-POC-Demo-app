import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

SCHEMA = Path(__file__).with_name("schema.sql").read_text(encoding="utf-8")
PRIORITIES = ("low", "medium", "high")
STATUSES = ("todo", "in_progress", "done")


# Validate a complete task payload and normalize its text fields.
def validate_fields(fields):
    if not isinstance(fields, dict):
        raise ValueError("Expected a JSON object")
    for name in ("title", "description", "priority", "status"):
        if not isinstance(fields.get(name), str):
            raise ValueError(f"{name} must be a string")
    title = fields["title"].strip()
    if not 1 <= len(title) <= 120:
        raise ValueError("Title must be 1-120 characters")
    if len(fields["description"]) > 2000:
        raise ValueError("Description must be at most 2000 characters")
    if fields["priority"] not in PRIORITIES:
        raise ValueError("Invalid priority")
    if fields["status"] not in STATUSES:
        raise ValueError("Invalid status")
    return dict(
        title=title,
        description=fields["description"].strip(),
        priority=fields["priority"],
        status=fields["status"],
    )


# Open a connection, commit on success, and roll back on failure.
@contextmanager
def connection():
    path = os.getenv("DATABASE_PATH", "/data/tasks.db")
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


# Create missing tables and indexes without replacing existing data.
def init():
    with connection() as db:
        db.executescript(SCHEMA)


# Return tasks newest first, optionally filtered by status and priority.
def listing(status=None, priority=None):
    if status is not None and status not in STATUSES:
        raise ValueError("Invalid status")
    if priority is not None and priority not in PRIORITIES:
        raise ValueError("Invalid priority")
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


# Return a task by ID, or None when it does not exist.
def find(task_id):
    with connection() as db:
        row = db.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        return dict(row) if row else None


# Validate and create a task, returning the stored row.
def insert(fields):
    fields = validate_fields(fields)
    with connection() as db:
        cursor = db.execute(
            "INSERT INTO tasks(title,description,priority,status) VALUES(?,?,?,?)",
            (fields['title'], fields['description'], fields['priority'], fields['status']),
        )
        row = db.execute("SELECT * FROM tasks WHERE id=?", (cursor.lastrowid,)).fetchone()
        return dict(row)


# Replace task fields and refresh the timestamp, or return None if missing.
def update(task_id, fields):
    fields = validate_fields(fields)
    with connection() as db:
        cursor = db.execute(
            "UPDATE tasks SET title=?, description=?, priority=?, status=?, "
            "updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE id=?",
            (fields['title'], fields['description'], fields['priority'], fields['status'], task_id),
        )
        if cursor.rowcount == 0:
            return None
        row = db.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        return dict(row)


# Delete a task and report whether a row was removed.
def delete(task_id):
    with connection() as db:
        return db.execute("DELETE FROM tasks WHERE id=?", (task_id,)).rowcount > 0
