const state = { events: [], competitors: [] };

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

function formatDate(value) {
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
    $('#events').innerHTML = '<div class="empty-state"><strong>No meaningful changes detected</strong>Run a watchlist scan or adjust the filters. Baseline captures do not create noise events.</div>';
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
  const [summary, competitors, health] = await Promise.all([
    request('/api/summary'), request('/api/competitors'), request('/api/source-health'),
  ]);
  state.competitors = competitors;
  renderSummary(summary);
  $('#watchlist').innerHTML = competitors.map((competitor) => `
    <div class="watch-row"><div><div class="watch-name">${escapeHtml(competitor.name)}</div><div class="watch-detail">${escapeHtml(labels[competitor.brand_id] || competitor.brand_id)} · ${escapeHtml(competitor.priority)} priority</div></div><button class="watch-action" data-scan-id="${escapeHtml(competitor.id)}">Scan</button></div>
  `).join('') || '<div class="empty-state">Add competitors to config/competitors.json.</div>';
  document.querySelectorAll('[data-scan-id]').forEach((button) => button.addEventListener('click', () => scan(button.dataset.scanId, button)));
  $('#source-health').innerHTML = health.map((item) => `<div class="health-row"><div><div class="health-name">${escapeHtml(item.source)}</div><div class="health-detail">${escapeHtml(item.detail)}</div></div><span class="health-status health-${escapeHtml(item.status)}">${escapeHtml(item.status.replace('_', ' '))}</span></div>`).join('');
}

async function scan(id, button) {
  if (button) { button.disabled = true; button.textContent = 'Scanning…'; }
  clearNotice();
  try {
    const result = await request(`/api/competitors/${encodeURIComponent(id)}/scan`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' });
    if (result.status === 'error') showNotice(`Scan failed: ${result.error}`);
    else showNotice(result.changed ? 'Meaningful change detected and added to the feed.' : 'Scan complete. No meaningful change detected.', 'info');
    await Promise.all([refreshDashboard(), refreshEvents()]);
  } catch (error) { showNotice(error.message); }
  finally { if (button) { button.disabled = false; button.textContent = 'Scan'; } }
}

async function scanAll() {
  const button = $('#scan-all');
  button.disabled = true;
  button.textContent = 'Scanning…';
  clearNotice();
  try {
    const results = await request('/api/scan-all', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' });
    const changed = results.filter((item) => item.changed).length;
    const failed = results.filter((item) => item.status === 'error').length;
    showNotice(`${results.length} watchlist scans complete · ${changed} meaningful change${changed === 1 ? '' : 's'}${failed ? ` · ${failed} failed` : ''}.`, failed ? 'warning' : 'info');
    await Promise.all([refreshDashboard(), refreshEvents()]);
  } catch (error) { showNotice(error.message); }
  finally { button.disabled = false; button.textContent = 'Scan watchlist'; }
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
