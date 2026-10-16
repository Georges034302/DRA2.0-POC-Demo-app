import hmac
import os
import sqlite3

from flask import Flask, abort, jsonify, request

import crud

app = Flask(__name__)
crud.init()


# Require the internal service token for every route except health checks.
@app.before_request
def protect():
    if request.path == '/health':
        return
    expected = os.getenv('INTERNAL_API_TOKEN', '')
    provided = request.headers.get('X-Service-Token', '')
    if not expected or not hmac.compare_digest(provided.encode('utf-8'), expected.encode('utf-8')):
        abort(401)


# Report whether the database connection and task table are accessible.
@app.get('/health')
def health():
    try:
        with crud.connection() as db:
            db.execute('SELECT id FROM tasks LIMIT 1').fetchone()
        return jsonify(service='database', status='ok')
    except (sqlite3.Error, OSError):
        return jsonify(service='database', status='unhealthy'), 503


# List tasks with validated status and priority filters.
@app.get('/internal/tasks')
def list_tasks():
    try:
        tasks = crud.listing(request.args.get('status'), request.args.get('priority'))
    except ValueError:
        abort(400)
    return jsonify(tasks)


# Fetch one task, returning 404 when the ID is missing.
@app.get('/internal/tasks/<int:task_id>')
def get_task(task_id):
    task = crud.find(task_id)
    return (jsonify(task), 200) if task else (jsonify(error='not found'), 404)


# Create a task, returning 201 on success or 400 for invalid input.
@app.post('/internal/tasks')
def add_task():
    try:
        task = crud.insert(request.get_json(silent=True))
    except (ValueError, sqlite3.IntegrityError):
        abort(400)
    return jsonify(task), 201


# Replace an existing task, rejecting invalid input and missing IDs.
@app.put('/internal/tasks/<int:task_id>')
def edit_task(task_id):
    try:
        task = crud.update(task_id, request.get_json(silent=True))
    except (ValueError, sqlite3.IntegrityError):
        abort(400)
    return (jsonify(task), 200) if task else (jsonify(error='not found'), 404)


# Delete a task, returning 204 on success or 404 when missing.
@app.delete('/internal/tasks/<int:task_id>')
def remove_task(task_id):
    return ('', 204) if crud.delete(task_id) else (jsonify(error='not found'), 404)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
