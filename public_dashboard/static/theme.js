'use strict';

// Apply before CSS paints; keep the preference local and separate from analysis URLs.
(() => {
  const system = window.matchMedia('(prefers-color-scheme: dark)');
  let preference = null;
  try {
    const saved = localStorage.getItem('skillscope-theme');
    if (saved === 'light' || saved === 'dark') preference = saved;
  } catch {
    // Storage may be disabled. The toggle still works for this page.
  }

  function apply() {
    const theme = preference || (system.matches ? 'dark' : 'light');
    document.documentElement.dataset.theme = theme;
    const toggle = document.getElementById('theme-toggle');
    if (toggle) {
      toggle.setAttribute('aria-pressed', String(theme === 'dark'));
      toggle.title = `Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`;
    }
  }

  apply();
  system.addEventListener('change', apply);
  document.addEventListener('DOMContentLoaded', () => {
    apply();
    document.getElementById('theme-toggle').addEventListener('click', () => {
      preference = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
      try {
        localStorage.setItem('skillscope-theme', preference);
      } catch {
        // Do not let a storage restriction interrupt the dashboard.
      }
      apply();
    });
  });
})();
