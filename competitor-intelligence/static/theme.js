// JA Assure Competitor Intelligence — explicit light/dark theme.
// Default is light ("proper light theme"). Choice persists in localStorage.
// Without a stored choice we follow the OS once, then lock that value so the
// toggle button always reflects the actual UI (fixes "no button" + stuck dark).
(function () {
  var KEY = 'ja-intel-theme';
  var root = document.documentElement;

  function systemTheme() {
    try {
      return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    } catch (_) {
      return 'light';
    }
  }

  function current() {
    var v = root.getAttribute('data-theme');
    return v === 'dark' || v === 'light' ? v : systemTheme();
  }

  function apply(theme) {
    var next = theme === 'dark' ? 'dark' : 'light';
    root.setAttribute('data-theme', next);
    root.style.colorScheme = next;
    try {
      localStorage.setItem(KEY, next);
    } catch (_) {}
    syncButtons(next);
    var meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.setAttribute('content', next === 'dark' ? '#000000' : '#fafafa');
  }

  function syncButtons(theme) {
    var isDark = theme === 'dark';
    document.querySelectorAll('[data-theme-toggle]').forEach(function (btn) {
      btn.setAttribute('aria-pressed', String(isDark));
      btn.setAttribute('aria-label', isDark ? 'Switch to light theme' : 'Switch to dark theme');
      var label = btn.querySelector('[data-theme-label]');
      if (label) label.textContent = isDark ? 'Light' : 'Dark';
      var moon = btn.querySelector('.theme-icon-moon');
      var sun = btn.querySelector('.theme-icon-sun');
      // Show the icon of the theme you will switch TO.
      if (moon) moon.style.display = isDark ? 'inline' : 'none';
      if (sun) sun.style.display = isDark ? 'none' : 'inline';
    });
  }

  function init() {
    var stored = null;
    try {
      stored = localStorage.getItem(KEY);
    } catch (_) {}
    apply(stored === 'dark' || stored === 'light' ? stored : systemTheme());
    document.querySelectorAll('[data-theme-toggle]').forEach(function (btn) {
      if (btn.dataset.bound) return;
      btn.dataset.bound = '1';
      btn.addEventListener('click', function () {
        apply(current() === 'dark' ? 'light' : 'dark');
      });
    });
  }

  window.JAIntelTheme = { apply: apply, current: current };
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init, { once: true });
  } else {
    init();
  }
})();
