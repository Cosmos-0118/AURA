const state = { events: [], competitors: [], monitors: [], scanning: false, scanTimer: null, scanStartedAt: 0, scanTrigger: null };

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
  const notice = $('#notice');
  notice.hidden = false;
  notice.textContent = message;
  notice.dataset.tone = tone;
}

function clearNotice() {
  $('#notice').hidden = true;
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
  const startedAt = performance.now();
  state.scanStartedAt = startedAt;
  let phaseIndex = 0;
  overlay.hidden = false;
  overlay.setAttribute('aria-hidden', 'false');
  overlay.classList.remove('is-complete', 'is-error');
  document.body.classList.add('is-scanning');
  $('main').inert = true;
  $('main').setAttribute('aria-busy', 'true');
  $('#scan-title').textContent = targets.length > 1 ? 'Scanning watchlist' : `Scanning ${targets[0]}`;
  $('#scan-targets').innerHTML = targets.map((target) => `<span class="scan-target"><i></i>${escapeHtml(target)}</span>`).join('');
  $('#scan-phase').textContent = scanPhases[phaseIndex];
  $('#scan-elapsed').textContent = '00:00';
  $('#scan-status').textContent = 'The dashboard will update when the scan returns.';
  $('#scan-card').focus({ preventScroll: true });
  state.scanTimer = window.setInterval(() => {
    phaseIndex = (phaseIndex + 1) % scanPhases.length;
    $('#scan-phase').textContent = scanPhases[phaseIndex];
    $('#scan-elapsed').textContent = formatElapsed(performance.now() - startedAt);
  }, 1200);
}

async function finishScanOverlay(outcome = 'complete') {
  if (state.scanTimer) window.clearInterval(state.scanTimer);
  state.scanTimer = null;
  const overlay = $('#scan-overlay');
  overlay.classList.toggle('is-complete', outcome === 'complete');
  overlay.classList.toggle('is-error', outcome === 'error');
  $('#scan-phase').textContent = outcome === 'complete' ? 'Snapshot comparison complete' : 'Scan stopped with an error';
  $('#scan-status').textContent = outcome === 'complete' ? 'Fresh source state is ready in the workspace.' : 'Check the notice for the source error details.';
  const minimumVisibleTime = 1200;
  const remaining = Math.max(520, minimumVisibleTime - (performance.now() - state.scanStartedAt));
  await new Promise((resolve) => window.setTimeout(resolve, remaining));
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
    <article class="event-card" data-event-id="${escapeHtml(event.id)}" tabindex="0" role="button" aria-label="View details for ${escapeHtml(event.summary)}">
      <span class="event-rail event-rail-${escapeHtml(event.impact)}"></span>
      <div class="event-content">
        <div class="event-topline">
          <span class="event-competitor">${escapeHtml(event.competitor_name)}</span>
          <span class="badge badge-${escapeHtml(event.impact)}">${escapeHtml(event.impact)} impact</span>
          <span class="badge badge-brand">${escapeHtml(labels[event.brand_id] || event.brand_id)}</span>
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
    </article>
  `).join('');
  document.querySelectorAll('.event-card').forEach((card) => {
    card.addEventListener('click', () => openDetail(card.dataset.eventId));
    card.addEventListener('keydown', (event) => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); openDetail(card.dataset.eventId); } });
  });
}

function openDetail(id) {
  const event = state.events.find((item) => item.id === id);
  if (!event) return;
  $('#event-detail').innerHTML = `
    <div class="detail">
      <div class="event-topline"><span class="badge badge-${escapeHtml(event.impact)}">${escapeHtml(event.impact)} impact</span><span class="badge badge-brand">${escapeHtml(labels[event.brand_id] || event.brand_id)}</span></div>
      <h2>${escapeHtml(event.summary)}</h2>
      <div class="detail-grid">
        <div class="detail-box"><span>Competitor</span><strong>${escapeHtml(event.competitor_name)}</strong></div>
        <div class="detail-box"><span>Market</span><strong>${escapeHtml(labels[event.country] || event.country || 'Regional')}</strong></div>
        <div class="detail-box"><span>Change type</span><strong>${escapeHtml(labels[event.change_type] || event.change_type)}</strong></div>
        <div class="detail-box"><span>Analysis confidence</span><strong>${Math.round(event.confidence * 100)}%</strong></div>
      </div>
      ${event.previous_value || event.current_value ? `<div class="detail-grid"><div class="detail-box"><span>Before</span><strong>${escapeHtml(event.previous_value || 'Not found')}</strong></div><div class="detail-box"><span>After</span><strong>${escapeHtml(event.current_value || 'Not found')}</strong></div></div>` : ''}
      <div class="detail-section"><h3>Why it matters</h3><p>${escapeHtml(event.why_it_matters)}</p></div>
      <div class="detail-section"><h3>Recommended action</h3><p>${escapeHtml(event.recommended_action)}</p></div>
      <div class="detail-section"><h3>Captured evidence</h3><p class="evidence">${escapeHtml(event.evidence)}</p></div>
      <div class="detail-section"><h3>Detected</h3><p>${escapeHtml(formatDate(event.detected_at))} via ${escapeHtml(event.source)}</p></div>
    </div>
  `;
  $('#event-dialog').showModal();
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
  const [summary, competitors, health, monitors] = await Promise.all([
    request('/api/summary'), request('/api/competitors'), request('/api/source-health'), request('/api/monitors'),
  ]);
  state.competitors = competitors;
  state.monitors = monitors;
  renderSummary(summary);
  $('#watchlist').innerHTML = competitors.map((competitor) => {
    const monitor = monitors.find((item) => item.competitor_id === competitor.id) || {};
    const source = monitor.source ? `${monitor.source} · ${monitor.versions || 0} version${monitor.versions === 1 ? '' : 's'}` : 'Not checked yet';
    const link = monitor.source_url ? `<a class="watch-link" href="${escapeHtml(monitor.source_url)}" target="_blank" rel="noreferrer">Open source</a>` : '';
    return `
    <div class="watch-row"><div><div class="watch-name">${escapeHtml(competitor.name)}</div><div class="watch-detail">${escapeHtml(labels[competitor.brand_id] || competitor.brand_id)} · ${escapeHtml(competitor.priority)} priority</div><div class="watch-detail">${escapeHtml(source)} · checked ${escapeHtml(formatDate(monitor.last_checked))}</div>${link}</div><button class="watch-action" data-scan-id="${escapeHtml(competitor.id)}">Scan</button></div>
    `;
  }).join('') || '<div class="empty-state">Add competitors to config/competitors.json.</div>';
  document.querySelectorAll('[data-scan-id]').forEach((button) => button.addEventListener('click', () => scan(button.dataset.scanId, button)));
  $('#source-health').innerHTML = health.map((item) => `<div class="health-row"><div><div class="health-name">${escapeHtml(item.source)}</div><div class="health-detail">${escapeHtml(item.detail)}</div></div><span class="health-status health-${escapeHtml(item.status)}">${escapeHtml(item.status.replace('_', ' '))}</span></div>`).join('');
}

async function scan(id, button) {
  if (state.scanning) return;
  if (button) { button.disabled = true; button.textContent = 'Scanning…'; }
  clearNotice();
  const competitor = state.competitors.find((item) => item.id === id);
  startScanOverlay([competitor?.name || 'Selected watch']);
  let outcome = 'complete';
  try {
    const result = await request(`/api/competitors/${encodeURIComponent(id)}/scan`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' });
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
  startScanOverlay(state.competitors.map((item) => item.name));
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

async function boot() {
  try {
    await request('/api/health');
    $('#api-status').textContent = 'Service ready';
    $('#api-status').className = 'status-pill status-ready';
    await refreshDashboard();
    await refreshEvents();
  } catch (error) {
    $('#api-status').textContent = 'Service unavailable';
    $('#api-status').className = 'status-pill status-error';
    showNotice(error.message);
  }
}

$('#scan-all').addEventListener('click', scanAll);
$('#filters').addEventListener('input', () => refreshEvents().catch((error) => showNotice(error.message)));
$('#clear-filters').addEventListener('click', () => { $('#filters').reset(); refreshEvents().catch((error) => showNotice(error.message)); });
$('#close-dialog').addEventListener('click', () => $('#event-dialog').close());
$('#event-dialog').addEventListener('click', (event) => { if (event.target === $('#event-dialog')) $('#event-dialog').close(); });
boot();
