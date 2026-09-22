const state = { scanning: false, scanStartedAt: 0, scanTrigger: null, competitors: [] };

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

function clearNotice() {
  $('#toast-container')?.replaceChildren();
}

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>'"]/g, (character) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[character]));
}

function startScanOverlay(targets) {
  const overlay = $('#scan-overlay');
  state.scanning = true;
  state.scanStartedAt = performance.now();
  state.scanTrigger = document.activeElement instanceof HTMLElement ? document.activeElement : null;
  overlay.hidden = false;
  overlay.setAttribute('aria-hidden', 'false');
  document.body.classList.add('is-scanning');
  $('main').inert = true;
  $('#scan-title').textContent = targets.length > 1 ? `Scanning ${targets.length} sources` : `Scanning ${targets[0] || 'source'}`;
  $('#scan-card').focus({ preventScroll: true });
}

async function finishScanOverlay() {
  const overlay = $('#scan-overlay');
  const elapsed = performance.now() - state.scanStartedAt;
  if (elapsed < 400) await new Promise((resolve) => window.setTimeout(resolve, 400 - elapsed));
  overlay.hidden = true;
  overlay.setAttribute('aria-hidden', 'true');
  document.body.classList.remove('is-scanning');
  $('main').inert = false;
  state.scanning = false;
  if (state.scanTrigger?.isConnected) state.scanTrigger.focus({ preventScroll: true });
  state.scanTrigger = null;
}

async function refresh() {
  const health = await request('/api/source-health');
  $('#source-health').innerHTML = health.map((item) => `<div class="health-row"><div><div class="health-name">${escapeHtml(item.source)}</div><div class="health-detail">${escapeHtml(item.detail)}</div></div><span class="health-status health-${escapeHtml(item.status)}">${escapeHtml(item.status.replace('_', ' '))}</span></div>`).join('') || '<div class="empty-state">No sources configured.</div>';
  $('#source-count').textContent = `${health.length} source${health.length === 1 ? '' : 's'}`;
}

async function scanAll() {
  if (state.scanning) return;
  const button = $('#scan-all');
  button.disabled = true;
  button.textContent = 'Scanning…';
  clearNotice();
  startScanOverlay(['watchlist']);
  try {
    await request('/api/scan-all', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' });
    await refresh();
    showNotice('Scan complete. Source health refreshed.', 'info');
  } catch (error) {
    showNotice(error.message);
  } finally {
    button.disabled = false;
    button.textContent = 'Scan watchlist';
    await finishScanOverlay();
  }
}

async function syncChanges() {
  const button = $('#sync-changes');
  button.disabled = true;
  button.textContent = 'Syncing…';
  clearNotice();
  try {
    const result = await request('/api/sync-changedetection', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' });
    await refresh();
    showNotice(`Imported ${result.imported} snapshot${result.imported === 1 ? '' : 's'} from changedetection.`, result.errors.length ? 'warning' : 'info');
  } catch (error) {
    showNotice(error.message);
  } finally {
    button.disabled = false;
    button.textContent = 'Sync 5001 changes';
  }
}

$('#scan-all').addEventListener('click', scanAll);
$('#sync-changes').addEventListener('click', syncChanges);
refresh().catch((error) => showNotice(error.message));
