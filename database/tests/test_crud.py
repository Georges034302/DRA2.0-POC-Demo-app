import pathlib
import runpy
import sqlite3
import sys

import pytest

DATABASE_DIR = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DATABASE_DIR))
import crud


# Initialize an isolated temporary database before each test.
@pytest.fixture(autouse=True)
def database(tmp_path, monkeypatch):
    path = tmp_path / 'data' / 'tasks.db'
    monkeypatch.setenv('DATABASE_PATH', str(path))
    crud.init()
    return path


# Provide a fresh, valid task payload for each test.
@pytest.fixture
def fields():
    return {'title': 'Example', 'description': '', 'priority': 'low', 'status': 'todo'}


# Load the database API with test authentication and exception propagation.
@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv('INTERNAL_API_TOKEN', 'test-token')
    app = runpy.run_path(str(DATABASE_DIR / 'app.py'))['app']
    app.config['TESTING'] = True
    return app.test_client()


HEADERS = {'X-Service-Token': 'test-token'}


# Verify invalid fields cannot create tasks or alter existing rows.
@pytest.mark.parametrize('field,value', [
    ('title', 123),
    ('title', []),
    ('title', '   '),
    ('title', 'x' * 121),
    ('description', 456),
    ('description', 'x' * 2001),
    ('priority', []),
    ('priority', 'urgent'),
    ('status', {}),
    ('status', 'unknown'),
])
@pytest.mark.parametrize('operation', ['insert', 'update'])
def test_write_rejects_invalid_fields(fields, field, value, operation):
    original = crud.insert(fields)
    fields[field] = value

    with pytest.raises(ValueError):
        if operation == 'insert':
            crud.insert(fields)
        else:
            crud.update(original['id'], fields)

    assert crud.listing() == [original]


# Reject non-object payloads and missing required task fields.
@pytest.mark.parametrize('payload', [None, [], 'text', {}, {'title': 'Example'}])
def test_write_requires_complete_object(payload):
    with pytest.raises(ValueError):
        crud.insert(payload)
    assert crud.listing() == []


# Exercise creation, retrieval, replacement, timestamps, and deletion.
def test_crud(fields):
    task = crud.insert(fields)
    assert task['id'] > 0
    assert {name: task[name] for name in fields} == fields
    assert task['created_at'].endswith('Z')
    assert task['updated_at'] == task['created_at']
    assert crud.find(task['id']) == task

    with crud.connection() as db:
        db.execute("UPDATE tasks SET updated_at='2000-01-01T00:00:00.000Z' WHERE id=?", (task['id'],))
    updated = crud.update(task['id'], dict(fields, title='Updated', priority='high', status='done'))
    assert updated['title'] == 'Updated'
    assert updated['status'] == 'done'
    assert updated['priority'] == 'high'
    assert updated['created_at'] == task['created_at']
    assert updated['updated_at'] > '2000-01-01T00:00:00.000Z'
    assert crud.find(task['id']) == updated

    assert crud.delete(task['id']) is True
    assert crud.find(task['id']) is None
    assert crud.listing() == []
    assert crud.delete(task['id']) is False


# Verify missing task IDs return None or False without creating rows.
def test_missing_task(fields):
    assert crud.find(999) is None
    assert crud.update(999, fields) is None
    assert crud.delete(999) is False


# Check newest-first ordering and individual or combined filters.
def test_listing_filters_and_order(fields):
    first = crud.insert(fields)
    second = crud.insert(dict(fields, priority='high', status='done'))
    third = crud.insert(dict(fields, priority='high'))
    assert crud.listing() == [third, second, first]
    assert crud.listing(status='todo') == [third, first]
    assert crud.listing(priority='high') == [third, second]
    assert crud.listing(status='done', priority='high') == [second]
    assert crud.listing(status='done', priority='low') == []


# Reject unsupported or empty filter values in the CRUD layer.
@pytest.mark.parametrize('filters', [{'status': 'unknown'}, {'priority': 'urgent'}, {'status': ''}])
def test_invalid_filters(filters):
    with pytest.raises(ValueError):
        crud.listing(**filters)


# Confirm repeated initialization preserves the database file and task data.
def test_init_preserves_existing_data(database, fields):
    task = crud.insert(fields)
    crud.init()
    assert database.is_file()
    assert crud.listing() == [task]


# Restore earlier changes in a transaction when a later statement fails.
def test_connection_rolls_back(fields):
    original = crud.insert(fields)
    with pytest.raises(sqlite3.IntegrityError):
        with crud.connection() as db:
            db.execute('DELETE FROM tasks')
            db.execute("INSERT INTO tasks(title) VALUES('')")
    assert crud.listing() == [original]


# Check whitespace normalization and acceptance of maximum text lengths.
def test_text_normalization_and_limits(fields):
    task = crud.insert(dict(fields, title='  Example  ', description='  Details  '))
    assert task['title'] == 'Example'
    assert task['description'] == 'Details'
    task = crud.insert(dict(fields, title='x' * 120, description='x' * 2000))
    assert len(task['title']) == 120
    assert len(task['description']) == 2000


# Confirm SQL-like task text is stored as data rather than executed.
def test_sql_values_are_not_executed(fields):
    title = "Example'); DROP TABLE tasks; --"
    task = crud.insert(dict(fields, title=title))
    assert crud.find(task['id'])['title'] == title
    assert len(crud.listing()) == 1


# Exercise authenticated CRUD routes, filters, response codes, and missing IDs.
def test_api_crud(client, fields):
    assert client.get('/internal/tasks', headers=HEADERS).get_json() == []
    response = client.post('/internal/tasks', json=fields, headers=HEADERS)
    assert response.status_code == 201
    task = response.get_json()
    url = f"/internal/tasks/{task['id']}"
    response = client.get(url, headers=HEADERS)
    assert response.status_code == 200
    assert response.get_json() == task
    assert client.get('/internal/tasks?status=todo&priority=low', headers=HEADERS).get_json() == [task]

    response = client.put(url, json=dict(fields, status='done'), headers=HEADERS)
    assert response.status_code == 200
    assert response.get_json()['status'] == 'done'
    assert client.get('/internal/tasks?status=todo', headers=HEADERS).get_json() == []
    response = client.delete(url, headers=HEADERS)
    assert response.status_code == 204
    assert response.data == b''
    assert client.get(url, headers=HEADERS).status_code == 404
    assert client.put(url, json=fields, headers=HEADERS).status_code == 404
    assert client.delete(url, headers=HEADERS).status_code == 404


# Require authentication on every task route, including malformed token values.
@pytest.mark.parametrize('method,url', [
    ('get', '/internal/tasks'),
    ('get', '/internal/tasks/1'),
    ('post', '/internal/tasks'),
    ('put', '/internal/tasks/1'),
    ('delete', '/internal/tasks/1'),
])
@pytest.mark.parametrize('token', [None, 'wrong-token', 'caf\xe9'])
def test_api_requires_token(client, method, url, token):
    headers = {} if token is None else {'X-Service-Token': token}
    assert getattr(client, method)(url, headers=headers).status_code == 401


# Deny task access when no expected service token is configured.
def test_api_fails_closed_without_configured_token(client, monkeypatch):
    monkeypatch.delenv('INTERNAL_API_TOKEN')
    assert client.get('/internal/tasks', headers=HEADERS).status_code == 401


# Return 400 for invalid write payloads without persisting tasks.
@pytest.mark.parametrize('method,url', [('post', '/internal/tasks'), ('put', '/internal/tasks/1')])
@pytest.mark.parametrize('payload', [None, [], {}, {'title': []}, {
    'title': [], 'description': '', 'priority': 'low', 'status': 'todo',
}])
def test_api_rejects_invalid_payload(client, method, url, payload):
    response = getattr(client, method)(url, json=payload, headers=HEADERS)
    assert response.status_code == 400
    assert crud.listing() == []


# Return 400 when write requests contain malformed JSON.
@pytest.mark.parametrize('method,url', [('post', '/internal/tasks'), ('put', '/internal/tasks/1')])
def test_api_rejects_malformed_json(client, method, url):
    response = getattr(client, method)(
        url, data='{invalid', content_type='application/json', headers=HEADERS,
    )
    assert response.status_code == 400


# Return 400 for unsupported or empty API filter values.
@pytest.mark.parametrize('query', ['status=unknown', 'priority=urgent', 'status='])
def test_api_rejects_invalid_filters(client, query):
    assert client.get(f'/internal/tasks?{query}', headers=HEADERS).status_code == 400


# Keep health public and report 503 when the task table is missing.
def test_health_checks_schema_without_authentication(client):
    response = client.get('/health')
    assert response.status_code == 200
    assert response.get_json() == {'service': 'database', 'status': 'ok'}
    with crud.connection() as db:
        db.execute('DROP TABLE tasks')
    response = client.get('/health')
    assert response.status_code == 503
    assert response.get_json()['status'] == 'unhealthy'


# Report unhealthy status when the configured database directory is unusable.
def test_health_handles_unusable_path(client, tmp_path, monkeypatch):
    blocker = tmp_path / 'not-a-directory'
    blocker.write_text('blocked', encoding='utf-8')
    monkeypatch.setenv('DATABASE_PATH', str(blocker / 'tasks.db'))
    assert client.get('/health').status_code == 503
