'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { Icons } from '@/components/icons';
import {
  analyzeCompetitorEvent,
  getCompetitorDashboard,
  getCompetitorEventDiff,
  scanAllCompetitors,
  scanCompetitorWatch,
  syncCompetitorChangedetection
} from '@/lib/api/client';
import type {
  CompetitorDashboard,
  CompetitorEvent,
  CompetitorRecord,
  CompetitorWatch
} from '@/lib/api/types';
import styles from './page.module.css';

type View = 'feed' | 'sources' | 'watchlist';
type FilterValue = '' | string;

const labels: Record<string, string> = {
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
  article: 'New article',
  social_post: 'Social post',
  DIRECT_COMPETITOR: 'Direct competitor',
  INDIRECT_COMPETITOR: 'Indirect competitor',
  PARTNER: 'Partner / overlap',
  UNDERWRITER: 'Underwriter',
  DISTRIBUTOR: 'Distributor',
  SECURE_LOGISTICS_COMPETITOR: 'Secure logistics competitor',
  ADJACENT: 'Adjacent market'
};

const buttonBase =
  'inline-flex h-9 items-center justify-center gap-2 rounded-[9px] border px-3 text-xs font-semibold transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-black dark:focus-visible:ring-white disabled:cursor-wait disabled:opacity-55';
const quietButton = `${buttonBase} border-[#e6e6e6] bg-transparent text-[#404040] hover:bg-[#f5f5f5] dark:border-[#424242] dark:text-[#d4d4d4] dark:hover:bg-[#242424]`;
const primaryButton = `${buttonBase} border-[#09090b] bg-[#09090b] text-white shadow-sm hover:opacity-85 dark:border-white dark:bg-white dark:text-black`;
const inputClass =
  'h-[38px] w-full rounded-lg border border-[#e6e6e6] bg-white px-3 text-xs text-[#404040] outline-none transition placeholder:text-[#a3a3a3] focus:border-[#737373] focus:ring-2 focus:ring-black/10 dark:border-[#424242] dark:bg-[#171717] dark:text-[#e5e5e5] dark:placeholder:text-[#737373] dark:focus:border-[#a3a3a3] dark:focus:ring-white/10';
const panelClass =
  'rounded-[13px] border border-[#e6e6e6] bg-white shadow-sm dark:border-[#424242] dark:bg-[#171717]';

const selectOptions = {
  brand: [
    ['', 'All brands'],
    ['jade', 'Jade'],
    ['doctorshield', 'DoctorShield'],
    ['jaguar', 'Jaguar Transit']
  ],
  impact: [
    ['', 'All impact'],
    ['high', 'High'],
    ['medium', 'Medium'],
    ['low', 'Low']
  ],
  country: [
    ['', 'All markets'],
    ['SG', 'Singapore'],
    ['MY', 'Malaysia'],
    ['HK', 'Hong Kong'],
    ['ID', 'Indonesia'],
    ['TH', 'Thailand']
  ],
  changeType: [
    ['', 'All change types'],
    ['price_change', 'Price change'],
    ['new_product', 'New product'],
    ['new_market', 'New market'],
    ['coverage_change', 'Coverage change'],
    ['partnership', 'Partnership'],
    ['positioning_change', 'Positioning'],
    ['social_post', 'Social post']
  ],
  source: [
    ['', 'All sources'],
    ['website', 'Website'],
    ['pricing', 'Pricing'],
    ['changedetection', 'Changedetection'],
    ['rsshub', 'RSSHub'],
    ['news', 'News']
  ]
} as const;

function label(value: string | null | undefined): string {
  return value ? labels[value] || value.replaceAll('_', ' ') : 'Regional';
}

function formatDate(value: string | null): string {
  if (!value) return 'Never';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat('en-SG', {
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit'
  }).format(date);
}

function competitorName(event: CompetitorEvent, competitors: CompetitorRecord[]): string {
  return event.competitor_name || competitors.find((item) => item.id === event.competitor_id)?.name || 'Unknown competitor';
}

function impactClasses(impact: string): { badge: string; rail: string } {
  if (impact === 'high') {
    return {
      badge: 'border-red-500/40 bg-red-500/10 text-red-600 dark:text-red-300',
      rail: 'bg-red-500'
    };
  }
  if (impact === 'medium') {
    return {
      badge: 'border-amber-500/40 bg-amber-500/10 text-amber-600 dark:text-amber-300',
      rail: 'bg-amber-500'
    };
  }
  return {
    badge: 'border-blue-500/40 bg-blue-500/10 text-blue-600 dark:text-blue-300',
    rail: 'bg-blue-500'
  };
}

function Badge({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return (
    <span
      className={`inline-flex max-w-full w-fit items-center rounded-full border px-2 py-1 text-[10px] leading-tight ${styles.wrapAnywhere} ${className || 'border-[#e6e6e6] bg-[#f7f7f7] text-[#404040] dark:border-[#424242] dark:bg-[#242424] dark:text-[#d4d4d4]'}`}
    >
      {children}
    </span>
  );
}

function SelectFilter({
  value,
  options,
  onChange,
  label: ariaLabel
}: {
  value: FilterValue;
  options: readonly (readonly [string, string])[];
  onChange: (value: string) => void;
  label: string;
}) {
  return (
    <label className='min-w-0 flex-1 basis-[112px]'>
      <span className='sr-only'>{ariaLabel}</span>
      <select aria-label={ariaLabel} className={inputClass} value={value} onChange={(event) => onChange(event.target.value)}>
        {options.map(([optionValue, optionLabel]) => (
          <option key={optionValue} value={optionValue}>
            {optionLabel}
          </option>
        ))}
      </select>
    </label>
  );
}

export default function CompetitorIntelligencePage() {
  const [view, setView] = useState<View>('feed');
  const [dashboard, setDashboard] = useState<CompetitorDashboard | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [busyAction, setBusyAction] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [selectedEvent, setSelectedEvent] = useState<CompetitorEvent | null>(null);
  const [eventDiff, setEventDiff] = useState<string | null>(null);
  const [analysis, setAnalysis] = useState<Record<string, { summary: string; why_it_matters: string; recommended_action: string; confidence_reason: string }>>({});
  const [search, setSearch] = useState('');
  const [watchSearch, setWatchSearch] = useState('');
  const [brand, setBrand] = useState<FilterValue>('');
  const [impact, setImpact] = useState<FilterValue>('');
  const [country, setCountry] = useState<FilterValue>('');
  const [changeType, setChangeType] = useState<FilterValue>('');
  const [source, setSource] = useState<FilterValue>('');

  const loadDashboard = useCallback(async () => {
    setIsLoading(true);
    try {
      setDashboard(await getCompetitorDashboard());
      setNotice(null);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : 'Could not load competitor intelligence.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadDashboard();
  }, [loadDashboard]);

  useEffect(() => {
    if (!selectedEvent) {
      setEventDiff(null);
      return;
    }
    setEventDiff(null);
    void getCompetitorEventDiff(selectedEvent.id)
      .then((result) => setEventDiff(result.diff))
      .catch(() => setEventDiff('No line changes in the captured evidence.'));
  }, [selectedEvent]);

  const filteredEvents = useMemo(() => {
    const query = search.trim().toLowerCase();
    return (dashboard?.events || []).filter((event) => {
      const eventText = [
        event.summary,
        event.evidence,
        event.current_value,
        event.previous_value,
        competitorName(event, dashboard?.competitors || [])
      ]
        .filter(Boolean)
        .join(' ')
        .toLowerCase();
      return (
        (!query || eventText.includes(query)) &&
        (!brand || event.brand_id === brand) &&
        (!impact || event.impact === impact) &&
        (!country || event.country === country) &&
        (!changeType || event.change_type === changeType) &&
        (!source || event.source === source)
      );
    });
  }, [brand, changeType, country, dashboard, impact, search, source]);

  const filteredCompetitors = useMemo(() => {
    const query = watchSearch.trim().toLowerCase();
    return (dashboard?.competitors || []).filter((competitor) => {
      const text = [competitor.name, competitor.product_category, competitor.market, competitor.relationship]
        .join(' ')
        .toLowerCase();
      return (!brand || competitor.brand_id === brand) && (!query || text.includes(query));
    });
  }, [brand, dashboard, watchSearch]);

  const showNotice = (message: string) => {
    setNotice(message);
    window.setTimeout(() => setNotice((current) => (current === message ? null : current)), 6000);
  };

  const runScanAll = async () => {
    if (busyAction) return;
    setBusyAction('scan-all');
    setNotice(null);
    try {
      const results = await scanAllCompetitors();
      const baseline = results.filter((item) => item.status === 'baseline').length;
      const changed = results.filter((item) => item.changed || item.status === 'changed').length;
      const unchanged = results.filter((item) => item.status === 'unchanged').length;
      const failed = results.filter((item) => item.status === 'error').length;
      const details = [
        baseline ? `${baseline} baseline${baseline === 1 ? '' : 's'}` : '',
        changed ? `${changed} changed` : '',
        unchanged ? `${unchanged} unchanged` : '',
        failed ? `${failed} failed` : ''
      ]
        .filter(Boolean)
        .join(' · ');
      await loadDashboard();
      showNotice(`${results.length} watchlist scan${results.length === 1 ? '' : 's'} complete${details ? ` · ${details}` : ''}.`);
    } catch (error) {
      showNotice(error instanceof Error ? error.message : 'The watchlist scan failed.');
    } finally {
      setBusyAction(null);
    }
  };

  const runWatchScan = async (watch: CompetitorWatch) => {
    if (busyAction) return;
    setBusyAction(`scan-watch:${watch.id}`);
    setNotice(null);
    try {
      const result = await scanCompetitorWatch(watch.id);
      await loadDashboard();
      showNotice(
        result.status === 'baseline'
          ? 'Baseline captured. Future scans will be compared against this source.'
          : result.changed
            ? 'Meaningful change detected and added to the feed.'
            : result.status === 'error'
              ? result.error || 'The source scan failed.'
              : 'Scan complete. No meaningful change detected.'
      );
    } catch (error) {
      showNotice(error instanceof Error ? error.message : 'The source scan failed.');
    } finally {
      setBusyAction(null);
    }
  };

  const syncChanges = async () => {
    if (busyAction) return;
    setBusyAction('sync');
    setNotice(null);
    try {
      const result = await syncCompetitorChangedetection();
      await loadDashboard();
      showNotice(
        `Imported ${result.imported} snapshot${result.imported === 1 ? '' : 's'} from changedetection.${result.errors.length ? ` ${result.errors.length} watch errors: ${result.errors.slice(0, 2).join('; ')}` : ''}`
      );
    } catch (error) {
      showNotice(error instanceof Error ? error.message : 'Changedetection sync failed.');
    } finally {
      setBusyAction(null);
    }
  };

  const analyzeEvent = async (event: CompetitorEvent) => {
    setBusyAction(`analyze:${event.id}`);
    try {
      setAnalysis((current) => ({
        ...current,
        [event.id]: {
          summary: 'Analyzing captured evidence…',
          why_it_matters: '',
          recommended_action: '',
          confidence_reason: ''
        }
      }));
      const result = await analyzeCompetitorEvent(event.id);
      setAnalysis((current) => ({ ...current, [event.id]: result }));
    } catch (error) {
      showNotice(error instanceof Error ? error.message : 'AI analysis is unavailable.');
    } finally {
      setBusyAction(null);
    }
  };

  const resetFilters = () => {
    setSearch('');
    setBrand('');
    setImpact('');
    setCountry('');
    setChangeType('');
    setSource('');
  };

  const openView = (nextView: View) => {
    setSelectedEvent(null);
    setView(nextView);
  };

  const renderHeader = () => (
    <header className={styles.header}>
      <button type='button' className='flex items-center gap-3 text-left' onClick={() => openView('feed')} aria-label='JA Assure competitor intelligence home'>
        <span className='grid size-9 place-items-center rounded-[11px] border border-[#e6e6e6] bg-[#f7f7f7] text-sm font-extrabold tracking-[-0.08em] text-black dark:border-[#424242] dark:bg-[#242424] dark:text-white'>JA</span>
        <span>
          <strong className='block text-[15px] tracking-[-0.02em] text-[#09090b] dark:text-white'>JA Assure</strong>
          <small className='mt-0.5 block text-[11px] text-[#737373] dark:text-[#a3a3a3]'>Competitor intelligence</small>
        </span>
      </button>
      <div className='flex max-w-full flex-wrap items-center justify-start gap-2'>
        <button type='button' className={`${quietButton} ${view === 'sources' ? 'bg-[#f5f5f5] text-black dark:bg-[#242424] dark:text-white' : ''}`} onClick={() => openView('sources')}>Sources</button>
        <button type='button' className={`${quietButton} ${view === 'watchlist' ? 'bg-[#f5f5f5] text-black dark:bg-[#242424] dark:text-white' : ''}`} onClick={() => openView('watchlist')}>Watchlist</button>
        <button type='button' className={quietButton} onClick={() => void syncChanges()} disabled={busyAction !== null}>
          {busyAction === 'sync' ? <Icons.spinner className='size-3.5 animate-spin' /> : null}
          {busyAction === 'sync' ? 'Syncing…' : 'Sync 5001 changes'}
        </button>
        <button type='button' className={primaryButton} onClick={() => void runScanAll()} disabled={busyAction !== null}>
          {busyAction === 'scan-all' ? <Icons.spinner className='size-3.5 animate-spin' /> : null}
          {busyAction === 'scan-all' ? 'Scanning…' : 'Scan watchlist'}
        </button>
      </div>
    </header>
  );

  const renderFeed = () => (
    <section className='pt-8'>
      <div className='mb-[17px] flex items-center justify-between gap-4'>
        <div>
          <p className='mb-2.5 text-[10px] font-extrabold uppercase tracking-[0.13em] text-black dark:text-white'>Prioritised feed</p>
          <h1 className='text-[26px] font-semibold tracking-[-0.04em] text-[#09090b] dark:text-white sm:text-[30px]'>Detected changes</h1>
        </div>
        <span className='text-xs text-[#737373] dark:text-[#a3a3a3]'>{filteredEvents.length} event{filteredEvents.length === 1 ? '' : 's'}</span>
      </div>

      <form className='mb-[15px] flex flex-wrap gap-2' onSubmit={(event) => event.preventDefault()}>
        <label className='min-w-0 flex-[2_1_220px]'>
          <span className='sr-only'>Search events</span>
          <div className='relative'>
            <Icons.search className='pointer-events-none absolute left-3 top-1/2 size-3.5 -translate-y-1/2 text-[#a3a3a3]' />
            <input aria-label='Search events' className={`${inputClass} pl-9`} value={search} onChange={(event) => setSearch(event.target.value)} placeholder='Search competitor, summary, or evidence…' />
          </div>
        </label>
        <SelectFilter value={brand} options={selectOptions.brand} onChange={setBrand} label='Brand' />
        <SelectFilter value={impact} options={selectOptions.impact} onChange={setImpact} label='Impact' />
        <SelectFilter value={country} options={selectOptions.country} onChange={setCountry} label='Country' />
        <SelectFilter value={changeType} options={selectOptions.changeType} onChange={setChangeType} label='Change type' />
        <SelectFilter value={source} options={selectOptions.source} onChange={setSource} label='Source' />
        <button type='button' className={`${quietButton} self-stretch`} onClick={resetFilters}>Clear</button>
      </form>

      <div className='flex flex-col gap-2.5' aria-live='polite'>
        {filteredEvents.map((event) => {
          const impactStyle = impactClasses(event.impact);
          return (
            <button key={event.id} type='button' aria-label={`View change from ${competitorName(event, dashboard?.competitors || [])}: ${event.summary}`} className='grid min-w-0 grid-cols-[5px_minmax(0,1fr)] items-stretch gap-4 rounded-xl border border-[#e6e6e6] bg-white pr-4 text-left transition hover:-translate-y-px hover:border-[#737373] hover:bg-[#f7f7f7] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-black dark:border-[#424242] dark:bg-[#171717] dark:hover:border-[#a3a3a3] dark:hover:bg-[#242424] dark:focus-visible:ring-white' onClick={() => setSelectedEvent(event)}>
              <span className={`rounded-r-md ${impactStyle.rail}`} />
              <span className={`${styles.eventBody} py-4`}>
                <span className='min-w-0'>
                  <span className='mb-2 flex min-w-0 flex-wrap items-center gap-[7px]'>
                    <span className={`min-w-0 text-[13px] font-bold text-[#09090b] dark:text-white ${styles.wrapAnywhere}`}>{competitorName(event, dashboard?.competitors || [])}</span>
                    <Badge className={impactStyle.badge}>{label(event.impact)} impact</Badge>
                    <Badge>{label(event.brand_id)}</Badge>
                    {event.relationship ? <Badge className='border-violet-500/35 bg-violet-500/10 text-violet-600 dark:text-violet-300'>{label(event.relationship)}</Badge> : null}
                  </span>
                  <span className={`mb-2 block line-clamp-2 text-[13px] leading-[1.55] text-[#404040] dark:text-[#d4d4d4] ${styles.wrapAnywhere}`}>{event.summary}</span>
                  <span className={`flex flex-wrap items-center gap-x-3 gap-y-1 text-[10px] text-[#737373] dark:text-[#a3a3a3] ${styles.wrapAnywhere}`}>
                    <span>{label(event.change_type)}</span><span>{label(event.country)}</span><span>{event.source}</span><span>{formatDate(event.detected_at)}</span>
                  </span>
                </span>
                <span className='min-w-0 text-left'>
                  <small className='mb-1 block text-[10px] text-[#737373] dark:text-[#a3a3a3]'>Confidence</small>
                  <strong className='text-sm text-black dark:text-white'>{Math.round(event.confidence * 100)}%</strong>
                </span>
              </span>
            </button>
          );
        })}
        {!filteredEvents.length && (
          <div className={`${panelClass} border-dashed px-5 py-11 text-center text-[13px] text-[#737373] dark:text-[#a3a3a3]`}>
            <strong className='mb-2 block text-[15px] text-[#09090b] dark:text-white'>{dashboard?.monitors.some((item) => item.last_checked) ? 'No meaningful changes detected' : 'No baselines captured yet'}</strong>
            {dashboard?.monitors.some((item) => item.last_checked)
              ? 'The latest scans are unchanged; new evidence will appear here when a monitored product page moves.'
              : 'Run a watchlist scan or start the collector worker to capture the first real source snapshot.'}
          </div>
        )}
      </div>
    </section>
  );

  const renderSources = () => (
    <section className='pb-10 pt-8'>
      <div className='mb-5 flex items-end justify-between gap-4'>
        <div>
          <p className='mb-2.5 text-[10px] font-extrabold uppercase tracking-[0.13em] text-black dark:text-white'>Collection layer</p>
          <h1 className='mb-2 text-[30px] font-semibold tracking-[-0.04em] text-[#09090b] dark:text-white'>Source health</h1>
          <p className='m-0 text-[13px] text-[#737373] dark:text-[#a3a3a3]'>Live status of every collection source feeding the feed.</p>
        </div>
        <span className='text-xs text-[#737373] dark:text-[#a3a3a3]'>{dashboard?.source_health.length || 0} sources</span>
      </div>
      <div className={`${panelClass} p-[18px]`}>
        <div className='flex flex-col gap-3'>
          {(dashboard?.source_health || []).map((item) => (
            <div key={item.source} className='flex items-center justify-between gap-3 border-b border-[#e6e6e6] pb-3 last:border-0 last:pb-0 dark:border-[#424242]'>
              <div>
                <div className='text-xs text-[#404040] dark:text-[#d4d4d4]'>{item.source}</div>
                <div className='mt-1 text-[10px] text-[#737373] dark:text-[#a3a3a3]'>{item.detail}</div>
              </div>
              <span className={`text-[10px] uppercase tracking-[0.06em] ${['ready', 'webhook_ready', 'receiving'].includes(item.status) ? 'text-lime-600 dark:text-lime-300' : item.status === 'waiting' ? 'text-amber-600 dark:text-amber-300' : item.status === 'configured' ? 'text-blue-600 dark:text-blue-300' : 'text-[#737373] dark:text-[#a3a3a3]'}`}>
                {item.status.replaceAll('_', ' ')}
              </span>
            </div>
          ))}
          {!dashboard?.source_health.length && <div className='text-sm text-[#737373]'>No source health data yet.</div>}
        </div>
      </div>
    </section>
  );

  const renderWatchlist = () => (
    <section className='pb-10 pt-8'>
      <div className='mb-5 flex flex-col items-start justify-between gap-4 sm:flex-row sm:items-end'>
        <div>
          <p className='mb-2.5 text-[10px] font-extrabold uppercase tracking-[0.13em] text-black dark:text-white'>Registry</p>
          <h1 className='mb-2 text-[30px] font-semibold tracking-[-0.04em] text-[#09090b] dark:text-white'>Watchlist</h1>
          <p className='m-0 text-[13px] text-[#737373] dark:text-[#a3a3a3]'>Every tracked competitor and the URLs being monitored.</p>
        </div>
        <div className='flex w-full items-center gap-3 sm:w-auto'>
          <input aria-label='Search watchlist' className={`${inputClass} sm:w-64`} value={watchSearch} onChange={(event) => setWatchSearch(event.target.value)} placeholder='Search watchlist…' />
          <span className='whitespace-nowrap text-xs text-[#737373] dark:text-[#a3a3a3]'>{filteredCompetitors.length} tracked</span>
        </div>
      </div>
      <div className='flex flex-col gap-3'>
        {filteredCompetitors.map((competitor) => {
          const monitor = dashboard?.monitors.find((item) => item.competitor_id === competitor.id);
          const watches = (dashboard?.watches || []).filter((item) => item.competitor_id === competitor.id);
          const checked = watches.filter((item) => item.last_checked).length;
          return (
            <article key={competitor.id} className={`${panelClass} p-[18px]`}>
              <div className='flex items-start justify-between gap-3'>
                <div>
                  <div className='text-[15px] font-bold tracking-[-0.01em] text-[#09090b] dark:text-white'>{competitor.name}</div>
                  <div className='mt-2 flex flex-wrap gap-1.5'>
                    <Badge>{label(competitor.brand_id)}</Badge>
                    <Badge className='border-violet-500/35 bg-violet-500/10 text-violet-600 dark:text-violet-300'>{label(competitor.relationship)}</Badge>
                  </div>
                </div>
                {monitor?.source_url ? <a className='flex-none text-xs text-blue-600 hover:underline dark:text-blue-300' href={monitor.source_url} target='_blank' rel='noreferrer'>Open source ↗</a> : null}
              </div>
              <p className='mt-2.5 text-xs text-[#404040] dark:text-[#d4d4d4]'>{competitor.product_category} · {competitor.market || competitor.countries.join(', ')}</p>
              <p className='mt-1 text-xs text-[#737373] dark:text-[#a3a3a3]'>{competitor.monitor ? `${watches.length} URL${watches.length === 1 ? '' : 's'} · ${checked} checked · last ${formatDate(monitor?.last_checked || null)}` : 'Context only — not scanned'}</p>
              {competitor.monitor && watches.length > 0 ? (
                <div className='mt-3 border-t border-[#e6e6e6] dark:border-[#424242]'>
                  {watches.map((watch) => (
                    <div key={watch.id} className='flex flex-col items-stretch justify-between gap-3 border-b border-[#e6e6e6] py-3 last:border-0 last:pb-0 dark:border-[#424242] sm:flex-row sm:items-center'>
                      <div className='flex min-w-0 flex-col gap-1'>
                        <a className='truncate text-xs font-semibold text-blue-600 hover:underline dark:text-blue-300' href={watch.url} target='_blank' rel='noreferrer'>{watch.id}</a>
                        <span className='text-[11px] text-[#737373] dark:text-[#a3a3a3]'>{watch.kind} · every {watch.interval_hours}h · {watch.priority} priority</span>
                      </div>
                      <button type='button' className={`${quietButton} h-8 flex-none px-3`} disabled={busyAction !== null} onClick={() => void runWatchScan(watch)}>
                        {busyAction === `scan-watch:${watch.id}` ? <Icons.spinner className='size-3.5 animate-spin' /> : null}
                        {busyAction === `scan-watch:${watch.id}` ? 'Scanning…' : 'Scan'}
                      </button>
                    </div>
                  ))}
                </div>
              ) : null}
            </article>
          );
        })}
        {!filteredCompetitors.length && <div className={`${panelClass} border-dashed px-5 py-11 text-center text-[13px] text-[#737373] dark:text-[#a3a3a3]`}>Add competitors to the registry or clear the watchlist search.</div>}
      </div>
    </section>
  );

  const renderEventDetail = () => {
    if (!selectedEvent) return null;
    const event = selectedEvent;
    const eventAnalysis = analysis[event.id];
    return (
      <section className='mx-auto max-w-[980px] min-w-0 pb-10 pt-7'>
        <button type='button' className='mb-[18px] inline-flex text-[13px] text-[#737373] hover:text-[#09090b] hover:underline dark:text-[#a3a3a3] dark:hover:text-white' onClick={() => setSelectedEvent(null)}>← Back to feed</button>
        <p className={`mb-3 text-[10px] font-extrabold uppercase tracking-[0.13em] text-[#737373] dark:text-[#a3a3a3] ${styles.wrapAnywhere}`}>{competitorName(event, dashboard?.competitors || [])} · {label(event.country)}</p>
        <h1 className={`mb-3.5 line-clamp-2 text-[26px] font-semibold leading-tight tracking-[-0.035em] text-[#09090b] dark:text-white sm:text-[30px] ${styles.wrapAnywhere}`}>{event.summary}</h1>
        <div className='mb-5 flex flex-wrap items-center gap-2'>
          <Badge className={impactClasses(event.impact).badge}>{label(event.impact)} impact</Badge>
          <Badge>{label(event.brand_id)}</Badge>
          {event.relationship ? <Badge className='border-violet-500/35 bg-violet-500/10 text-violet-600 dark:text-violet-300'>{label(event.relationship)}</Badge> : null}
          <span className='text-xs text-[#737373] dark:text-[#a3a3a3]'>{formatDate(event.detected_at)} via {event.source}</span>
        </div>
        <div className={`${panelClass} min-w-0 p-4 sm:p-6`}>
          <div className='mb-5'>
            <h2 className='mb-2 text-[10px] font-bold uppercase tracking-[0.1em] text-[#737373] dark:text-[#a3a3a3]'>Change summary</h2>
            <p className={`m-0 text-[13px] leading-[1.6] text-[#404040] dark:text-[#d4d4d4] ${styles.wrapAnywhere}`}>{event.summary}</p>
          </div>
          <div className={`${styles.metadataGrid} gap-2.5`}>
            {[
              ['Competitor', competitorName(event, dashboard?.competitors || [])],
              ['Market', label(event.country)],
              ['Change type', label(event.change_type)],
              ['Analysis confidence', `${Math.round(event.confidence * 100)}%`],
              ...(event.product_category ? [['Product category', event.product_category]] : []),
              ['Source', event.source]
            ].map(([name, value]) => (
              <div key={name} className='min-w-0 rounded-[9px] border border-[#e6e6e6] bg-[#f7f7f7] p-3 dark:border-[#424242] dark:bg-[#242424]'>
                <span className='mb-1.5 block text-[10px] text-[#737373] dark:text-[#a3a3a3]'>{name}</span>
                <strong className={`text-[13px] text-[#09090b] dark:text-white ${styles.wrapAnywhere}`}>{value}</strong>
              </div>
            ))}
          </div>
          {event.previous_value || event.current_value ? (
            <div className={`${styles.metadataGrid} mt-2.5 gap-2.5`}>
              {[
                ['Before', event.previous_value || 'Not found'],
                ['After', event.current_value || 'Not found']
              ].map(([name, value]) => (
                <div key={name} className='min-w-0 rounded-[9px] border border-[#e6e6e6] bg-[#f7f7f7] p-3 dark:border-[#424242] dark:bg-[#242424]'>
                  <span className='mb-1.5 block text-[10px] text-[#737373] dark:text-[#a3a3a3]'>{name}</span>
                  <strong className={`text-[13px] text-[#09090b] dark:text-white ${styles.wrapAnywhere}`}>{value}</strong>
                </div>
              ))}
            </div>
          ) : null}
          <div className='mt-[17px]'>
            <h2 className='mb-2 text-[10px] font-bold uppercase tracking-[0.1em] text-[#737373] dark:text-[#a3a3a3]'>Why it matters</h2>
            <p className='m-0 text-[13px] leading-[1.6] text-[#404040] dark:text-[#d4d4d4]'>{event.why_it_matters}</p>
          </div>
          <div className='mt-[17px]'>
            <h2 className='mb-2 text-[10px] font-bold uppercase tracking-[0.1em] text-[#737373] dark:text-[#a3a3a3]'>Recommended action</h2>
            <p className='m-0 text-[13px] leading-[1.6] text-[#404040] dark:text-[#d4d4d4]'>{event.recommended_action}</p>
          </div>
          <div className='mt-[17px]'>
            <h2 className='mb-2 text-[10px] font-bold uppercase tracking-[0.1em] text-[#737373] dark:text-[#a3a3a3]'>Captured evidence</h2>
            <p className={`border-l-2 border-black bg-[#f5f5f5] p-3 text-xs leading-[1.6] text-[#404040] dark:border-white dark:bg-[#242424] dark:text-[#d4d4d4] ${styles.wrapAnywhere}`}>{event.evidence}</p>
          </div>
          <div className='mt-[17px]'>
            <h2 className='mb-2 text-[10px] font-bold uppercase tracking-[0.1em] text-[#737373] dark:text-[#a3a3a3]'>Before / after diff</h2>
            <pre className={`max-h-[300px] min-w-0 overflow-auto whitespace-pre-wrap border border-[#e6e6e6] p-3 text-[11px] leading-[1.5] text-[#404040] dark:border-[#424242] dark:text-[#d4d4d4] ${styles.wrapAnywhere}`}>{eventDiff === null ? 'Loading captured diff…' : eventDiff || 'No line changes in the captured evidence.'}</pre>
          </div>
          <div className='mt-[17px]'>
            <div className='flex flex-wrap gap-2'>
              <button type='button' className={primaryButton} disabled={busyAction === `analyze:${event.id}`} onClick={() => void analyzeEvent(event)}>
                {busyAction === `analyze:${event.id}` ? <Icons.spinner className='size-3.5 animate-spin' /> : <Icons.sparkles className='size-3.5' />}
                {busyAction === `analyze:${event.id}` ? 'Analyzing…' : 'Analyze with AI'}
              </button>
              {event.source_url ? <a className={quietButton} href={event.source_url} target='_blank' rel='noreferrer'>Open source ↗</a> : null}
            </div>
            {eventAnalysis ? (
              <div className='mt-3 text-[13px] leading-[1.6] text-[#404040] dark:text-[#d4d4d4]'>
                <h3 className='mb-1 font-semibold text-[#09090b] dark:text-white'>{eventAnalysis.summary}</h3>
                {eventAnalysis.why_it_matters ? <p className='mb-2'>{eventAnalysis.why_it_matters}</p> : null}
                {eventAnalysis.recommended_action ? <><h4 className='mb-1 font-semibold text-[#09090b] dark:text-white'>Recommended action</h4><p className='mb-2'>{eventAnalysis.recommended_action}</p></> : null}
                {eventAnalysis.confidence_reason ? <small className='text-[#737373] dark:text-[#a3a3a3]'>{eventAnalysis.confidence_reason}</small> : null}
              </div>
            ) : null}
          </div>
        </div>
      </section>
    );
  };

  return (
    <main className='min-h-[calc(100vh-4rem)] min-w-0 w-full bg-white px-4 pb-16 pt-6 text-[#09090b] dark:bg-black dark:text-white sm:px-6 lg:px-8 xl:px-12'>
      <div className={`mx-auto min-w-0 w-full max-w-[1440px] ${styles.workspace}`}>
        {renderHeader()}
        {notice ? (
          <div className='fixed bottom-5 right-5 z-50 flex max-w-[380px] items-start gap-2.5 rounded-[10px] border border-[#e6e6e6] bg-white p-3 text-[13px] leading-6 text-[#09090b] shadow-2xl dark:border-[#424242] dark:bg-[#171717] dark:text-white' role='status'>
            <span className='flex-1'>{notice}</span>
            <button type='button' className='grid size-6 flex-none place-items-center rounded-full border border-[#e6e6e6] text-[#737373] dark:border-[#424242]' onClick={() => setNotice(null)} aria-label='Dismiss notification'>×</button>
          </div>
        ) : null}
        {isLoading && !dashboard ? (
          <div className='flex items-center gap-2 py-20 text-sm text-[#737373] dark:text-[#a3a3a3]'><Icons.spinner className='size-4 animate-spin' /> Loading intelligence data…</div>
        ) : selectedEvent ? renderEventDetail() : view === 'sources' ? renderSources() : view === 'watchlist' ? renderWatchlist() : renderFeed()}
      </div>
      {busyAction?.startsWith('scan') ? (
        <div className='fixed inset-0 z-40 flex items-center justify-center bg-black/45 p-5 backdrop-blur-[2px]' role='dialog' aria-modal='true' aria-busy='true'>
          <div className='w-full max-w-[360px] rounded-[14px] border border-[#e6e6e6] bg-white p-7 text-center shadow-2xl dark:border-[#424242] dark:bg-[#171717]'>
            <div className='mx-auto mb-4 size-8 animate-spin rounded-full border-[3px] border-[#e6e6e6] border-t-black dark:border-[#424242] dark:border-t-white' />
            <h2 className='mb-2 text-[17px] font-semibold tracking-[-0.02em]'>Scanning</h2>
            <p className='mb-[18px] text-[13px] leading-6 text-[#737373] dark:text-[#a3a3a3]'>Checking sources for changes. This may take a few seconds.</p>
            <div className='h-1 overflow-hidden rounded-full border border-[#e6e6e6] bg-[#f7f7f7] dark:border-[#424242] dark:bg-[#242424]'><span className='block h-full w-2/5 animate-pulse rounded-full bg-black dark:bg-white' /></div>
          </div>
        </div>
      ) : null}
    </main>
  );
}
