const state = { events: [], competitors: [], monitors: [], watches: [], scanning: false, scanTimer: null, scanStartedAt: 0, scanTrigger: null };

const $ = (selector) => document.querySelector(selector);

const labels = {
  jade: 'Jade',
  doctorshield: 'DoctorShield',
  jaguar: 'Jaguar Transit',
  SG: 'Singapore',
  MY: 'Malaysia',
  HK: 'Hong Kong',
  ID: 'Indonesia',
  TH: 'Thailand',
  price_change: 'Price change',
  new_product: 'New product',
  new_market: 'New market',
  coverage_change: 'Coverage change',
  partnership: 'Partnership',
  positioning_change: 'Positioning',
  promotion: 'Promotion',
  article: 'Article',
  social_post: 'Social post',
  article: 'New article',
  DIRECT_COMPETITOR: 'Direct competitor',
  INDIRECT_COMPETITOR: 'Indirect competitor',
  PARTNER: 'Partner / overlap',
  UNDERWRITER: 'Underwriter',
  DISTRIBUTOR: 'Distributor',
  SECURE_LOGISTICS_COMPETITOR: 'Secure logistics competitor',
  ADJACENT: 'Adjacent market',
};

const scanPhases = [
  'Opening source watches',
  'Reading current pages',
  'Normalizing source text',
  'Comparing stored snapshots',
];

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

function formatElapsed(milliseconds) {
  const seconds = Math.floor(milliseconds / 1000);
  return `${String(Math.floor(seconds / 60)).padStart(2, '0')}:${String(seconds % 60).padStart(2, '0')}`;
}

function startScanOverlay(targets) {
  const overlay = $('#scan-overlay');
  const activeElement = document.activeElement;
  state.scanTrigger = activeElement instanceof HTMLElement ? activeElement : null;
  state.scanning = true;
  state.scanStartedAt = performance.now();
  overlay.hidden = false;
  overlay.setAttribute('aria-hidden', 'false');
  document.body.classList.add('is-scanning');
  $('main').inert = true;
  $('main').setAttribute('aria-busy', 'true');
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
  $('main').removeAttribute('aria-busy');
  state.scanning = false;
  if (state.scanTrigger?.isConnected) state.scanTrigger.focus({ preventScroll: true });
  state.scanTrigger = null;
}

function formatDate(value) {
  if (!value) return 'Never';
  return new Intl.DateTimeFormat('en-SG', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }).format(new Date(value));
}

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>'"]/g, (character) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[character]));
}

function renderSummary(summary) {
  $('#summary-high').textContent = summary.high;
  $('#summary-total').textContent = summary.total;
  $('#summary-competitors').textContent = summary.competitors;
}

function renderEvents(events) {
  $('#event-count').textContent = `${events.length} event${events.length === 1 ? '' : 's'}`;
  if (!events.length) {
    const checked = state.monitors.filter((item) => item.last_checked).length;
    $('#events').innerHTML = checked
      ? `<div class="empty-state"><strong>No meaningful changes detected</strong>${checked} source${checked === 1 ? '' : 's'} have baselines. The latest scans are unchanged; new evidence will appear here when a monitored product page moves.</div>`
      : '<div class="empty-state"><strong>No baselines captured yet</strong>Run a watchlist scan or start the collector worker to capture the first real source snapshot.</div>';
    return;
  }
  $('#events').innerHTML = events.map((event) => `
    <a class="event-card" href="/event/${encodeURIComponent(event.id)}" aria-label="View details for ${escapeHtml(event.summary)}">
      <span class="event-rail event-rail-${escapeHtml(event.impact)}"></span>
      <div class="event-content">
        <div class="event-topline">
          <span class="event-competitor">${escapeHtml(event.competitor_name)}</span>
          <span class="badge badge-${escapeHtml(event.impact)}">${escapeHtml(event.impact)} impact</span>
          <span class="badge badge-brand">${escapeHtml(labels[event.brand_id] || event.brand_id)}</span>
          ${event.relationship ? `<span class="badge badge-relationship">${escapeHtml(labels[event.relationship] || event.relationship)}</span>` : ''}
        </div>
        <p class="event-summary">${escapeHtml(event.summary)}</p>
        <div class="event-meta">
          <span>${escapeHtml(labels[event.change_type] || event.change_type)}</span>
          <span>${escapeHtml(labels[event.country] || event.country || 'Regional')}</span>
          <span>${escapeHtml(event.source)}</span>
          <span>${escapeHtml(formatDate(event.detected_at))}</span>
        </div>
      </div>
      <div class="event-value">
        ${event.current_value ? `<small>Detected value</small><strong>${escapeHtml(event.current_value)}</strong>` : '<small>Confidence</small><strong>' + Math.round(event.confidence * 100) + '%</strong>'}
      </div>
    </a>
  `).join('');
}

function filterQuery() {
  const form = new FormData($('#filters'));
  return new URLSearchParams([...form.entries()].filter(([, value]) => value)).toString();
}

async function refreshEvents() {
  const query = filterQuery();
  state.events = await request(`/api/events${query ? `?${query}` : ''}`);
  renderEvents(state.events);
}

async function refreshDashboard() {
  const [summary, competitors, health, monitors, watches] = await Promise.all([
    request('/api/summary'), request('/api/competitors'), request('/api/source-health'), request('/api/monitors'), request('/api/watches'),
  ]);
  state.competitors = competitors;
  state.monitors = monitors;
  state.watches = watches;
  if ($('#summary-watches')) $('#summary-watches').textContent = `${watches.length} URLs`;
  renderSummary(summary);
  const watchlistEl = $('#watchlist');
  if (watchlistEl) {
    watchlistEl.innerHTML = competitors.map((competitor) => {
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
  }
  const healthEl = $('#source-health');
  if (healthEl) healthEl.innerHTML = health.map((item) => `<div class="health-row"><div><div class="health-name">${escapeHtml(item.source)}</div><div class="health-detail">${escapeHtml(item.detail)}</div></div><span class="health-status health-${escapeHtml(item.status)}">${escapeHtml(item.status.replace('_', ' '))}</span></div>`).join('');
}

async function scanWatch(id, button) {
  if (state.scanning) return;
  if (button) { button.disabled = true; button.textContent = 'Scanning…'; }
  clearNotice();
  const watch = state.watches.find((item) => item.id === id);
  startScanOverlay([watch?.id || 'Selected watch']);
  let outcome = 'complete';
  try {
    const result = await request(`/api/watches/${encodeURIComponent(id)}/scan`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' });
    if (result.status === 'error') {
      outcome = 'error';
      showNotice(`Scan failed: ${result.error}`);
    } else if (result.status === 'baseline') {
      showNotice('Baseline captured. Future scans will be compared against this source.', 'info');
    } else {
      showNotice(result.changed ? 'Meaningful change detected and added to the feed.' : 'Scan complete. No meaningful change detected.', 'info');
    }
    await Promise.all([refreshDashboard(), refreshEvents()]);
  } catch (error) {
    outcome = 'error';
    showNotice(error.message);
  } finally {
    if (button) { button.disabled = false; button.textContent = 'Scan'; }
    await finishScanOverlay(outcome);
  }
}

async function scanAll() {
  if (state.scanning) return;
  const button = $('#scan-all');
  button.disabled = true;
  button.textContent = 'Scanning…';
  clearNotice();
  const activeCompetitors = state.competitors.filter((item) => item.monitor);
  startScanOverlay(activeCompetitors.map((item) => item.name));
  let outcome = 'complete';
  try {
    const results = await request('/api/scan-all', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' });
    const baseline = results.filter((item) => item.status === 'baseline').length;
    const changed = results.filter((item) => item.changed || item.status === 'changed').length;
    const unchanged = results.filter((item) => item.status === 'unchanged').length;
    const failed = results.filter((item) => item.status === 'error').length;
    outcome = failed ? 'error' : 'complete';
    const details = [
      baseline ? `${baseline} baseline${baseline === 1 ? '' : 's'}` : '',
      changed ? `${changed} changed` : '',
      unchanged ? `${unchanged} unchanged` : '',
      failed ? `${failed} failed` : '',
    ].filter(Boolean).join(' · ');
    showNotice(`${results.length} watchlist scan${results.length === 1 ? '' : 's'} complete · ${details}.`, failed ? 'warning' : 'info');
    await Promise.all([refreshDashboard(), refreshEvents()]);
  } catch (error) {
    outcome = 'error';
    showNotice(error.message);
  } finally {
    button.disabled = false;
    button.textContent = 'Scan watchlist';
    await finishScanOverlay(outcome);
  }
}

async function syncChanges() {
  const button = $('#sync-changes');
  button.disabled = true;
  button.textContent = 'Syncing…';
  clearNotice();
  try {
    const result = await request('/api/sync-changedetection', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' });
    await Promise.all([refreshDashboard(), refreshEvents()]);
    showNotice(`Imported ${result.imported} snapshot${result.imported === 1 ? '' : 's'} from changedetection.${result.errors.length ? ` ${result.errors.length} watch errors: ${result.errors.slice(0, 2).join('; ')}` : ''}`, result.errors.length ? 'warning' : 'info');
  } catch (error) {
    showNotice(error.message);
  } finally {
    button.disabled = false;
    button.textContent = 'Sync 5001 changes';
  }
}

async function boot() {
  try {
    await request('/api/health');
    await refreshDashboard();
    await refreshEvents();
  } catch (error) {
    showNotice(error.message);
  }
}

$('#scan-all').addEventListener('click', scanAll);
$('#sync-changes').addEventListener('click', syncChanges);
$('#filters').addEventListener('input', () => refreshEvents().catch((error) => showNotice(error.message)));
$('#clear-filters').addEventListener('click', () => { $('#filters').reset(); refreshEvents().catch((error) => showNotice(error.message)); });
boot();
