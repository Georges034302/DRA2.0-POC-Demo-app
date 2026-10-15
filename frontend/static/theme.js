(() => {
  const root = document.documentElement;
  const saved = localStorage.getItem('dra-theme');
  const initial = saved === 'dark' || saved === 'light' ? saved : (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
  root.dataset.theme = initial;
  const sync = () => { const label = document.getElementById('theme-name'); const icon = document.getElementById('theme-symbol'); if(label)label.textContent = root.dataset.theme === 'dark' ? 'Light mode' : 'Dark mode'; if(icon)icon.textContent = root.dataset.theme === 'dark' ? '☀' : '☾'; };
  document.addEventListener('DOMContentLoaded', () => { sync(); document.getElementById('theme-toggle').addEventListener('click', () => { root.dataset.theme = root.dataset.theme === 'dark' ? 'light' : 'dark'; localStorage.setItem('dra-theme', root.dataset.theme); sync(); }); });
})();
