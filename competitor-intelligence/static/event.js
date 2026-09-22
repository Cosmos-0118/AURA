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

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>'"]/g, (character) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[character]));
}

function formatDate(value) {
  if (!value) return 'Never';
  return new Intl.DateTimeFormat('en-SG', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }).format(new Date(value));
}

function eventIdFromPath() {
  const parts = window.location.pathname.split('/').filter(Boolean);
  return parts.length >= 2 ? decodeURIComponent(parts.slice(1).join('/')) : '';
}

async function analyzeEvent(id) {
  const button = $('#analyze-event');
  if (!button) return;
  button.disabled = true;
  button.textContent = 'Analyzing…';
  $('#ai-analysis').textContent = 'Gemini is reviewing the captured before/after evidence.';
  try {
    const result = await request(`/api/events/${encodeURIComponent(id)}/analyze`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' });
    $('#ai-analysis').innerHTML = `<h3>${escapeHtml(result.summary)}</h3><p>${escapeHtml(result.why_it_matters)}</p><h4>Recommended action</h4><p>${escapeHtml(result.recommended_action)}</p><small>${escapeHtml(result.confidence_reason)}</small>`;
  } catch (error) {
    $('#ai-analysis').textContent = error.message;
  } finally {
    button.disabled = false;
    button.textContent = 'Analyze with AI';
  }
}

function renderDiff(text) {
  const el = $('#event-diff');
  if (!el) return;
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
  if (!id) {
    $('#event-detail').innerHTML = '<div class="empty-state"><strong>Event not found</strong>The link is missing an event ID.</div>';
    return;
  }
  let events;
  try {
    events = await request('/api/events');
  } catch (error) {
    $('#event-detail').innerHTML = '<div class="empty-state"><strong>Could not load event</strong>Check your connection and try again.</div>';
    showNotice(error.message);
    return;
  }
  const event = events.find((item) => item.id === id);
  if (!event) {
    $('#event-detail').innerHTML = '<div class="empty-state"><strong>Event not found</strong>It may have been removed or the link is incorrect.</div>';
    return;
  }
  document.title = `${event.summary} · Competitor Intelligence`;
  $('#event-detail').innerHTML = `
    <p class="eyebrow">${escapeHtml(event.competitor_name)} · ${escapeHtml(labels[event.country] || event.country || 'Regional')}</p>
    <h1 class="event-title">${escapeHtml(event.summary)}</h1>
    <div class="event-topline">
      <span class="badge badge-${escapeHtml(event.impact)}">${escapeHtml(event.impact)} impact</span>
      <span class="badge badge-brand">${escapeHtml(labels[event.brand_id] || event.brand_id)}</span>
      ${event.relationship ? `<span class="badge badge-relationship">${escapeHtml(labels[event.relationship] || event.relationship)}</span>` : ''}
      <span class="muted">${escapeHtml(formatDate(event.detected_at))} via ${escapeHtml(event.source)}</span>
    </div>
    <section class="panel">
      <div class="detail-grid">
        <div class="detail-box"><span>Competitor</span><strong>${escapeHtml(event.competitor_name)}</strong></div>
        <div class="detail-box"><span>Market</span><strong>${escapeHtml(labels[event.country] || event.country || 'Regional')}</strong></div>
        <div class="detail-box"><span>Change type</span><strong>${escapeHtml(labels[event.change_type] || event.change_type)}</strong></div>
        <div class="detail-box"><span>Analysis confidence</span><strong>${Math.round(event.confidence * 100)}%</strong></div>
        ${event.product_category ? `<div class="detail-box"><span>Product category</span><strong>${escapeHtml(event.product_category)}</strong></div>` : ''}
        <div class="detail-box"><span>Source</span><strong>${escapeHtml(event.source)}</strong></div>
      </div>
      ${event.previous_value || event.current_value ? `<div class="detail-grid"><div class="detail-box"><span>Before</span><strong>${escapeHtml(event.previous_value || 'Not found')}</strong></div><div class="detail-box"><span>After</span><strong>${escapeHtml(event.current_value || 'Not found')}</strong></div></div>` : ''}
      <div class="detail-section"><h3>Why it matters</h3><p>${escapeHtml(event.why_it_matters)}</p></div>
      <div class="detail-section"><h3>Recommended action</h3><p>${escapeHtml(event.recommended_action)}</p></div>
      <div class="detail-section"><h3>Captured evidence</h3><p class="evidence">${escapeHtml(event.evidence)}</p></div>
      <div class="detail-section"><h3>Before / after diff</h3><pre id="event-diff" class="diff-evidence">Loading captured diff…</pre></div>
      <div class="detail-section"><div class="button-row"><button id="analyze-event" class="button button-primary">Analyze with AI</button><a class="button button-quiet" href="/event/${encodeURIComponent(id)}/diff">View full diff</a></div><div id="ai-analysis" role="status" aria-live="polite"></div></div>
    </section>
  `;
  $('#analyze-event').addEventListener('click', () => analyzeEvent(id));
  try {
    const evidence = await request(`/api/events/${encodeURIComponent(id)}/diff`);
    renderDiff(evidence.diff);
  } catch (error) {
    if ($('#event-diff')) $('#event-diff').textContent = error.message;
  }
}

boot();
