/**
 * DRA 2.0 POC - Frontend Application Logic
 * Handles theme toggle, HTMX event handling, and UI interactions
 */

// ============================================================================
// Theme Management
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
});

// ============================================================================
// Modal Management
// ============================================================================

class ModalManager {
  constructor() {
    this.modals = new Map();
    this.setupDefaultHandlers();
  }

  setupDefaultHandlers() {
    document.addEventListener("click", (e) => {
      if (e.target.classList.contains("modal-overlay")) {
        this.closeAll();
      }

      if (e.target.classList.contains("modal-close")) {
        const modal = e.target.closest(".modal-overlay");
        if (modal) {
          this.close(modal.id);
        }
      }
    });

    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") {
        this.closeAll();
      }
    });
  }

  open(modalId) {
    const overlay = document.getElementById(modalId);
    if (overlay) {
      overlay.classList.add("active");
      this.modals.set(modalId, true);
      document.body.style.overflow = "hidden";
    }
  }

  close(modalId) {
    const overlay = document.getElementById(modalId);
    if (overlay) {
      overlay.classList.remove("active");
      this.modals.delete(modalId);
      if (this.modals.size === 0) {
        document.body.style.overflow = "";
      }
    }
  }

  closeAll() {
    this.modals.forEach((_, modalId) => this.close(modalId));
  }

  toggle(modalId) {
    const overlay = document.getElementById(modalId);
    if (overlay && overlay.classList.contains("active")) {
      this.close(modalId);
    } else {
      this.open(modalId);
    }
  }
}

const modalManager = new ModalManager();

// ============================================================================
// HTMX Event Handlers
// ============================================================================

document.addEventListener("htmx:xhr:loadstart", (e) => {
  console.log("[HTMX] Request started");
});

document.addEventListener("htmx:afterSettle", (e) => {
  console.log("[HTMX] Response settled");
  initializeTaskHandlers(e.detail.target);
});

document.addEventListener("htmx:responseError", (e) => {
  console.error("[HTMX] Response error:", e.detail);
  showAlert("An error occurred. Please try again.", "error");
});

// ============================================================================
// Task Management
// ============================================================================

function initializeTaskHandlers(container = document) {
  container.querySelectorAll(".btn-delete-task").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.preventDefault();
      const taskId = btn.dataset.taskId;
      if (confirm("Delete this task?")) {
        htmx.ajax("DELETE", `/api/tasks/${taskId}`, {
          target: `#task-${taskId}`,
          swap: "outerHTML swap:1s",
          onError: () => showAlert("Failed to delete task", "error"),
          onSuccess: () => showAlert("Task deleted", "success"),
        });
      }
    });
  });

  container.querySelectorAll(".btn-edit-task").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.preventDefault();
      const taskId = btn.dataset.taskId;
      modalManager.open("editTaskModal");
      htmx.ajax("GET", `/api/tasks/${taskId}/edit`, {
        target: "#editTaskForm",
        swap: "innerHTML",
      });
    });
  });

  container.querySelectorAll(".task-status-select").forEach((select) => {
    select.addEventListener("change", (e) => {
      const taskId = e.target.dataset.taskId;
      const newStatus = e.target.value;
      htmx.ajax("PATCH", `/api/tasks/${taskId}`, {
        values: { status: newStatus },
        swap: "none",
        onError: () => showAlert("Failed to update", "error"),
        onSuccess: () => showAlert("Updated", "success"),
      });
    });
  });
}

document.addEventListener("DOMContentLoaded", () => {
  initializeTaskHandlers();
});

// ============================================================================
// Notification System
// ============================================================================

function showAlert(message, type = "info") {
  const container = document.getElementById("alertContainer");
  if (!container) return;

  const alert = document.createElement("div");
  alert.className = `alert alert-${type}`;
  alert.innerHTML = `
    <span class="alert-icon">${getAlertIcon(type)}</span>
    <span>${message}</span>
  `;

  container.appendChild(alert);

  setTimeout(() => {
    alert.style.animation = "fadeOut 0.3s ease";
    setTimeout(() => alert.remove(), 300);
  }, 5000);
}

function getAlertIcon(type) {
  const icons = {
    success: "✓",
    error: "✕",
    warning: "⚠",
    info: "ℹ",
  };
  return icons[type] || "✓";
}

// ============================================================================
// Utility Functions
// ============================================================================

function formatDate(dateString) {
  const date = new Date(dateString);
  return date.toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function formatTime(dateString) {
  const date = new Date(dateString);
  return date.toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

function getAuthToken() {
  return localStorage.getItem("authToken");
}

function setAuthToken(token) {
  localStorage.setItem("authToken", token);
}

function clearAuthToken() {
  localStorage.removeItem("authToken");
}

// ============================================================================
// HTMX Global Configuration
// ============================================================================

document.addEventListener("DOMContentLoaded", () => {
  if (typeof htmx !== "undefined") {
    htmx.on("htmx:configRequest", (detail) => {
      const token = getAuthToken();
      if (token) {
        detail.xhr.setRequestHeader("Authorization", `Bearer ${token}`);
      }
    });
  }
});

// ============================================================================
// Exports for global use
// ============================================================================

window.themeManager = themeManager;
window.modalManager = modalManager;
window.showAlert = showAlert;
window.formatDate = formatDate;
window.formatTime = formatTime;
window.getAuthToken = getAuthToken;
window.setAuthToken = setAuthToken;
window.clearAuthToken = clearAuthToken;
