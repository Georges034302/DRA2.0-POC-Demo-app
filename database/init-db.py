import os
import sqlite3

DEFAULT_DATABASE_PATH = '/data/tasks.db'

SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT DEFAULT '',
    priority TEXT DEFAULT 'medium' CHECK(priority IN ('low', 'medium', 'high')),
    status TEXT DEFAULT 'todo' CHECK(status IN ('todo', 'in_progress', 'done')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""

SEED_TASKS = [
    ('Create minimal application', 'Database, API and basic UI running locally', 'high', 'done'),
    ('Build CI/CD pipeline', 'Test, build and publish images with digests', 'high', 'todo'),
    ('Integrate broker review', 'Send evidence to the broker and enforce decisions', 'medium', 'todo'),
]


# Creates the schema if missing and seeds an empty table; returns how many rows were seeded.
# Safe to run on every start: existing data is never touched.
def init_db(path):
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)

    with sqlite3.connect(path) as connection:
        connection.execute(SCHEMA)
        (count,) = connection.execute('SELECT COUNT(*) FROM tasks').fetchone()
        if count:
            return 0
        connection.executemany(
            'INSERT INTO tasks (title, description, priority, status) VALUES (?, ?, ?, ?)',
            SEED_TASKS,
        )
        return len(SEED_TASKS)


if __name__ == '__main__':
    database_path = os.environ.get('DATABASE_PATH', DEFAULT_DATABASE_PATH)
    seeded = init_db(database_path)
    print(f'Database ready at {database_path} ({seeded} initial tasks loaded)')
