const $ = (selector) => document.querySelector(selector);

async function request(path, options) {
  const response = await fetch(path, options);
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.detail || `Request failed (${response.status})`);
  return payload;
}

function showNotice(message, tone = 'warning') {
  const container = $('#toast-container');
  if (!container) return;
  const toast = document.createElement('div');
  toast.className = `toast toast-${tone}`;
  toast.setAttribute('role', tone === 'info' ? 'status' : 'alert');
  const text = document.createElement('span');
  text.className = 'toast-message';
  text.textContent = message;
  const close = document.createElement('button');
  close.className = 'toast-close';
  close.setAttribute('aria-label', 'Dismiss notification');
  close.textContent = '×';
  close.addEventListener('click', () => toast.remove());
  toast.append(text, close);
  container.append(toast);
  window.setTimeout(() => {
    toast.classList.add('is-leaving');
    window.setTimeout(() => toast.remove(), 250);
  }, 6000);
}

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>'"]/g, (character) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[character]));
}

function eventIdFromPath() {
  const parts = window.location.pathname.split('/').filter(Boolean);
  if (parts.length < 3 || parts[0] !== 'event' || parts[parts.length - 1] !== 'diff') return '';
  return decodeURIComponent(parts.slice(1, -1).join('/'));
}

function renderDiff(el, text) {
  if (!text) {
    el.textContent = 'No line changes in the captured evidence.';
    return;
  }
  el.innerHTML = text.split('\n').map((line) => {
    let cls = '';
    if (line.startsWith('@@')) cls = 'diff-hunk';
    else if (line.startsWith('+++') || line.startsWith('---')) cls = 'diff-meta';
    else if (line.startsWith('+')) cls = 'diff-add';
    else if (line.startsWith('-')) cls = 'diff-del';
    return `<span class="dl${cls ? ` ${cls}` : ''}">${escapeHtml(line) || ' '}</span>`;
  }).join('\n');
}

async function boot() {
  const id = eventIdFromPath();
  const el = $('#full-diff');
  if (!id) {
    el.textContent = 'Event not found. The link is missing an event ID.';
    return;
  }
  $('#back-to-event').href = `/event/${encodeURIComponent(id)}`;
  try {
    const events = await request('/api/events');
    const event = events.find((item) => item.id === id);
    if (event) {
      $('#diff-eyebrow').textContent = `${event.competitor_name} · Before / after diff`;
      $('#diff-title').textContent = event.summary;
      document.title = `Full diff · ${event.summary}`;
    }
  } catch (error) {
    showNotice(error.message);
  }
  try {
    const evidence = await request(`/api/events/${encodeURIComponent(id)}/diff`);
    renderDiff(el, evidence.diff);
  } catch (error) {
    el.textContent = error.message;
  }
}

boot();
