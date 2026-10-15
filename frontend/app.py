import hmac
import os
import requests
from flask import Flask, Response, abort, jsonify, redirect, render_template, request, url_for

app=Flask(__name__)
BACKEND=lambda:os.getenv('BACKEND_URL','http://backend:5000').rstrip('/')
TOKEN=lambda:os.getenv('INTERNAL_API_TOKEN','')

def client(method,path,**kwargs):
    try:return requests.request(method,BACKEND()+path,headers={'X-Service-Token':TOKEN()},timeout=9,**kwargs)
    except requests.RequestException:return None

@app.before_request
def browser_auth():
    if request.path=='/health':return
    if request.method in ('POST','PUT','PATCH','DELETE') and request.headers.get('HX-Request') != 'true':
        abort(403)
    username=os.getenv('DEMO_USERNAME','')
    password=os.getenv('DEMO_PASSWORD','')
    credentials=request.authorization
    if not username or not password or not credentials or not (hmac.compare_digest(credentials.username or '',username) and hmac.compare_digest(credentials.password or '',password)):
        return Response('Authentication required',401,{'WWW-Authenticate':'Basic realm="DRA 2.0 Task Manager"'})

@app.get('/health')
def health():
    reply=client('GET','/health')
    if reply is not None and reply.ok:return jsonify(service='frontend',backend='ok',status='ok')
    return jsonify(service='frontend',backend='unhealthy',status='unhealthy'),503

def read_tasks():
    response=client('GET','/api/tasks',params={k:v for k,v in request.args.items() if k in ('status','priority') and v})
    if response is None or not response.ok: return None
    return response.json()

@app.get('/')
def index():
    tasks=read_tasks()
    return render_template('index.html',tasks=tasks, status=request.args.get('status',''),priority=request.args.get('priority','')), (200 if tasks is not None else 503)

@app.get('/tasks')
def tasks_fragment():
    tasks=read_tasks()
    return render_template('tasks.html',tasks=tasks), (200 if tasks is not None else 503)

@app.post('/tasks')
def create():
    response=client('POST','/api/tasks',json=dict(title=request.form.get('title',''),description=request.form.get('description',''),priority=request.form.get('priority','medium'),status=request.form.get('status','todo')))
    return mutation_result(response)

@app.post('/tasks/<int:task_id>/status')
def change_status(task_id):
    response=client('PUT',f'/api/tasks/{task_id}',json={'status':request.form.get('status','todo')})
    return mutation_result(response)

@app.post('/tasks/<int:task_id>/edit')
def change_task(task_id):
    response=client('PUT',f'/api/tasks/{task_id}',json={k:request.form.get(k,'') for k in ('title','description','status','priority')})
    return mutation_result(response)

@app.delete('/tasks/<int:task_id>')
def remove(task_id):
    response=client('DELETE',f'/api/tasks/{task_id}')
    return mutation_result(response)

def mutation_result(response):
    if response is None:return '<div class="notice error">Backend unavailable</div>',503
    if not response.ok:
        try:error=response.json().get('error','Request failed')
        except ValueError:error='Request failed'
        return render_template('tasks.html',tasks=read_tasks(),error=error),response.status_code
    tasks=read_tasks()
    return render_template('tasks.html',tasks=tasks),200 if tasks is not None else 503

if __name__=='__main__':app.run(host='0.0.0.0',port=8000)
