from flask import Flask, render_template, request, session, jsonify, redirect, url_for, flash
from functools import wraps
import os
import json
from datetime import datetime
from models import db, Task, init_db

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-prod')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///tasks.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# Demo credentials
DEMO_USERNAME = os.getenv('DEMO_USERNAME', 'user')
DEMO_PASSWORD = os.getenv('DEMO_PASSWORD', 'password')


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.headers.get('Accept') == 'application/json':
                return jsonify(error='Unauthorized'), 401
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


# Initialize database once at startup
with app.app_context():
    db.create_all()


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify(service='backend', status='ok', database='connected')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handle login"""
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        
        if username == DEMO_USERNAME and password == DEMO_PASSWORD:
            session['user_id'] = 1
            session['username'] = username
            flash('Logged in successfully', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials', 'error')
    
    return render_template('login.html')


@app.route('/logout', methods=['POST'])
@login_required
def logout():
    """Handle logout"""
    session.clear()
    flash('Logged out successfully', 'success')
    return redirect(url_for('login'))


@app.route('/', methods=['GET'])
@login_required
def dashboard():
    """Dashboard page"""
    return render_template('dashboard.html')


@app.route('/api/tasks', methods=['GET'])
@login_required
def list_tasks():
    """List all tasks, optionally filtered by status"""
    status = request.args.get('status', '')
    query = Task.query
    
    if status:
        query = query.filter_by(status=status)
    
    tasks = query.order_by(Task.created_at.desc()).all()
    
    if request.headers.get('HX-Request'):
        return render_template('task_list.html', tasks=tasks)
    
    return jsonify([task.to_dict() for task in tasks])


@app.route('/api/tasks', methods=['POST'])
@login_required
def create_task():
    """Create a new task"""
    data = request.get_json() or request.form.to_dict()
    
    title = data.get('title', '').strip()
    description = data.get('description', '').strip()
    status = data.get('status', 'pending')
    
    if not title:
        return jsonify(error='Title is required'), 400
    
    if len(title) > 200:
        return jsonify(error='Title too long'), 400
    
    if status not in ['pending', 'in_progress', 'completed']:
        return jsonify(error='Invalid status'), 400
    
    task = Task(title=title, description=description, status=status)
    db.session.add(task)
    db.session.commit()
    
    return jsonify(task.to_dict()), 201


@app.route('/api/tasks/<int:task_id>', methods=['GET'])
@login_required
def get_task(task_id):
    """Get a single task"""
    task = Task.query.get_or_404(task_id)
    return jsonify(task.to_dict())


@app.route('/api/tasks/<int:task_id>/edit', methods=['GET'])
@login_required
def edit_task_form(task_id):
    """Get edit form for task (HTMX)"""
    task = Task.query.get_or_404(task_id)
    return render_template('task_form.html', task=task)


@app.route('/api/tasks/<int:task_id>', methods=['PATCH'])
@login_required
def update_task(task_id):
    """Update a task"""
    task = Task.query.get_or_404(task_id)
    data = request.get_json() or request.form.to_dict()
    
    if 'title' in data:
        title = data['title'].strip()
        if not title or len(title) > 200:
            return jsonify(error='Invalid title'), 400
        task.title = title
    
    if 'description' in data:
        task.description = data['description'].strip()
    
    if 'status' in data:
        if data['status'] not in ['pending', 'in_progress', 'completed']:
            return jsonify(error='Invalid status'), 400
        task.status = data['status']
    
    task.updated_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify(task.to_dict())


@app.route('/api/tasks/<int:task_id>', methods=['DELETE'])
@login_required
def delete_task(task_id):
    """Delete a task"""
    task = Task.query.get_or_404(task_id)
    db.session.delete(task)
    db.session.commit()
    
    return '', 204


@app.errorhandler(404)
def not_found(e):
    """404 error handler"""
    return jsonify(error='Not found'), 404


@app.errorhandler(500)
def server_error(e):
    """500 error handler"""
    return jsonify(error='Server error'), 500


if __name__ == '__main__':
    with app.app_context():
        init_db()
    app.run(host='0.0.0.0', port=5000, debug=False)

