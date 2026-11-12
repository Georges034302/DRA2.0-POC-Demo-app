import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_TEST_ENV = {
    'SECRET_KEY': 'test-secret',
    'INTERNAL_API_TOKEN': 'test-internal-token',
    'DEMO_USERNAME': 'demo',
    'DEMO_PASSWORD': 'demo-pass',
}
DATABASE_TOKEN = 'test-internal-token'


# Loads the backend app by path under a unique name so it can be imported alongside the database app.
def load_backend_app():
    spec = importlib.util.spec_from_file_location('backend_app_security', REPO_ROOT / 'backend' / 'app.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.app


# Loads a database-service module by path under a unique name so it can be imported alongside the backend app.
def load_database_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, REPO_ROOT / 'database' / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


with patch.dict(os.environ, BACKEND_TEST_ENV):
    backend_app = load_backend_app()

database_init_db = load_database_module('database_init_db_security', 'init-db.py')
with patch.dict(os.environ, {'INTERNAL_API_TOKEN': DATABASE_TOKEN}):
    database_app = load_database_module('database_app_security', 'app.py').app


# Builds a fake response from the database service, for mocking backend -> database calls.
def upstream_response(status_code, body=b''):
    response = Mock()
    response.status_code = status_code
    response.content = body
    return response


class BackendAuthSecurityTests(unittest.TestCase):
    def setUp(self):
        self.client = backend_app.test_client()

    def test_wrong_or_malformed_credentials_are_rejected(self):
        for body in (
            {'username': 'demo', 'password': 'wrong'},
            {'username': 'other', 'password': 'demo-pass'},
            {'username': 'demo'},
            {'username': 5, 'password': 5},
            ['demo', 'demo-pass'],
            {},
        ):
            with self.subTest(body=body):
                self.assertEqual(self.client.post('/api/auth/login', json=body).status_code, 401)

    def test_tasks_require_a_valid_token(self):
        with patch('requests.request') as request_mock:
            self.assertEqual(self.client.get('/api/tasks').status_code, 401)
            self.assertEqual(self.client.get('/api/tasks', headers={'Authorization': 'Bearer nonsense'}).status_code, 401)
            self.assertEqual(self.client.get('/api/tasks', headers={'Authorization': 'mock-token'}).status_code, 401)
            request_mock.assert_not_called()

    def test_expired_token_is_rejected(self):
        token = self.client.post('/api/auth/login', json={'username': 'demo', 'password': 'demo-pass'}).json['token']
        with patch.dict(backend_app.config, {'TOKEN_MAX_AGE': -1}):
            response = self.client.get('/api/tasks', headers={'Authorization': f'Bearer {token}'})
        self.assertEqual(response.status_code, 401)


class BackendProxySecurityTests(unittest.TestCase):
    def setUp(self):
        self.client = backend_app.test_client()
        token = self.client.post('/api/auth/login', json={'username': 'demo', 'password': 'demo-pass'}).json['token']
        self.client.environ_base['HTTP_AUTHORIZATION'] = f'Bearer {token}'

    @patch('requests.request')
    def test_database_auth_failure_is_not_reported_as_user_auth_failure(self, request_mock):
        request_mock.return_value = upstream_response(401, b'{"status": "error", "message": "Unauthorized"}')

        self.assertEqual(self.client.get('/api/tasks').status_code, 502)


class DatabaseAuthSecurityTests(unittest.TestCase):
    def test_missing_internal_token_prevents_startup(self):
        with patch.dict(os.environ):
            os.environ.pop('INTERNAL_API_TOKEN', None)
            with self.assertRaisesRegex(RuntimeError, 'INTERNAL_API_TOKEN'):
                load_database_module('database_app_no_token_security', 'app.py')

    def test_internal_token_is_required(self):
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / 'tasks.db')
            database_init_db.init_db(path)
            database_app.config['DATABASE_PATH'] = path

            anonymous = database_app.test_client()
            self.assertEqual(anonymous.get('/api/tasks').status_code, 401)
            self.assertEqual(anonymous.get('/api/tasks', headers={'X-Internal-Token': 'wrong'}).status_code, 401)
            self.assertEqual(anonymous.get('/api/tasks', headers={'X-Internal-Token': DATABASE_TOKEN}).status_code, 200)
            self.assertEqual(anonymous.get('/health').status_code, 200)


if __name__ == '__main__':
    unittest.main()
