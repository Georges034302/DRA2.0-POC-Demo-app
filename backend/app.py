import hmac
import os

import requests
from flask import Flask, Response, jsonify, request
from itsdangerous import BadData, URLSafeTimedSerializer

TASK_FIELDS = ('title', 'description', 'priority', 'status')
REQUIRED_SETTINGS = ('SECRET_KEY', 'INTERNAL_API_TOKEN', 'DEMO_USERNAME', 'DEMO_PASSWORD')


# Reads the required settings from the environment and refuses to start if any is missing.
def load_settings():
    missing = [name for name in REQUIRED_SETTINGS if not os.environ.get(name)]
    if missing:
        raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")
    return {name: os.environ[name] for name in REQUIRED_SETTINGS}


app = Flask(__name__)
app.config.update(load_settings())
app.config['DATABASE_SERVICE_URL'] = os.environ.get('DATABASE_SERVICE_URL', 'http://localhost:5001')
app.config['DATABASE_TIMEOUT'] = 10
app.config['TOKEN_MAX_AGE'] = 8 * 60 * 60


# Builds a JSON error response.
def error(message, status):
    return jsonify({'status': 'error', 'message': message}), status


# Compares two strings in constant time.
def matches(provided, expected):
    return hmac.compare_digest(provided.encode(), expected.encode())


# Checks a username and password against the configured demo credentials.
def credentials_valid(username, password):
    if not isinstance(username, str) or not isinstance(password, str):
        return False
    username_ok = matches(username, app.config['DEMO_USERNAME'])
    password_ok = matches(password, app.config['DEMO_PASSWORD'])
    return username_ok and password_ok


# Creates a signed, expiring token for a logged-in user.
def issue_token(username):
    return URLSafeTimedSerializer(app.config['SECRET_KEY'], salt='dra-auth').dumps({'user': username})


# Tells whether a token has a valid signature and has not expired.
def token_valid(token):
    try:
        URLSafeTimedSerializer(app.config['SECRET_KEY'], salt='dra-auth').loads(
            token, max_age=app.config['TOKEN_MAX_AGE']
        )
    except BadData:
        return False
    return True


# Requires a valid bearer token on every task route.
@app.before_request
def require_login():
    if not request.path.startswith('/api/tasks'):
        return None
    scheme, _, token = request.headers.get('Authorization', '').partition(' ')
    if scheme != 'Bearer' or not token_valid(token):
        return error('Authentication required', 401)
    return None


# Calls the database service and relays its answer; its own failures become a 502.
def database_request(method, path, payload=None):
    try:
        upstream = requests.request(
            method,
            f"{app.config['DATABASE_SERVICE_URL']}{path}",
            json=payload,
            headers={'X-Internal-Token': app.config['INTERNAL_API_TOKEN']},
            timeout=app.config['DATABASE_TIMEOUT'],
        )
    except requests.RequestException:
        app.logger.exception('Database service request failed: %s %s', method, path)
        return error('Database service unavailable', 502)

    # A rejected internal token or a database crash is not the user's fault.
    if upstream.status_code in (401, 403) or upstream.status_code >= 500:
        app.logger.error('Database service returned %s for %s %s', upstream.status_code, method, path)
        return error('Database service error', 502)
    if upstream.status_code == 204:
        return '', 204
    return Response(upstream.content, status=upstream.status_code, content_type='application/json')


# Extracts only the known task fields from the request body, or None if it is not a JSON object.
def task_payload():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return None
    return {field: data[field] for field in TASK_FIELDS if field in data}


# Checks the demo credentials and returns a token.
@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict) or not credentials_valid(data.get('username'), data.get('password')):
        return error('Invalid credentials', 401)
    return jsonify({'status': 'success', 'message': 'Logged in', 'token': issue_token(data['username'])}), 200


# Lists all tasks.
@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    return database_request('GET', '/api/tasks')


# Creates a task.
@app.route('/api/tasks', methods=['POST'])
def create_task():
    payload = task_payload()
    if payload is None:
        return error('A JSON object body is required', 400)
    return database_request('POST', '/api/tasks', payload)


# Returns one task.
@app.route('/api/tasks/<int:task_id>', methods=['GET'])
def get_task(task_id):
    return database_request('GET', f'/api/tasks/{task_id}')


# Updates the given fields of a task.
@app.route('/api/tasks/<int:task_id>', methods=['PATCH'])
def update_task(task_id):
    payload = task_payload()
    if payload is None:
        return error('A JSON object body is required', 400)
    return database_request('PATCH', f'/api/tasks/{task_id}', payload)


# Deletes a task.
@app.route('/api/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    return database_request('DELETE', f'/api/tasks/{task_id}')


REDIRECT_PAGE = """<!doctype html>
<title>DRA 2.0 POC</title>
<script>
  const port = '%(port)s';
  const host = location.host.includes('-' + port + '.')
    ? location.host.replace('-' + port + '.', '-80.')
    : location.hostname;
  location.replace(location.protocol + '//' + host + '/');
</script>
<noscript>This is the backend API. Open the app on port 80.</noscript>
"""


# Sends anyone who opens this API's address in a browser to the frontend UI on port 80.
@app.route('/', methods=['GET'])
def index():
    return Response(REDIRECT_PAGE % {'port': 5000}, mimetype='text/html')


# Reports that the backend is running; used by the container health check.
@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy'}), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
