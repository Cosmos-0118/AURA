const state = { competitors: [], monitors: [], watches: [], scanning: false, scanStartedAt: 0, scanTrigger: null };

const $ = (selector) => document.querySelector(selector);

const labels = {
  jade: 'Jade',
  doctorshield: 'DoctorShield',
  jaguar: 'Jaguar Transit',
  DIRECT_COMPETITOR: 'Direct competitor',
  INDIRECT_COMPETITOR: 'Indirect competitor',
  PARTNER: 'Partner / overlap',
  UNDERWRITER: 'Underwriter',
  DISTRIBUTOR: 'Distributor',
  SECURE_LOGISTICS_COMPETITOR: 'Secure logistics competitor',
  ADJACENT: 'Adjacent market',
};

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

function formatDate(value) {
  if (!value) return 'Never';
  return new Intl.DateTimeFormat('en-SG', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }).format(new Date(value));
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
  const [competitors, monitors, watches] = await Promise.all([
    request('/api/competitors'), request('/api/monitors'), request('/api/watches'),
  ]);
  state.competitors = competitors;
  state.monitors = monitors;
  state.watches = watches;
  $('#watchlist').innerHTML = competitors.map((competitor) => {
    const monitor = monitors.find((item) => item.competitor_id === competitor.id) || {};
    const watchRows = watches.filter((item) => item.competitor_id === competitor.id);
    const checked = watchRows.filter((item) => item.last_checked).length;
    const status = competitor.monitor
      ? `${watchRows.length} URL${watchRows.length === 1 ? '' : 's'} · ${checked} checked · last ${escapeHtml(formatDate(monitor.last_checked))}`
      : 'Context only — not scanned';
    const link = monitor.source_url ? `<a class="watch-link" href="${escapeHtml(monitor.source_url)}" target="_blank" rel="noreferrer">Open source ↗</a>` : '';
    const relationship = labels[competitor.relationship] || competitor.relationship;
    const urls = competitor.monitor && watchRows.length
      ? `<div class="watch-urls">${watchRows.map((item) => `
        <div class="watch-url">
          <div class="watch-url-info">
            <a class="watch-url-link" href="${escapeHtml(item.url)}" target="_blank" rel="noreferrer">${escapeHtml(item.id)}</a>
            <span class="watch-url-meta">${escapeHtml(item.kind)} · every ${item.interval_hours}h · ${escapeHtml(item.priority)} priority</span>
          </div>
          <button class="button button-quiet watch-scan" data-scan-watch-id="${escapeHtml(item.id)}">Scan</button>
        </div>`).join('')}</div>`
      : '';
    return `
    <article class="watch-card">
      <div class="watch-card-head">
        <div>
          <div class="watch-name">${escapeHtml(competitor.name)}</div>
          <div class="watch-badges"><span class="badge badge-brand">${escapeHtml(labels[competitor.brand_id] || competitor.brand_id)}</span><span class="badge badge-relationship">${escapeHtml(relationship)}</span></div>
        </div>
        ${link}
      </div>
      <p class="watch-sub">${escapeHtml(competitor.product_category)} · ${escapeHtml(competitor.market || competitor.countries.join(', '))}</p>
      <p class="watch-status">${status}</p>
      ${urls}
    </article>
    `;
  }).join('') || '<div class="empty-state">Add competitors to config/competitors.json.</div>';
  document.querySelectorAll('[data-scan-watch-id]').forEach((button) => button.addEventListener('click', () => scanWatch(button.dataset.scanWatchId, button)));
  $('#watchlist-count').textContent = `${competitors.length} tracked`;
}

async function scanWatch(id, button) {
  if (state.scanning) return;
  if (button) { button.disabled = true; button.textContent = 'Scanning…'; }
  clearNotice();
  const watch = state.watches.find((item) => item.id === id);
  startScanOverlay([watch?.id || 'Selected watch']);
  try {
    const result = await request(`/api/watches/${encodeURIComponent(id)}/scan`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' });
    if (result.status === 'error') {
      showNotice(`Scan failed: ${result.error}`);
    } else if (result.status === 'baseline') {
      showNotice('Baseline captured. Future scans will be compared against this source.', 'info');
    } else {
      showNotice(result.changed ? 'Meaningful change detected and added to the feed.' : 'Scan complete. No meaningful change detected.', 'info');
    }
    await refresh();
  } catch (error) {
    showNotice(error.message);
  } finally {
    if (button) { button.disabled = false; button.textContent = 'Scan'; }
    await finishScanOverlay();
  }
}

async function scanAll() {
  if (state.scanning) return;
  const button = $('#scan-all');
  button.disabled = true;
  button.textContent = 'Scanning…';
  clearNotice();
  startScanOverlay(state.competitors.filter((item) => item.monitor).map((item) => item.name));
  try {
    await request('/api/scan-all', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' });
    await refresh();
    showNotice('Watchlist scan complete.', 'info');
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
