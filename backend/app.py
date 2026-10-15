import hmac
import os
import requests
from flask import Flask, abort, jsonify, request
from tasks import validate

app=Flask(__name__)
DB=lambda: os.getenv('DATABASE_URL','http://database:5000').rstrip('/')
TOKEN=lambda: os.getenv('INTERNAL_API_TOKEN','')

@app.before_request
def protect():
    if request.path=='/health': return
    if not TOKEN() or not hmac.compare_digest(request.headers.get('X-Service-Token',''), TOKEN()): abort(401)

def call(method,path,**kwargs):
    try:
        return requests.request(method, DB()+path, headers={'X-Service-Token': TOKEN()}, timeout=8, **kwargs)
    except requests.RequestException:
        return None

def forwarded(resp):
    if resp is None: return jsonify(error='Database service unavailable'),503
    if resp.status_code==204:return '',204
    try:return jsonify(resp.json()),resp.status_code
    except ValueError:return jsonify(error='Invalid database response'),502

@app.get('/health')
def health():
    response=call('GET','/health')
    if response is not None and response.ok:return jsonify(service='backend',database='ok',status='ok')
    return jsonify(service='backend',database='unavailable',status='unhealthy'),503

@app.get('/api/tasks')
def listing():
    return forwarded(call('GET','/internal/tasks',params=request.args))

@app.get('/api/tasks/<int:task_id>')
def get(task_id):
    return forwarded(call('GET',f'/internal/tasks/{task_id}'))

@app.post('/api/tasks')
def create():
    try: data=validate(request.get_json(silent=True))
    except ValueError as e:return jsonify(error=str(e)),400
    return forwarded(call('POST','/internal/tasks',json=data))

@app.put('/api/tasks/<int:task_id>')
def update(task_id):
    existing=call('GET',f'/internal/tasks/{task_id}')
    if existing is None or not existing.ok:return forwarded(existing)
    try: data=validate(request.get_json(silent=True), existing.json())
    except (ValueError,TypeError) as e:return jsonify(error=str(e)),400
    return forwarded(call('PUT',f'/internal/tasks/{task_id}',json=data))

@app.delete('/api/tasks/<int:task_id>')
def delete(task_id):
    return forwarded(call('DELETE',f'/internal/tasks/{task_id}'))

if __name__=='__main__':app.run(host='0.0.0.0',port=5000)
