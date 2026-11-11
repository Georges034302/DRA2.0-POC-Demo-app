/* DRA 2.0 POC - Theme toggle + Kanban board with drag-drop task management */

// ============================================================================
// THEME MANAGER
// ============================================================================

class ThemeManager {
  constructor() {
    this.theme = localStorage.getItem("theme") || "dark";
    this.applyTheme();
  }

  applyTheme() {
    document.documentElement.setAttribute("data-theme", this.theme);
    this.updateToggleButton();
  }

  updateToggleButton() {
    const button = document.querySelector(".theme-toggle");
    if (button) {
      button.textContent = this.theme === "dark" ? "☀️" : "🌙";
      button.setAttribute("title", this.theme === "dark" ? "Switch to light mode" : "Switch to dark mode");
    }
  }

  toggle() {
    this.theme = this.theme === "dark" ? "light" : "dark";
    localStorage.setItem("theme", this.theme);
    this.applyTheme();
  }
}

const themeManager = new ThemeManager();

document.addEventListener("DOMContentLoaded", () => {
  const themeToggle = document.querySelector(".theme-toggle");
  if (themeToggle) {
    themeToggle.addEventListener("click", () => themeManager.toggle());
  }
  themeManager.updateToggleButton();
  
  // Initialize Kanban board on dashboard
  if (document.getElementById("kanbanBoard")) {
    initKanbanBoard();
  }
});

// ============================================================================
// KANBAN BOARD - DRAG-DROP & STATUS MANAGEMENT
// ============================================================================

let draggedTask = null;

function initKanbanBoard() {
  console.log("Initializing Kanban board...");
  loadTasks();
  setupDragDropListeners();
}

// Load tasks and render them in their respective columns
async function loadTasks() {
  console.log("Loading tasks...");
  try {
    const response = await apiFetch('/api/tasks');
    console.log("Response status:", response.status);
    
    if (!response.ok) {
      throw new Error(await responseError(response, 'Failed to load tasks'));
    }
    
    const tasks = await response.json();
    console.log("Tasks loaded:", tasks.length, tasks);
    renderKanbanBoard(tasks);
  } catch (error) {
    console.error('Error loading tasks:', error);
    showError('Failed to load tasks');
  }
}

// Render tasks grouped by status in their columns
function renderKanbanBoard(tasks) {
  console.log("Rendering Kanban board with", tasks.length, "tasks");
  
  // Clear all columns first
  const columnIds = ['tasks-pending', 'tasks-in_progress', 'tasks-done'];
  columnIds.forEach(id => {
    const col = document.getElementById(id);
    if (col) col.innerHTML = '';
  });

  // Group tasks by status
  const grouped = {
    'pending': [],
    'in_progress': [],
    'done': []
  };

  tasks.forEach(task => {
    // Normalize status: map 'todo' → 'pending' for backward compatibility
    let status = (task.status || 'pending').toLowerCase();
    if (status === 'todo') status = 'pending';
    
    if (grouped[status]) {
      grouped[status].push(task);
    } else {
      console.warn(`Unknown task status: ${status}`, task);
    }
  });

  console.log("Grouped tasks:", grouped);

  // Render each column
  const statusMap = {
    'pending': 'tasks-pending',
    'in_progress': 'tasks-in_progress',
    'done': 'tasks-done'
  };

  Object.entries(statusMap).forEach(([status, columnId]) => {
    const column = document.getElementById(columnId);
    const countEl = document.getElementById(`count-${status}`);
    const taskList = grouped[status] || [];

    if (column) {
      if (taskList.length === 0) {
        column.innerHTML = '<p style="color: var(--text-secondary); text-align: center; padding: 1rem;">No tasks</p>';
      } else {
        let html = '';
        taskList.forEach(task => {
          html += createTaskCard(task);
        });
        column.innerHTML = html;
        attachTaskCardListeners(column);
      }
    }

    if (countEl) {
      countEl.textContent = taskList.length;
    }
  });
}

// Create HTML for a task card
function createTaskCard(task) {
  const desc = task.description ? `<div class="task-card-desc">${escapeHtml(task.description)}</div>` : '';
  return `
    <div class="task-card" draggable="true" data-task-id="${task.id}">
      <div class="task-card-title" onclick="editTask(${task.id})">${escapeHtml(task.title)}</div>
      ${desc}
      <div class="task-card-meta">
        <span>${formatDate(task.created_at)}</span>
      </div>
      <button class="task-delete-btn" onclick="deleteTask(${task.id}, event)">🗑️</button>
    </div>
  `;
}

// Attach event listeners for task card interactions
function attachTaskCardListeners(column) {
  const cards = column.querySelectorAll('.task-card');
  cards.forEach(card => {
    card.addEventListener('dragstart', handleDragStart);
    card.addEventListener('dragend', handleDragEnd);
  });
}

// Setup drop zones on all kanban columns
function setupDragDropListeners() {
  const dropZones = document.querySelectorAll('.kanban-tasks');
  dropZones.forEach(zone => {
    zone.addEventListener('dragover', handleDragOver);
    zone.addEventListener('dragleave', handleDragLeave);
    zone.addEventListener('drop', handleDrop);
  });
}

// Drag start handler
function handleDragStart(e) {
  draggedTask = this;
  this.classList.add('dragging');
  e.dataTransfer.effectAllowed = 'move';
}

// Drag end handler
function handleDragEnd(e) {
  this.classList.remove('dragging');
  document.querySelectorAll('.kanban-tasks').forEach(zone => {
    zone.classList.remove('drag-over');
  });
  draggedTask = null;
}

// Drag over handler (show drop zone hint)
function handleDragOver(e) {
  e.preventDefault();
  e.dataTransfer.dropEffect = 'move';
  this.classList.add('drag-over');
}

// Drag leave handler
function handleDragLeave(e) {
  if (e.target === this) {
    this.classList.remove('drag-over');
  }
}

// Drop handler
async function handleDrop(e) {
  e.preventDefault();
  this.classList.remove('drag-over');

  if (!draggedTask) return;

  const taskId = parseInt(draggedTask.getAttribute('data-task-id'));
  const newStatus = this.closest('.kanban-column').getAttribute('data-status');

  console.log(`Moving task ${taskId} to ${newStatus}`);
  await updateTaskStatus(taskId, newStatus);
}

// Update task status (API call)
async function updateTaskStatus(taskId, newStatus) {
  try {
    const response = await apiFetch(`/api/tasks/${taskId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: newStatus })
    });

    if (!response.ok) {
      throw new Error(await responseError(response, 'Failed to update task'));
    }

    loadTasks();
  } catch (error) {
    console.error('Error updating task:', error);
    showError('Failed to move task');
    loadTasks();
  }
}

// ============================================================================
// TASK CRUD OPERATIONS
// ============================================================================

function openNewTaskForm() {
  document.getElementById('taskId').value = '';
  document.getElementById('taskForm').reset();
  document.getElementById('taskStatus').value = 'pending';
  document.getElementById('taskModal').showModal();
}

async function editTask(taskId) {
  try {
    const response = await apiFetch(`/api/tasks/${taskId}`);
    if (!response.ok) throw new Error('Task not found');

    const task = await response.json();
    document.getElementById('taskId').value = task.id;
    document.getElementById('taskTitle').value = task.title;
    document.getElementById('taskDesc').value = task.description || '';
    document.getElementById('taskStatus').value = task.status || 'pending';
    document.getElementById('taskModal').showModal();
  } catch (error) {
    console.error('Error loading task:', error);
    showError('Failed to load task');
  }
}

async function saveTask(event) {
  event.preventDefault();

  const taskId = document.getElementById('taskId').value;
  const title = document.getElementById('taskTitle').value.trim();
  const description = document.getElementById('taskDesc').value.trim();
  const status = document.getElementById('taskStatus').value;

  if (!title) {
    showError('Task title is required');
    return;
  }

  try {
    let response;
    if (taskId) {
      response = await apiFetch(`/api/tasks/${taskId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title, description, status })
      });
    } else {
      response = await apiFetch('/api/tasks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title, description, status })
      });
    }

    if (!response.ok) {
      throw new Error(await responseError(response, 'Failed to save task'));
    }

    document.getElementById('taskModal').close();
    loadTasks();
    showSuccess(taskId ? 'Task updated' : 'Task created');
  } catch (error) {
    console.error('Error saving task:', error);
    showError('Failed to save task');
  }
}

async function deleteTask(taskId, event) {
  event.stopPropagation();

  if (!confirm('Delete this task?')) return;

  try {
    const response = await apiFetch(`/api/tasks/${taskId}`, { method: 'DELETE' });
    if (!response.ok) {
      throw new Error(await responseError(response, 'Failed to delete task'));
    }

    loadTasks();
    showSuccess('Task deleted');
  } catch (error) {
    console.error('Error deleting task:', error);
    showError('Failed to delete task');
  }
}

// ============================================================================
// API & UTILITY FUNCTIONS
// ============================================================================

async function apiFetch(url, options = {}) {
  const token = localStorage.getItem('auth_token');
  console.log("apiFetch for:", url, "token exists:", !!token);
  
  if (!token) {
    console.error("No auth token! Redirecting to login...");
    logout();
    throw new Error('No authentication token');
  }
  
  const response = await fetch(url, {
    ...options,
    credentials: 'include',
    headers: { 
      ...options.headers, 
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    }
  });
  
  console.log("Response status:", response.status);
  
  if (response.status === 401) {
    console.error("401 Unauthorized - logging out");
    logout();
    throw new Error('Session expired');
  }
  return response;
}

async function responseError(response, fallback) {
  try {
    const body = await response.json();
    return body.message || fallback;
  } catch {
    return fallback;
  }
}

function logout() {
  localStorage.removeItem('auth_token');
  window.location.href = '/';
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function formatDate(dateStr) {
  if (!dateStr) return '';
  const date = new Date(dateStr);
  return date.toLocaleDateString();
}

function showError(message) {
  alert(`❌ ${message}`);
}

function showSuccess(message) {
  alert(`✅ ${message}`);
}
