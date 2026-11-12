import importlib.util
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

DATABASE_DIR = Path(__file__).resolve().parents[2] / 'database'
TOKEN = 'test-internal-token'


# Loads a database-service module by path under a unique name so backend and database tests can share one pytest run.
def load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, DATABASE_DIR / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


init_db_script = load_module('database_init_db', 'init-db.py')
with patch.dict(os.environ, {'INTERNAL_API_TOKEN': TOKEN}):
    app = load_module('database_app', 'app.py').app


class StartupTests(unittest.TestCase):
    def test_missing_internal_token_prevents_startup(self):
        with patch.dict(os.environ):
            os.environ.pop('INTERNAL_API_TOKEN', None)
            with self.assertRaisesRegex(RuntimeError, 'INTERNAL_API_TOKEN'):
                load_module('database_app_no_token', 'app.py')


class InitDbTests(unittest.TestCase):
    def test_creates_schema_and_seeds_once(self):
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / 'nested' / 'tasks.db')

            self.assertEqual(init_db_script.init_db(path), len(init_db_script.SEED_TASKS))
            self.assertEqual(init_db_script.init_db(path), 0)

            with sqlite3.connect(path) as connection:
                (count,) = connection.execute('SELECT COUNT(*) FROM tasks').fetchone()
            self.assertEqual(count, len(init_db_script.SEED_TASKS))

    def test_existing_data_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / 'tasks.db')
            with sqlite3.connect(path) as connection:
                connection.execute(init_db_script.SCHEMA)
                connection.execute("INSERT INTO tasks (title) VALUES ('Existing')")

            self.assertEqual(init_db_script.init_db(path), 0)

            with sqlite3.connect(path) as connection:
                titles = [row[0] for row in connection.execute('SELECT title FROM tasks')]
            self.assertEqual(titles, ['Existing'])


class TaskApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        path = str(Path(self.temp_dir.name) / 'tasks.db')
        init_db_script.init_db(path)
        app.config['DATABASE_PATH'] = path
        self.client = app.test_client()
        self.client.environ_base['HTTP_X_INTERNAL_TOKEN'] = TOKEN

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_list_returns_seed_tasks(self):
        response = self.client.get('/api/tasks')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json), len(init_db_script.SEED_TASKS))

    def test_create_applies_defaults(self):
        response = self.client.post('/api/tasks', json={'title': '  New task  '})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json['title'], 'New task')
        self.assertEqual(response.json['status'], 'todo')
        self.assertEqual(response.json['priority'], 'medium')
        self.assertEqual(self.client.get(f"/api/tasks/{response.json['id']}").json['title'], 'New task')

    def test_create_validation(self):
        for body in (
            {},
            {'title': '   '},
            {'title': 'x' * 201},
            {'title': 'ok', 'status': 'pending'},
            {'title': 'ok', 'priority': 'urgent'},
            {'title': 'ok', 'description': 5},
        ):
            with self.subTest(body=body):
                self.assertEqual(self.client.post('/api/tasks', json=body).status_code, 400)
        self.assertEqual(self.client.post('/api/tasks', data='not json').status_code, 400)

    def test_update_changes_only_given_fields(self):
        task_id = self.client.post('/api/tasks', json={'title': 'Edit me', 'priority': 'low'}).json['id']

        response = self.client.patch(f'/api/tasks/{task_id}', json={'status': 'done'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['status'], 'done')
        self.assertEqual(response.json['title'], 'Edit me')
        self.assertEqual(response.json['priority'], 'low')

    def test_update_errors(self):
        task_id = self.client.post('/api/tasks', json={'title': 'Edit me'}).json['id']
        self.assertEqual(self.client.patch(f'/api/tasks/{task_id}', json={'status': 'pending'}).status_code, 400)
        self.assertEqual(self.client.patch(f'/api/tasks/{task_id}', json={}).status_code, 400)
        self.assertEqual(self.client.patch('/api/tasks/9999', json={'status': 'done'}).status_code, 404)

    def test_delete(self):
        task_id = self.client.post('/api/tasks', json={'title': 'Remove me'}).json['id']
        self.assertEqual(self.client.delete(f'/api/tasks/{task_id}').status_code, 204)
        self.assertEqual(self.client.get(f'/api/tasks/{task_id}').status_code, 404)
        self.assertEqual(self.client.delete(f'/api/tasks/{task_id}').status_code, 404)

    def test_internal_token_is_required(self):
        anonymous = app.test_client()
        self.assertEqual(anonymous.get('/api/tasks').status_code, 401)
        self.assertEqual(anonymous.get('/api/tasks', headers={'X-Internal-Token': 'wrong'}).status_code, 401)
        self.assertEqual(anonymous.get('/api/tasks', headers={'X-Internal-Token': TOKEN}).status_code, 200)
        self.assertEqual(anonymous.get('/health').status_code, 200)

    def test_root_redirects_browsers_to_the_frontend(self):
        response = app.test_client().get('/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, 'text/html')
        self.assertIn("'5001'", response.get_data(as_text=True))
        self.assertIn("'-80.'", response.get_data(as_text=True))


if __name__ == '__main__':
    unittest.main()
