/* DRA 2.0 POC - theme toggle shared by the login and dashboard pages */

class ThemeManager {
  // Restores the saved theme (dark by default) and applies it.
  constructor() {
    this.theme = localStorage.getItem("theme") || "dark";
    this.applyTheme();
  }

  // Sets the theme on the document and refreshes the toggle button.
  applyTheme() {
    document.documentElement.setAttribute("data-theme", this.theme);
    this.updateToggleButton();
  }

  // Updates the toggle button icon and tooltip to match the current theme.
  updateToggleButton() {
    const button = document.querySelector(".theme-toggle");
    if (button) {
      button.textContent = this.theme === "dark" ? "☀️" : "🌙";
      button.setAttribute("title", this.theme === "dark" ? "Switch to light mode" : "Switch to dark mode");
    }
  }

  // Switches between dark and light and remembers the choice.
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
});
