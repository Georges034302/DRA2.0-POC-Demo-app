CREATE TABLE IF NOT EXISTS tasks (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 title TEXT NOT NULL CHECK(length(trim(title)) BETWEEN 1 AND 120),
 description TEXT NOT NULL DEFAULT '',
 priority TEXT NOT NULL DEFAULT 'medium' CHECK(priority IN ('low','medium','high')),
 status TEXT NOT NULL DEFAULT 'todo' CHECK(status IN ('todo','in_progress','done')),
 created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
 updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
