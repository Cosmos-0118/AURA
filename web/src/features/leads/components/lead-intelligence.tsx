'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Icons } from '@/components/icons';
import PageContainer from '@/components/layout/page-container';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Textarea } from '@/components/ui/textarea';
import { getLeadEmailDraft, getLeadRefreshStatus, listLeads, refreshLeads, sendLeadEmail } from '@/lib/api/client';
import type { BrandId, Lead, LeadEmailDraft, LeadRefreshStatus } from '@/lib/api/types';

const BRANDS: { id: BrandId | 'all'; label: string }[] = [
  { id: 'all', label: 'All' },
  { id: 'jade', label: 'Jade' },
  { id: 'doctorshield', label: 'DoctorShield' },
  { id: 'jaguar', label: 'Jaguar Transit' },
];

const LOADING_STEPS = ['Searching company sites', 'Reading the public page', 'Checking contact details'];

// Theme tokens shared with the competitor-intelligence page.
const buttonBase =
  'inline-flex h-9 items-center justify-center gap-2 rounded-[9px] border px-3 text-xs font-semibold transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-black dark:focus-visible:ring-white disabled:cursor-wait disabled:opacity-55';
const quietButton = `${buttonBase} border-[#e6e6e6] bg-transparent text-[#404040] hover:bg-[#f5f5f5] dark:border-[#424242] dark:text-[#d4d4d4] dark:hover:bg-[#242424]`;
const primaryButton = `${buttonBase} border-[#09090b] bg-[#09090b] text-white shadow-sm hover:opacity-85 dark:border-white dark:bg-white dark:text-black`;
const inputClass =
  'h-[38px] w-full rounded-lg border border-[#e6e6e6] bg-white px-3 text-xs text-[#404040] outline-none transition placeholder:text-[#a3a3a3] focus:border-[#737373] focus:ring-2 focus:ring-black/10 dark:border-[#424242] dark:bg-[#171717] dark:text-[#e5e5e5] dark:placeholder:text-[#737373] dark:focus:border-[#a3a3a3] dark:focus:ring-white/10';
const panelClass =
  'rounded-[13px] border border-[#e6e6e6] bg-white shadow-sm dark:border-[#424242] dark:bg-[#171717]';

const BRAND_LABEL: Record<BrandId, string> = {
  jade: 'Jade',
  doctorshield: 'DoctorShield',
  jaguar: 'Jaguar Transit',
};

const BRAND_DOT: Record<BrandId, string> = {
  jade: 'bg-emerald-500',
  doctorshield: 'bg-blue-500',
  jaguar: 'bg-amber-500',
};

type SortKey = 'fit' | 'name' | 'country';
type ContactFilter = 'all' | 'email' | 'phone' | 'reachable';

function brandLabel(id: string | null | undefined): string {
  if (!id) return 'Unknown';
  return BRAND_LABEL[id as BrandId] || id;
}

function initials(name: string): string {
  const words = name.trim().split(/\s+/).filter(Boolean);
  if (words.length === 0) return '••';
  if (words.length === 1) return words[0].slice(0, 2).toUpperCase();
  return (words[0][0] + words[1][0]).toUpperCase();
}

function fitTone(score: number): { label: string; badge: string } {
  if (score >= 85) {
    return {
      label: 'Prime fit',
      badge: 'border-emerald-500/35 bg-emerald-500/10 text-emerald-600 dark:text-emerald-300',
    };
  }
  if (score >= 70) {
    return {
      label: 'Strong fit',
      badge: 'border-blue-500/35 bg-blue-500/10 text-blue-600 dark:text-blue-300',
    };
  }
  return {
    label: 'Review fit',
    badge: 'border-amber-500/35 bg-amber-500/10 text-amber-600 dark:text-amber-300',
  };
}

function sortLeads(rows: Lead[]) {
  return [...rows].sort((left, right) => {
    const scoreDiff = right.fit_score - left.fit_score;
    if (scoreDiff !== 0) return scoreDiff;
    return left.name.localeCompare(right.name);
  });
}

function formatWhen(value: string | null) {
  if (!value) return 'Not yet';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return 'Not yet';
  return date.toLocaleString();
}

function hostOf(url: string | null): string {
  if (!url) return 'Not listed';
  return url.replace(/^https?:\/\//, '').replace(/^www\./, '').split('/')[0];
}

function LeadLoadingCard({ label }: { label: string }) {
  return (
    <div className={`${panelClass} p-[18px]`} aria-busy='true' aria-live='polite'>
      <div className='flex items-center gap-3'>
        <Skeleton className='size-10 rounded-full' />
        <div className='flex-1 space-y-2'>
          <Skeleton className='h-4 w-2/3' />
          <Skeleton className='h-3 w-1/3' />
        </div>
        <Skeleton className='h-6 w-14 rounded-full' />
      </div>
      <div className='mt-4 space-y-2'>
        <Skeleton className='h-3 w-full' />
        <Skeleton className='h-3 w-11/12' />
        <Skeleton className='h-3 w-2/3' />
      </div>
      <div className='mt-4 flex items-center gap-2 text-xs text-[#737373] dark:text-[#a3a3a3]'>
        <Icons.spinner className='size-3.5 animate-spin' />
        {label}…
      </div>
    </div>
  );
}

export default function LeadIntelligence() {
  const [brand, setBrand] = useState<(typeof BRANDS)[number]['id']>('all');
  const [query, setQuery] = useState('');
  const [sort, setSort] = useState<SortKey>('fit');
  const [contact, setContact] = useState<ContactFilter>('all');
  const [leads, setLeads] = useState<Lead[]>([]);
  const [shown, setShown] = useState<Lead[]>([]);
  const [status, setStatus] = useState<LeadRefreshStatus | null>(null);
  const [pending, setPending] = useState(false);
  const [draftLead, setDraftLead] = useState<Lead | null>(null);
  const [draft, setDraft] = useState<LeadEmailDraft | null>(null);
  const [draftError, setDraftError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState(false);
  const [queued, setQueued] = useState(0);
  const [isSwitchingBrand, setIsSwitchingBrand] = useState(false);
  const [loadingStep, setLoadingStep] = useState(0);
  const seenRef = useRef<Set<string>>(new Set());
  const queueRef = useRef<Lead[]>([]);
  const brandRef = useRef(brand);
  const seededRef = useRef(false);
  const requestRef = useRef(0);
  const refreshing = pending || Boolean(status?.refreshing);

  const load = useCallback(async () => {
    const request = ++requestRef.current;
    try {
      const [rows, refresh] = await Promise.all([
        listLeads(brand === 'all' ? undefined : brand),
        getLeadRefreshStatus(),
      ]);
      if (request !== requestRef.current) return;
      setLeads(sortLeads(rows));
      setStatus(refresh);
      setIsSwitchingBrand(false);
      if (!refresh.refreshing) setPending(false);
    } catch {
      if (request !== requestRef.current) return;
      setIsSwitchingBrand(false);
    }
  }, [brand]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (!refreshing && shown.length > 0 && queueRef.current.length === 0) return;
    const timer = window.setInterval(() => {
      void load();
    }, refreshing ? 1500 : 5000);
    return () => window.clearInterval(timer);
  }, [refreshing, shown.length, load]);

  useEffect(() => {
    if (brandRef.current !== brand) {
      brandRef.current = brand;
      seededRef.current = false;
      seenRef.current = new Set();
      queueRef.current = [];
      setQueued(0);
      setShown([]);
      setLeads([]);
      setIsSwitchingBrand(true);
    }
  }, [brand]);

  useEffect(() => {
    if (refreshing && leads.length === 0) {
      seededRef.current = true;
      seenRef.current = new Set();
      queueRef.current = [];
      setQueued(0);
      setShown([]);
      return;
    }
    const fresh = leads.filter((lead) => !seenRef.current.has(lead.id));
    if (!seededRef.current) {
      fresh.forEach((lead) => seenRef.current.add(lead.id));
      if (leads.length > 0 || status) {
        seededRef.current = true;
        if (refreshing) queueRef.current.push(...fresh);
        else setShown(leads);
      }
      setQueued(queueRef.current.length);
      return;
    }
    fresh.forEach((lead) => seenRef.current.add(lead.id));
    if (fresh.length) queueRef.current.push(...fresh);
    setQueued(queueRef.current.length);
  }, [leads, refreshing, status]);

  useEffect(() => {
    const timer = window.setInterval(() => {
      const next = queueRef.current.shift();
      if (!next) return;
      setQueued(queueRef.current.length);
      setShown((current) => (current.some((item) => item.id === next.id) ? current : [...current, next]));
    }, 450);
    return () => window.clearInterval(timer);
  }, []);

  const awaiting = status === null;
  const loadingCompanies = refreshing || queued > 0 || awaiting || isSwitchingBrand;

  useEffect(() => {
    if (!loadingCompanies) return;
    const timer = window.setInterval(() => {
      setLoadingStep((current) => (current + 1) % LOADING_STEPS.length);
    }, 1400);
    return () => window.clearInterval(timer);
  }, [loadingCompanies]);

  const openDraft = async (lead: Lead) => {
    setDraftLead(lead);
    setDraft(null);
    setDraftError(null);
    setSent(false);
    try {
      setDraft(await getLeadEmailDraft(lead.id));
    } catch (err) {
      setDraftError(err instanceof Error ? err.message : 'Could not prepare this email.');
    }
  };

  const sendDraft = async () => {
    if (!draftLead || sending) return;
    setSending(true);
    setDraftError(null);
    try {
      await sendLeadEmail(draftLead.id);
      setSent(true);
    } catch (err) {
      setDraftError(err instanceof Error ? err.message : 'Could not send this email.');
    } finally {
      setSending(false);
    }
  };

  const runRefresh = () => {
    setPending(true);
    seenRef.current = new Set();
    queueRef.current = [];
    setQueued(0);
    setShown([]);
    setLeads([]);
    void refreshLeads().then(() => load());
  };

  const resetFilters = () => {
    setQuery('');
    setSort('fit');
    setContact('all');
  };

  const average = useMemo(() => {
    if (!shown.length) return 0;
    return Math.round(shown.reduce((sum, lead) => sum + lead.fit_score, 0) / shown.length);
  }, [shown]);

  const highFit = useMemo(() => shown.filter((lead) => lead.fit_score >= 85).length, [shown]);
  const reachable = useMemo(() => shown.filter((lead) => Boolean(lead.email || lead.phone)).length, [shown]);

  const visible = useMemo(() => {
    const text = query.trim().toLowerCase();
    const filtered = shown.filter((lead) => {
      if (contact === 'email' && !lead.email) return false;
      if (contact === 'phone' && !lead.phone) return false;
      if (contact === 'reachable' && !lead.email && !lead.phone) return false;
      if (!text) return true;
      const haystack = [lead.name, lead.country, lead.requirements, lead.why, lead.email, lead.url]
        .filter(Boolean)
        .join(' ')
        .toLowerCase();
      return haystack.includes(text);
    });
    if (sort === 'name') return [...filtered].sort((a, b) => a.name.localeCompare(b.name));
    if (sort === 'country')
      return [...filtered].sort((a, b) => (a.country || 'zzz').localeCompare(b.country || 'zzz'));
    return sortLeads(filtered);
  }, [shown, query, sort, contact]);

  const hasFilters = query.trim() !== '' || sort !== 'fit' || contact !== 'all';

  return (
    <PageContainer>
      <div className='flex flex-1 flex-col gap-4 pb-12'>
        {/* Header — same language as the other dashboard pages */}
        <div className='flex flex-col justify-between gap-4 pt-2 md:flex-row md:items-end'>
          <div>
            <p className='mb-2 text-[10px] font-extrabold uppercase tracking-[0.13em] text-black dark:text-white'>
              TinyFish live discovery
            </p>
            <h1 className='text-[30px] font-semibold tracking-[-0.04em] text-[#09090b] dark:text-white'>
              Lead Intelligence
            </h1>
            <p className='mt-1 max-w-2xl text-[13px] text-[#737373] dark:text-[#a3a3a3]'>
              Qualified companies from public pages, scored for fit. Filter by brand, search, and send mail.
            </p>
          </div>
          <div className='flex flex-wrap items-center gap-2'>
            {loadingCompanies && (
              <span className='inline-flex items-center gap-2 text-xs text-[#737373] dark:text-[#a3a3a3]'>
                <Icons.spinner className='size-3.5 animate-spin' />
                {LOADING_STEPS[loadingStep]}…
              </span>
            )}
            <button type='button' className={primaryButton} onClick={runRefresh} disabled={refreshing}>
              {refreshing ? <Icons.spinner className='size-3.5 animate-spin' /> : <Icons.search className='size-3.5' />}
              {refreshing ? 'Refreshing…' : 'Refresh discovery'}
            </button>
          </div>
        </div>

        {/* Compact KPI strip */}
        <div className='grid gap-3 sm:grid-cols-2 xl:grid-cols-4'>
          {[
            { title: 'Qualified', value: shown.length, hint: 'In the current brand view' },
            { title: 'Prime fit 85+', value: highFit, hint: 'Ready for outreach' },
            { title: 'Reachable', value: reachable, hint: 'Email or phone published' },
            { title: 'Average fit', value: average, hint: 'Across loaded companies' },
          ].map((stat) => (
            <div key={stat.title} className={`${panelClass} px-4 py-3.5`}>
              <p className='text-[10px] font-extrabold uppercase tracking-[0.13em] text-black dark:text-white'>
                {stat.title}
              </p>
              <div className='mt-1 flex items-baseline justify-between gap-2'>
                <span className='text-[26px] font-semibold tracking-[-0.04em] text-[#09090b] dark:text-white'>
                  {stat.value}
                </span>
                <span className='text-[11px] text-[#737373] dark:text-[#a3a3a3]'>{stat.hint}</span>
              </div>
            </div>
          ))}
        </div>

        {/* Toolbar */}
        <div className={panelClass}>
          <div className='flex flex-col gap-3 p-3'>
            <div className='flex flex-wrap items-center gap-2'>
              {BRANDS.map((item) => {
                const active = brand === item.id;
                return (
                  <button
                    key={item.id}
                    type='button'
                    onClick={() => setBrand(item.id)}
                    aria-pressed={active}
                    className={`${quietButton} ${active ? 'bg-[#f5f5f5] text-black dark:bg-[#242424] dark:text-white' : ''}`}
                  >
                    {item.id !== 'all' && (
                      <span className={`size-2 rounded-full ${BRAND_DOT[item.id as BrandId]}`} />
                    )}
                    {item.label}
                  </button>
                );
              })}
              <span className='ml-auto hidden text-[11px] text-[#737373] sm:block dark:text-[#a3a3a3]'>
                {visible.length} of {shown.length} shown · Last update {formatWhen(status?.last_scraped_at ?? null)}
              </span>
            </div>
            <div className='flex flex-col gap-2 sm:flex-row'>
              <label className='min-w-0 flex-[2_1_220px]'>
                <span className='sr-only'>Search companies</span>
                <div className='relative'>
                  <Icons.search className='pointer-events-none absolute left-3 top-1/2 size-3.5 -translate-y-1/2 text-[#a3a3a3]' />
                  <input
                    aria-label='Search companies'
                    className={`${inputClass} pl-9`}
                    value={query}
                    onChange={(event) => setQuery(event.target.value)}
                    placeholder='Search company, market, signal, or email…'
                  />
                </div>
              </label>
              <label className='min-w-0 flex-1'>
                <span className='sr-only'>Sort companies</span>
                <select
                  aria-label='Sort companies'
                  className={inputClass}
                  value={sort}
                  onChange={(event) => setSort(event.target.value as SortKey)}
                >
                  <option value='fit'>Sort: Best fit</option>
                  <option value='name'>Sort: Name A–Z</option>
                  <option value='country'>Sort: Market A–Z</option>
                </select>
              </label>
              <label className='min-w-0 flex-1'>
                <span className='sr-only'>Contact availability</span>
                <select
                  aria-label='Contact availability'
                  className={inputClass}
                  value={contact}
                  onChange={(event) => setContact(event.target.value as ContactFilter)}
                >
                  <option value='all'>Contact: Any</option>
                  <option value='email'>Contact: Has email</option>
                  <option value='phone'>Contact: Has phone</option>
                  <option value='reachable'>Contact: Email or phone</option>
                </select>
              </label>
              <button type='button' className={quietButton} onClick={resetFilters} disabled={!hasFilters}>
                Clear
              </button>
            </div>
          </div>
        </div>

        {status && status.configured === false && (
          <Card className={`${panelClass} border-amber-500/35`}>
            <CardHeader>
              <CardTitle className='flex items-center gap-2 text-base'>
                <Icons.warning className='size-4 text-amber-600' />
                Discovery is not configured
              </CardTitle>
              <CardDescription>
                Add TinyFish_API_KEY to the project .env, then refresh. Lead Intelligence does not use a preset
                company list.
              </CardDescription>
            </CardHeader>
          </Card>
        )}

        {visible.length === 0 && !loadingCompanies ? (
          <div className={`${panelClass} border-dashed px-5 py-12 text-center`}>
            <span className='mx-auto mb-3 grid size-11 place-items-center rounded-full border border-[#e6e6e6] bg-[#f7f7f7] text-[#404040] dark:border-[#424242] dark:bg-[#242424] dark:text-[#d4d4d4]'>
              <Icons.search className='size-4' />
            </span>
            <p className='text-[15px] font-semibold text-[#09090b] dark:text-white'>
              {shown.length === 0 ? 'No companies yet' : 'No companies match these filters'}
            </p>
            <p className='mx-auto mt-1 max-w-md text-[13px] text-[#737373] dark:text-[#a3a3a3]'>
              {shown.length === 0
                ? 'Refresh to search the web. Each card appears as soon as its public page is read.'
                : 'Try clearing the search or choosing a different brand, sort, or contact filter.'}
            </p>
            <div className='mt-4 flex justify-center gap-2'>
              {shown.length === 0 ? (
                <button type='button' className={primaryButton} onClick={runRefresh} disabled={refreshing}>
                  {refreshing ? 'Refreshing…' : 'Refresh discovery'}
                </button>
              ) : (
                <button type='button' className={quietButton} onClick={resetFilters}>
                  Clear filters
                </button>
              )}
            </div>
          </div>
        ) : (
          <div className='grid items-start gap-3 md:grid-cols-2 xl:grid-cols-3'>
            {visible.map((lead) => {
              const tone = fitTone(lead.fit_score);
              return (
                <article key={lead.id} className={`${panelClass} p-5`}>
                  <div className='flex items-start justify-between gap-3'>
                    <div className='flex min-w-0 items-center gap-3'>
                      <span className='grid size-10 flex-none place-items-center rounded-[10px] bg-[#09090b] text-xs font-bold text-white dark:bg-white dark:text-black'>
                        {initials(lead.name)}
                      </span>
                      <div className='min-w-0'>
                        <h2
                          className='truncate text-[15px] font-semibold tracking-[-0.01em] text-[#09090b] dark:text-white'
                          title={lead.name}
                        >
                          {lead.name}
                        </h2>
                        <p className='mt-0.5 flex items-center gap-1.5 text-[11px] text-[#737373] dark:text-[#a3a3a3]'>
                          {lead.brand_id in BRAND_DOT && (
                            <span className={`size-1.5 rounded-full ${BRAND_DOT[lead.brand_id]}`} />
                          )}
                          <span className='truncate'>
                            {brandLabel(lead.brand_id)} · {lead.country || 'Market not found'}
                          </span>
                        </p>
                      </div>
                    </div>
                    <span
                      className={`inline-flex flex-none items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-semibold ${tone.badge}`}
                    >
                      {lead.fit_score} · {tone.label.replace(' fit', '')}
                    </span>
                  </div>

                  <p className='mt-3 line-clamp-2 min-h-[42px] text-[13px] leading-[1.6] text-[#404040] dark:text-[#d4d4d4]'>
                    {lead.requirements || lead.why || 'Public page did not expose a clear requirement yet.'}
                  </p>

                  <div className='mt-3 divide-y divide-[#eeeeee] rounded-[10px] border border-[#eeeeee] text-[12px] dark:divide-[#2e2e2e] dark:border-[#2e2e2e]'>
                    <div className='flex items-center justify-between gap-3 px-3 py-2'>
                      <span className='flex-none text-[#737373] dark:text-[#a3a3a3]'>Website</span>
                      {lead.url ? (
                        <a
                          className='min-w-0 truncate font-medium text-[#09090b] hover:underline dark:text-white'
                          href={lead.url}
                          target='_blank'
                          rel='noreferrer'
                          title={lead.url}
                        >
                          {hostOf(lead.url)}
                        </a>
                      ) : (
                        <span className='text-[#a3a3a3]'>—</span>
                      )}
                    </div>
                    <div className='flex items-center justify-between gap-3 px-3 py-2'>
                      <span className='flex-none text-[#737373] dark:text-[#a3a3a3]'>Email</span>
                      {lead.email ? (
                        <span className='min-w-0 truncate text-[#404040] dark:text-[#d4d4d4]' title={lead.email}>
                          {lead.email}
                        </span>
                      ) : (
                        <span className='text-[#a3a3a3]'>—</span>
                      )}
                    </div>
                    <div className='flex items-center justify-between gap-3 px-3 py-2'>
                      <span className='flex-none text-[#737373] dark:text-[#a3a3a3]'>Phone</span>
                      {lead.phone ? (
                        <span className='min-w-0 truncate text-[#404040] dark:text-[#d4d4d4]'>{lead.phone}</span>
                      ) : (
                        <span className='text-[#a3a3a3]'>—</span>
                      )}
                    </div>
                  </div>

                  {lead.source_url && (
                    <p className='mt-2 truncate text-[11px] text-[#a3a3a3]'>
                      via{' '}
                      <a
                        className='hover:underline'
                        href={lead.source_url}
                        target='_blank'
                        rel='noreferrer'
                        title={lead.source_url}
                      >
                        {lead.source_title || hostOf(lead.source_url)}
                      </a>
                    </p>
                  )}

                  <div className='mt-3 flex gap-2 border-t border-[#eeeeee] pt-3 dark:border-[#2e2e2e]'>
                    {lead.url ? (
                      <a className={`${quietButton} flex-1`} href={lead.url} target='_blank' rel='noreferrer'>
                        Open site
                        <Icons.externalLink className='size-3.5' />
                      </a>
                    ) : (
                      <button type='button' className={quietButton} disabled style={{ flex: 1 }}>
                        No site
                      </button>
                    )}
                    <button
                      type='button'
                      className={primaryButton}
                      style={{ flex: 1 }}
                      disabled={!lead.email}
                      onClick={() => void openDraft(lead)}
                      title={lead.email ? `Send mail to ${lead.email}` : 'Needs a published email'}
                    >
                      <Icons.send className='size-3.5' />
                      {lead.email ? 'Send mail' : 'No email'}
                    </button>
                  </div>
                </article>
              );
            })}
            {loadingCompanies &&
              Array.from({ length: visible.length === 0 ? 6 : 2 }, (_, index) => (
                <LeadLoadingCard
                  key={`loading-${index}`}
                  label={LOADING_STEPS[(loadingStep + index) % LOADING_STEPS.length]}
                />
              ))}
          </div>
        )}
      </div>

      <Dialog
        open={draftLead !== null}
        onOpenChange={(open) => {
          if (!open) {
            setDraftLead(null);
            setDraft(null);
            setDraftError(null);
            setSent(false);
          }
        }}
      >
        <DialogContent className='sm:max-w-xl'>
          <DialogHeader>
            <DialogTitle>Send mail</DialogTitle>
            <DialogDescription>
              {draftLead ? (
                <>
                  To {draftLead.name} · {draftLead.email || 'no published email'}
                </>
              ) : (
                'From your Gmail account to the address on this lead.'
              )}
            </DialogDescription>
          </DialogHeader>
          {draft ? (
            <div className='space-y-3'>
              <div className={`${panelClass} space-y-1.5 p-3 text-sm`}>
                <p>
                  <span className='text-muted-foreground'>From </span>
                  {draft.from_email}
                </p>
                <p>
                  <span className='text-muted-foreground'>To </span>
                  {draft.to_email}
                </p>
                <p>
                  <span className='text-muted-foreground'>Subject </span>
                  {draft.subject}
                </p>
              </div>
              <Textarea readOnly value={draft.body} className='min-h-56 font-mono text-xs' />
              {!draft.configured && (
                <p className='text-sm text-destructive'>
                  Gmail does not use an API key. Add GMAIL_APP_PASSWORD to .env. Create it at
                  myaccount.google.com/apppasswords for {draft.from_email}.
                </p>
              )}
            </div>
          ) : (
            <p className='text-sm text-muted-foreground'>Preparing the email template…</p>
          )}
          {draftError && <p className='text-sm text-destructive'>{draftError}</p>}
          {sent && <p className='text-sm'>Sent from {draft?.from_email} to {draft?.to_email}.</p>}
          <DialogFooter>
            <Button
              type='button'
              variant='outline'
              onClick={() => {
                setDraftLead(null);
                setDraft(null);
                setDraftError(null);
                setSent(false);
              }}
            >
              Cancel
            </Button>
            <Button type='button' onClick={() => void sendDraft()} disabled={!draft?.configured || sending || sent}>
              {sending ? 'Sending…' : sent ? 'Sent' : 'Send email'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </PageContainer>
  );
}
