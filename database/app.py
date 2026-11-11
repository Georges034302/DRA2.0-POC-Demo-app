import hmac
import os
import sqlite3

from flask import Flask, Response, g, jsonify, request

PRIORITIES = ('low', 'medium', 'high')
STATUSES = ('todo', 'in_progress', 'done')
MAX_TITLE_LENGTH = 200
MAX_DESCRIPTION_LENGTH = 2000
TASK_COLUMNS = 'id, title, description, priority, status, created_at, updated_at'

app = Flask(__name__)
app.config['DATABASE_PATH'] = os.environ.get('DATABASE_PATH', '/data/tasks.db')
app.config['INTERNAL_API_TOKEN'] = os.environ.get('INTERNAL_API_TOKEN', '')
if not app.config['INTERNAL_API_TOKEN']:
    raise RuntimeError('INTERNAL_API_TOKEN must be set')


# Returns the SQLite connection for the current request, opening it on first use.
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(app.config['DATABASE_PATH'])
        g.db.row_factory = sqlite3.Row
    return g.db


# Closes the request's database connection.
@app.teardown_appcontext
def close_db(_error):
    db = g.pop('db', None)
    if db is not None:
        db.close()


# Builds a JSON error response.
def error(message, status):
    return jsonify({'status': 'error', 'message': message}), status


# Only the backend may call the API: requires the shared internal token on /api routes.
@app.before_request
def require_internal_token():
    if not request.path.startswith('/api/'):
        return None
    provided = request.headers.get('X-Internal-Token', '')
    if not hmac.compare_digest(provided.encode(), app.config['INTERNAL_API_TOKEN'].encode()):
        return error('Unauthorized', 401)
    return None


# Validates a task payload and returns the known fields; raises ValueError describing the problem.
# With partial=True only the fields present are checked (for updates).
def parse_task(data, partial):
    if not isinstance(data, dict):
        raise ValueError('A JSON object body is required')

    values = {}
    if not partial or 'title' in data:
        title = data.get('title')
        if not isinstance(title, str) or not title.strip():
            raise ValueError('title is required')
        title = title.strip()
        if len(title) > MAX_TITLE_LENGTH:
            raise ValueError(f'title must be at most {MAX_TITLE_LENGTH} characters')
        values['title'] = title

    if 'description' in data:
        description = data['description']
        if not isinstance(description, str) or len(description) > MAX_DESCRIPTION_LENGTH:
            raise ValueError(f'description must be text of at most {MAX_DESCRIPTION_LENGTH} characters')
        values['description'] = description

    if 'priority' in data:
        if data['priority'] not in PRIORITIES:
            raise ValueError(f"priority must be one of: {', '.join(PRIORITIES)}")
        values['priority'] = data['priority']

    if 'status' in data:
        if data['status'] not in STATUSES:
            raise ValueError(f"status must be one of: {', '.join(STATUSES)}")
        values['status'] = data['status']

    return values


# Loads one task as a dict, or None if it does not exist.
def fetch_task(task_id):
    row = get_db().execute(f'SELECT {TASK_COLUMNS} FROM tasks WHERE id = ?', (task_id,)).fetchone()
    return dict(row) if row else None


REDIRECT_PAGE = """<!doctype html>
<title>DRA 2.0 POC</title>
<script>
  const port = '%(port)s';
  const host = location.host.includes('-' + port + '.')
    ? location.host.replace('-' + port + '.', '-80.')
    : location.hostname;
  location.replace(location.protocol + '//' + host + '/');
</script>
<noscript>This is the database API. Open the app on port 80.</noscript>
"""


# Sends anyone who opens this API's address in a browser to the frontend UI on port 80.
@app.route('/', methods=['GET'])
def index():
    return Response(REDIRECT_PAGE % {'port': 5001}, mimetype='text/html')


# Reports that the service is running; used by the container health check.
@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy'}), 200


# Lists all tasks.
@app.route('/api/tasks', methods=['GET'])
def list_tasks():
    rows = get_db().execute(f'SELECT {TASK_COLUMNS} FROM tasks ORDER BY id').fetchall()
    return jsonify([dict(row) for row in rows]), 200


# Creates a task from the request body.
@app.route('/api/tasks', methods=['POST'])
def create_task():
    try:
        values = parse_task(request.get_json(silent=True), partial=False)
    except ValueError as exc:
        return error(str(exc), 400)

    columns = ', '.join(values)
    placeholders = ', '.join('?' for _ in values)
    db = get_db()
    cursor = db.execute(f'INSERT INTO tasks ({columns}) VALUES ({placeholders})', tuple(values.values()))
    db.commit()
    return jsonify(fetch_task(cursor.lastrowid)), 201


# Returns one task.
@app.route('/api/tasks/<int:task_id>', methods=['GET'])
def get_task(task_id):
    task = fetch_task(task_id)
    if task is None:
        return error('Task not found', 404)
    return jsonify(task), 200


# Updates the given fields of a task and refreshes its updated_at time.
@app.route('/api/tasks/<int:task_id>', methods=['PATCH'])
def update_task(task_id):
    if fetch_task(task_id) is None:
        return error('Task not found', 404)

    try:
        values = parse_task(request.get_json(silent=True), partial=True)
    except ValueError as exc:
        return error(str(exc), 400)
    if not values:
        return error('No updatable fields provided', 400)

    assignments = ', '.join(f'{column} = ?' for column in values)
    db = get_db()
    db.execute(
        f'UPDATE tasks SET {assignments}, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
        (*values.values(), task_id),
    )
    db.commit()
    return jsonify(fetch_task(task_id)), 200


# Deletes a task.
@app.route('/api/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    db = get_db()
    cursor = db.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
    db.commit()
    if cursor.rowcount == 0:
        return error('Task not found', 404)
    return '', 204


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=False)
