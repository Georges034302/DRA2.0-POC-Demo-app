import importlib.util
import os
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import requests

TEST_ENV = {
    'SECRET_KEY': 'test-secret',
    'INTERNAL_API_TOKEN': 'test-internal-token',
    'DEMO_USERNAME': 'demo',
    'DEMO_PASSWORD': 'demo-pass',
}
APP_PATH = Path(__file__).resolve().parents[1] / 'app.py'


# Loads the backend app by path under a unique name so backend and database tests can share one pytest run.
def load_app():
    spec = importlib.util.spec_from_file_location('backend_app', APP_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.app


with patch.dict(os.environ, TEST_ENV):
    app = load_app()


# Builds a fake response from the database service.
def upstream_response(status_code, body=b''):
    response = Mock()
    response.status_code = status_code
    response.content = body
    return response


class StartupTests(unittest.TestCase):
    def test_missing_settings_prevent_startup(self):
        with patch.dict(os.environ, TEST_ENV):
            del os.environ['SECRET_KEY']
            with self.assertRaisesRegex(RuntimeError, 'SECRET_KEY'):
                load_app()


class LoginTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_valid_credentials_return_a_token_that_unlocks_tasks(self):
        response = self.client.post('/api/auth/login', json={'username': 'demo', 'password': 'demo-pass'})
        self.assertEqual(response.status_code, 200)

        with patch('requests.request', return_value=upstream_response(200, b'[]')):
            tasks = self.client.get('/api/tasks', headers={'Authorization': f"Bearer {response.json['token']}"})
        self.assertEqual(tasks.status_code, 200)

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
        with patch.dict(app.config, {'TOKEN_MAX_AGE': -1}):
            response = self.client.get('/api/tasks', headers={'Authorization': f'Bearer {token}'})
        self.assertEqual(response.status_code, 401)

    def test_health_needs_no_token(self):
        self.assertEqual(self.client.get('/health').status_code, 200)

    def test_root_redirects_browsers_to_the_frontend(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, 'text/html')
        self.assertIn("'5000'", response.get_data(as_text=True))
        self.assertIn("'-80.'", response.get_data(as_text=True))


class TaskProxyTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        token = self.client.post('/api/auth/login', json={'username': 'demo', 'password': 'demo-pass'}).json['token']
        self.client.environ_base['HTTP_AUTHORIZATION'] = f'Bearer {token}'

    @patch('requests.request')
    def test_list_relays_database_response_with_internal_token(self, request_mock):
        request_mock.return_value = upstream_response(200, b'[{"id": 1, "status": "todo"}]')

        response = self.client.get('/api/tasks')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, [{'id': 1, 'status': 'todo'}])
        args, kwargs = request_mock.call_args
        self.assertEqual(args, ('GET', 'http://localhost:5001/api/tasks'))
        self.assertEqual(kwargs['headers'], {'X-Internal-Token': 'test-internal-token'})

    @patch('requests.request')
    def test_create_forwards_only_known_fields(self, request_mock):
        request_mock.return_value = upstream_response(201, b'{"id": 2}')

        response = self.client.post('/api/tasks', json={
            'title': 'New',
            'priority': 'high',
            'status': 'in_progress',
            'id': 99,
            'unexpected': 'ignored',
        })

        self.assertEqual(response.status_code, 201)
        self.assertEqual(request_mock.call_args.kwargs['json'], {
            'title': 'New',
            'priority': 'high',
            'status': 'in_progress',
        })

    @patch('requests.request')
    def test_database_validation_errors_are_relayed(self, request_mock):
        request_mock.return_value = upstream_response(400, b'{"status": "error", "message": "bad status"}')

        response = self.client.post('/api/tasks', json={'title': 'x', 'status': 'pending'})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json['message'], 'bad status')

    @patch('requests.request')
    def test_update_and_delete_use_database_routes(self, request_mock):
        request_mock.return_value = upstream_response(200, b'{"id": 3}')
        self.assertEqual(self.client.patch('/api/tasks/3', json={'status': 'done'}).status_code, 200)
        self.assertEqual(request_mock.call_args.args, ('PATCH', 'http://localhost:5001/api/tasks/3'))

        request_mock.return_value = upstream_response(204)
        self.assertEqual(self.client.delete('/api/tasks/3').status_code, 204)
        self.assertEqual(request_mock.call_args.args, ('DELETE', 'http://localhost:5001/api/tasks/3'))

    @patch('requests.request')
    def test_non_object_body_is_rejected_without_calling_database(self, request_mock):
        response = self.client.post('/api/tasks', json=['not', 'an', 'object'])

        self.assertEqual(response.status_code, 400)
        request_mock.assert_not_called()

    @patch('requests.request')
    def test_database_auth_failure_is_not_reported_as_user_auth_failure(self, request_mock):
        request_mock.return_value = upstream_response(401, b'{"status": "error", "message": "Unauthorized"}')

        self.assertEqual(self.client.get('/api/tasks').status_code, 502)

    @patch('requests.request')
    def test_database_server_error_returns_502(self, request_mock):
        request_mock.return_value = upstream_response(500, b'<html>boom</html>')

        self.assertEqual(self.client.get('/api/tasks').status_code, 502)

    @patch('requests.request', side_effect=requests.ConnectionError('refused'))
    def test_unreachable_database_returns_502(self, _request_mock):
        response = self.client.get('/api/tasks')

        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json['message'], 'Database service unavailable')


if __name__ == '__main__':
    unittest.main()
