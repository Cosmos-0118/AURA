'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { Icons } from '@/components/icons';
import PageContainer from '@/components/layout/page-container';
import { Button } from '@/components/ui/button';
import { Card, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from '@/components/ui/dialog';
import { Textarea } from '@/components/ui/textarea';
import {
  getLead,
  getLeadEmailDraft,
  getLeadRefreshStatus,
  listLeads,
  refreshLeads,
  sendLeadEmail
} from '@/lib/api/client';
import type { BrandId, Lead, LeadEmailDraft, LeadRefreshStatus } from '@/lib/api/types';

const BRANDS: { id: BrandId | 'all'; label: string }[] = [
  { id: 'all', label: 'All' },
  { id: 'jade', label: 'Jade' },
  { id: 'doctorshield', label: 'DoctorShield' },
  { id: 'jaguar', label: 'Jaguar Transit' }
];

const DEFAULT_PAGE_SIZE = 40;

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
  jaguar: 'Jaguar Transit'
};

const BRAND_DOT: Record<BrandId, string> = {
  jade: 'bg-emerald-500',
  doctorshield: 'bg-blue-500',
  jaguar: 'bg-amber-500'
};

type SortKey = 'fit' | 'name';
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
      badge: 'border-emerald-500/35 bg-emerald-500/10 text-emerald-600 dark:text-emerald-300'
    };
  }
  if (score >= 70) {
    return {
      label: 'Strong fit',
      badge: 'border-blue-500/35 bg-blue-500/10 text-blue-600 dark:text-blue-300'
    };
  }
  return {
    label: 'Review fit',
    badge: 'border-amber-500/35 bg-amber-500/10 text-amber-600 dark:text-amber-300'
  };
}

function reviewTone(status: string | null | undefined) {
  if (status === 'approved') {
    return {
      label: 'Approved',
      dot: 'bg-emerald-500',
      hover: 'hover:border-emerald-500/40 hover:bg-emerald-500/[0.035]'
    };
  }
  if (status === 'rejected') {
    return {
      label: 'Rejected',
      dot: 'bg-rose-500',
      hover: 'hover:border-rose-500/40 hover:bg-rose-500/[0.035]'
    };
  }
  return {
    label: 'Pending',
    dot: 'bg-amber-500',
    hover: 'hover:border-amber-500/40 hover:bg-amber-500/[0.035]'
  };
}

function formatWhen(value: string | null) {
  if (!value) return 'Not yet';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return 'Not yet';
  return date.toLocaleString();
}

function hostOf(url: string | null): string {
  if (!url) return 'Not listed';
  return url
    .replace(/^https?:\/\//, '')
    .replace(/^www\./, '')
    .split('/')[0];
}

function LeadLoadingCard() {
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
        Loading lead records…
      </div>
    </div>
  );
}

export default function LeadIntelligence() {
  const [brand, setBrand] = useState<(typeof BRANDS)[number]['id']>('all');
  const [query, setQuery] = useState('');
  const [debouncedQuery, setDebouncedQuery] = useState('');
  const [sort, setSort] = useState<SortKey>('fit');
  const [contact, setContact] = useState<ContactFilter>('all');
  const [pageSize, setPageSize] = useState(DEFAULT_PAGE_SIZE);
  const [leads, setLeads] = useState<Lead[]>([]);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(false);
  const [pageIndex, setPageIndex] = useState(0);
  const [cursorTrail, setCursorTrail] = useState<(string | null)[]>([null]);
  const [resultsOutdated, setResultsOutdated] = useState(false);
  const [status, setStatus] = useState<LeadRefreshStatus | null>(null);
  const [pendingRefresh, setPendingRefresh] = useState(false);
  const [loadingPage, setLoadingPage] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [refreshError, setRefreshError] = useState<string | null>(null);
  const [statusError, setStatusError] = useState<string | null>(null);
  const [draftLead, setDraftLead] = useState<Lead | null>(null);
  const [detailLead, setDetailLead] = useState<Lead | null>(null);
  const [draft, setDraft] = useState<LeadEmailDraft | null>(null);
  const [draftSubject, setDraftSubject] = useState('');
  const [draftBody, setDraftBody] = useState('');
  const [draftError, setDraftError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState(false);
  const requestRef = useRef(0);
  const abortRef = useRef<AbortController | null>(null);
  const failedPageRef = useRef<{ cursor: string | null; pageIndex: number } | null>(null);
  const dialogRequestRef = useRef(0);
  const dialogLeadIdRef = useRef<string | null>(null);
  const statusRef = useRef<LeadRefreshStatus | null>(null);
  const refreshing = pendingRefresh || (Boolean(status?.refreshing) && statusError === null);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      const normalized = query.trim();
      setDebouncedQuery(normalized.length >= 2 ? normalized : '');
    }, 250);
    return () => window.clearTimeout(timer);
  }, [query]);

  const loadPage = useCallback(
    async (cursor: string | null, targetPage: number) => {
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;
      const request = ++requestRef.current;
      setLoadingPage(true);
      setLoadError(null);
      setLeads([]);
      try {
        const page = await listLeads(
          {
            brand_id: brand === 'all' ? undefined : brand,
            search: debouncedQuery || undefined,
            contact,
            sort,
            limit: pageSize,
            cursor: cursor || undefined
          },
          controller.signal
        );
        if (request !== requestRef.current) return;
        setLeads(page.items);
        setNextCursor(page.next_cursor);
        setHasMore(page.has_more);
        setPageIndex(targetPage);
        failedPageRef.current = null;
      } catch (err) {
        if (request !== requestRef.current) return;
        if (!(err instanceof DOMException && err.name === 'AbortError')) {
          failedPageRef.current = { cursor, pageIndex: targetPage };
          setLoadError(err instanceof Error ? err.message : 'Could not load lead records.');
        }
      } finally {
        if (request === requestRef.current) setLoadingPage(false);
      }
    },
    [brand, contact, debouncedQuery, pageSize, sort]
  );

  useEffect(() => {
    setCursorTrail([null]);
    setPageIndex(0);
    setResultsOutdated(false);
    void loadPage(null, 0);
    return () => abortRef.current?.abort();
  }, [loadPage]);

  const reloadCurrentPage = useCallback(() => {
    const cursor = cursorTrail[pageIndex] ?? null;
    void loadPage(cursor, pageIndex);
  }, [cursorTrail, loadPage, pageIndex]);

  const retryPage = () => {
    const failedPage = failedPageRef.current;
    if (failedPage) void loadPage(failedPage.cursor, failedPage.pageIndex);
    else reloadCurrentPage();
  };

  const loadStatus = useCallback(async () => {
    try {
      const next = await getLeadRefreshStatus();
      const previous = statusRef.current;
      const wasRefreshing = previous?.refreshing ?? false;
      const jobsProgressed =
        previous !== null &&
        previous !== undefined &&
        previous.jobs_progress_total !== next.jobs_progress_total;
      const pendingChanged =
        previous !== null && previous !== undefined && previous.pending_jobs !== next.pending_jobs;
      const leadsAdded =
        previous !== null && previous !== undefined && next.updated > previous.updated;
      statusRef.current = next;
      setStatus(next);
      setStatusError(null);
      const listMayHaveChanged =
        leadsAdded ||
        (wasRefreshing && !next.refreshing) ||
        (!next.refreshing && (jobsProgressed || pendingChanged));
      if (listMayHaveChanged) {
        if (pageIndex === 0 && leads.length === 0) void loadPage(null, 0);
        else setResultsOutdated(true);
      }
    } catch (err) {
      setStatusError(err instanceof Error ? err.message : 'Could not check discovery status.');
    }
  }, [leads.length, loadPage, pageIndex]);

  useEffect(() => {
    void loadStatus();
    const timer = window.setInterval(() => void loadStatus(), status?.refreshing ? 2000 : 15000);
    return () => window.clearInterval(timer);
  }, [loadStatus, status?.refreshing]);

  const replaceLead = (updated: Lead, request: number) => {
    setLeads((current) => current.map((item) => (item.id === updated.id ? updated : item)));
    if (request === dialogRequestRef.current && dialogLeadIdRef.current === updated.id)
      setDetailLead(updated);
  };

  const openDraft = async (lead: Lead) => {
    const request = ++dialogRequestRef.current;
    dialogLeadIdRef.current = lead.id;
    setDraftLead(lead);
    setDetailLead(lead);
    setDraft(null);
    setDraftSubject('');
    setDraftBody('');
    setDraftError(null);
    setSent(false);
    setSending(false);
    try {
      const detail = await getLead(lead.id);
      if (request !== dialogRequestRef.current) return;
      replaceLead(detail, request);
      setDetailLead(detail);
      if (
        detail.review_status === 'approved' &&
        detail.outreach_status === 'approved' &&
        (detail.email || detail.public_email)
      ) {
        const emailDraft = await getLeadEmailDraft(lead.id);
        if (request === dialogRequestRef.current) {
          setDraft(emailDraft);
          setDraftSubject(emailDraft.subject);
          setDraftBody(emailDraft.body);
        }
      }
    } catch (err) {
      if (request === dialogRequestRef.current) {
        setDraftError(err instanceof Error ? err.message : 'Could not prepare this email.');
      }
    }
  };

  const sendDraft = async () => {
    if (!draftLead || sending) return;
    const request = dialogRequestRef.current;
    setSending(true);
    setDraftError(null);
    try {
      if (
        !detailLead ||
        detailLead.review_status !== 'approved' ||
        detailLead.outreach_status !== 'approved'
      ) {
        setDraftError('Approve this lead in the review step before sending.');
        return;
      }
      await sendLeadEmail(draftLead.id, {
        subject: draftSubject.trim(),
        body: draftBody.trim()
      });
      if (request === dialogRequestRef.current) setSent(true);
      try {
        const updated = await getLead(draftLead.id);
        replaceLead(updated, request);
        if (request === dialogRequestRef.current) setDetailLead(updated);
      } catch {
        // The send response is authoritative even if the follow-up read fails.
      }
    } catch (err) {
      if (request === dialogRequestRef.current) {
        setDraftError(err instanceof Error ? err.message : 'Could not send this email.');
      }
      try {
        const updated = await getLead(draftLead.id);
        replaceLead(updated, request);
        if (request === dialogRequestRef.current) setDetailLead(updated);
      } catch {
        // Keep the send error visible if the follow-up read also fails.
      }
    } finally {
      if (request === dialogRequestRef.current) setSending(false);
    }
  };

  const runRefresh = async () => {
    setPendingRefresh(true);
    setRefreshError(null);
    try {
      const next = await refreshLeads();
      statusRef.current = next;
      setStatus(next);
      if (!next.refreshing) reloadCurrentPage();
    } catch (err) {
      setRefreshError(err instanceof Error ? err.message : 'Could not start lead discovery.');
    } finally {
      setPendingRefresh(false);
    }
  };

  const refreshResults = () => {
    setResultsOutdated(false);
    setCursorTrail([null]);
    setPageIndex(0);
    void loadPage(null, 0);
  };

  const resetFilters = () => {
    setQuery('');
    setSort('fit');
    setContact('all');
  };

  const goToNextPage = () => {
    if (!hasMore || !nextCursor || loadingPage) return;
    const nextTrail = [...cursorTrail.slice(0, pageIndex + 1), nextCursor];
    setCursorTrail(nextTrail);
    void loadPage(nextCursor, pageIndex + 1);
  };

  const goToPreviousPage = () => {
    if (pageIndex === 0 || loadingPage) return;
    const previousPage = pageIndex - 1;
    void loadPage(cursorTrail[previousPage] ?? null, previousPage);
  };

  const hasFilters = query.trim() !== '' || sort !== 'fit' || contact !== 'all';
  const loadingCompanies = loadingPage;

  return (
    <PageContainer>
      <div className='flex flex-1 flex-col gap-4 pb-12'>
        {/* Header — same language as the other dashboard pages */}
        <div className='flex flex-col justify-between gap-4 pt-2 md:flex-row md:items-end'>
          <div>
            <p className='mb-2 text-[10px] font-extrabold uppercase tracking-[0.13em] text-black dark:text-white'>
              Overture Places discovery
            </p>
            <h1 className='text-[30px] font-semibold tracking-[-0.04em] text-[#09090b] dark:text-white'>
              Lead Intelligence
            </h1>
            <p className='mt-1 max-w-2xl text-[13px] text-[#737373] dark:text-[#a3a3a3]'>
              Evidence-backed companies discovered from Overture Places, verified on public
              websites, and reviewed before outreach.
            </p>
          </div>
          <div className='flex flex-wrap items-center gap-2'>
            {(loadingPage || refreshing) && (
              <span className='inline-flex items-center gap-2 text-xs text-[#737373] dark:text-[#a3a3a3]'>
                <Icons.spinner className='size-3.5 animate-spin' />
                {refreshing ? status?.phase || 'Refreshing source data…' : 'Loading page…'}
              </span>
            )}
            <button
              type='button'
              className={primaryButton}
              onClick={runRefresh}
              disabled={refreshing}
            >
              {refreshing ? (
                <Icons.spinner className='size-3.5 animate-spin' />
              ) : (
                <Icons.search className='size-3.5' />
              )}
              {refreshing ? 'Refreshing…' : 'Refresh discovery'}
            </button>
          </div>
        </div>

        {refreshError && (
          <Card className={`${panelClass} border-red-500/35`} role='alert'>
            <CardHeader>
              <CardTitle className='text-base'>Could not start discovery</CardTitle>
              <CardDescription>{refreshError}</CardDescription>
            </CardHeader>
          </Card>
        )}

        {(statusError || status?.last_error) && (
          <Card className={`${panelClass} border-amber-500/35`} role='status'>
            <CardHeader>
              <CardTitle className='text-base'>
                {statusError ? 'Discovery status unavailable' : 'Discovery needs attention'}
              </CardTitle>
              <CardDescription>
                {statusError
                  ? 'The lead API did not return a status update. Check that the API server is running, then retry discovery.'
                  : status?.last_error}
              </CardDescription>
            </CardHeader>
          </Card>
        )}

        {resultsOutdated && (
          <div
            className={`${panelClass} flex flex-wrap items-center justify-between gap-3 border-amber-500/35 px-4 py-3`}
            role='status'
          >
            <p className='text-sm text-[#525252] dark:text-[#d4d4d4]'>
              Lead scores or contacts changed while you were browsing. Refresh to rebuild the page
              order.
            </p>
            <button
              type='button'
              className={quietButton}
              onClick={refreshResults}
              disabled={loadingPage}
            >
              Refresh results
            </button>
          </div>
        )}

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
                {leads.length} records on this page · Updated{' '}
                {formatWhen(status?.last_scraped_at ?? null)}
                {status?.pending_jobs ? ` · ${status.pending_jobs} website checks queued` : ''}
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
                    placeholder='Company name or website prefix…'
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
              <button
                type='button'
                className={quietButton}
                onClick={resetFilters}
                disabled={!hasFilters}
              >
                Clear
              </button>
            </div>
            <div className='flex flex-col gap-2 border-t border-[#eeeeee] pt-3 sm:flex-row sm:items-center sm:justify-between dark:border-[#2e2e2e]'>
              <p className='text-[11px] text-[#737373] dark:text-[#a3a3a3]'>
                {query.trim().length === 1
                  ? 'Enter at least 2 characters to search by company name or website prefix.'
                  : 'Search and filters run on the database. Only this page is loaded.'}
              </p>
              <label className='flex items-center gap-2 text-[11px] text-[#737373] dark:text-[#a3a3a3]'>
                Rows per page
                <select
                  aria-label='Rows per page'
                  className={`${inputClass} w-[90px]`}
                  value={pageSize}
                  onChange={(event) => setPageSize(Number(event.target.value))}
                >
                  {[25, 40, 75, 100].map((size) => (
                    <option key={size} value={size}>
                      {size}
                    </option>
                  ))}
                </select>
              </label>
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
                Configure the Overture discovery pipeline, then refresh. Lead Intelligence does not
                use a preset company list.
              </CardDescription>
            </CardHeader>
          </Card>
        )}

        {loadError && !loadingPage && (
          <Card className={`${panelClass} border-red-500/35`} role='alert'>
            <CardHeader>
              <CardTitle className='flex items-center gap-2 text-base'>
                <Icons.warning className='size-4 text-red-600' />
                Could not load lead records
              </CardTitle>
              <CardDescription>{loadError}</CardDescription>
              <div className='pt-2'>
                <button type='button' className={quietButton} onClick={retryPage}>
                  Retry
                </button>
              </div>
            </CardHeader>
          </Card>
        )}

        {loadError ? null : leads.length === 0 && !loadingCompanies ? (
          refreshing ? (
            <div className={`${panelClass} border-dashed px-5 py-12 text-center`} role='status'>
              <Icons.spinner className='mx-auto mb-3 size-5 animate-spin text-[#737373]' />
              <p className='text-[15px] font-semibold text-[#09090b] dark:text-white'>
                Overture discovery is still running
              </p>
              <p className='mx-auto mt-1 max-w-md text-[13px] text-[#737373] dark:text-[#a3a3a3]'>
                {status?.phase ||
                  'The first source scan can take several minutes. The page will show real records as soon as they are saved.'}
              </p>
              {typeof status?.pending_jobs === 'number' && status.pending_jobs > 0 && (
                <p className='mt-2 text-xs text-[#737373] dark:text-[#a3a3a3]'>
                  {status.pending_jobs} websites queued for background verification.
                </p>
              )}
            </div>
          ) : (
            <div className={`${panelClass} border-dashed px-5 py-12 text-center`}>
              <span className='mx-auto mb-3 grid size-11 place-items-center rounded-full border border-[#e6e6e6] bg-[#f7f7f7] text-[#404040] dark:border-[#424242] dark:bg-[#242424] dark:text-[#d4d4d4]'>
                <Icons.search className='size-4' />
              </span>
              <p className='text-[15px] font-semibold text-[#09090b] dark:text-white'>
                {hasFilters ? 'No companies match these filters' : 'No companies yet'}
              </p>
              <p className='mx-auto mt-1 max-w-md text-[13px] text-[#737373] dark:text-[#a3a3a3]'>
                {hasFilters
                  ? 'Try clearing the search or choosing a different brand or contact filter.'
                  : 'Refresh to query Overture Places and verify public business websites.'}
              </p>
              <div className='mt-4 flex justify-center gap-2'>
                {!hasFilters ? (
                  <button
                    type='button'
                    className={primaryButton}
                    onClick={runRefresh}
                    disabled={refreshing}
                  >
                    {refreshing ? 'Refreshing…' : 'Refresh discovery'}
                  </button>
                ) : (
                  <button type='button' className={quietButton} onClick={resetFilters}>
                    Clear filters
                  </button>
                )}
              </div>
            </div>
          )
        ) : (
          <div className='grid grid-cols-1 items-start gap-3 md:grid-cols-4 xl:grid-cols-6'>
            {leads.map((lead, index) => {
              const tone = fitTone(lead.fit_score);
              const statusTone = reviewTone(lead.review_status);
              const trailingColumn = leads.length % 3;
              const isLast = index === leads.length - 1;
              const centerAtMedium = isLast && leads.length % 2 === 1 ? ' md:col-start-2' : '';
              const centerAtWide =
                trailingColumn === 1 && isLast
                  ? ' xl:col-start-3'
                  : trailingColumn === 2 && index === leads.length - 2
                    ? ' xl:col-start-2'
                    : trailingColumn === 2 && isLast
                      ? ' xl:col-start-4'
                      : isLast && leads.length % 2 === 1
                        ? ' xl:col-start-auto'
                        : '';
              return (
                <article
                  key={lead.id}
                  className={`${panelClass} p-5 transition-colors ${statusTone.hover} md:col-span-2 xl:col-span-2${centerAtMedium}${centerAtWide}`}
                >
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
                        <p className='mt-0.5 flex min-w-0 items-center gap-1.5 text-[11px] text-[#737373] dark:text-[#a3a3a3]'>
                          {lead.brand_id in BRAND_DOT && (
                            <span className={`size-1.5 rounded-full ${BRAND_DOT[lead.brand_id]}`} />
                          )}
                          <span className='min-w-0 truncate'>
                            {brandLabel(lead.brand_id)} · {lead.country || 'Market not found'}
                          </span>
                          <span className='text-[#b3b3b3] dark:text-[#737373]' aria-hidden='true'>
                            ·
                          </span>
                          <span className='inline-flex flex-none items-center gap-1'>
                            <span
                              className={`size-1.5 rounded-full ${statusTone.dot}`}
                              aria-hidden='true'
                            />
                            {statusTone.label}
                          </span>
                        </p>
                      </div>
                    </div>
                    <div className='flex flex-none items-start'>
                      <span
                        className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-semibold ${tone.badge}`}
                      >
                        {lead.fit_score} · {tone.label.replace(' fit', '')}
                      </span>
                    </div>
                  </div>

                  <p className='mt-3 line-clamp-2 min-h-[42px] text-[13px] leading-[1.6] text-[#404040] dark:text-[#d4d4d4]'>
                    {lead.requirements ||
                      lead.why ||
                      'Public page did not expose a clear requirement yet.'}
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
                        <span
                          className='min-w-0 truncate text-[#404040] dark:text-[#d4d4d4]'
                          title={lead.email}
                        >
                          {lead.email}
                        </span>
                      ) : (
                        <span className='text-[#a3a3a3]'>—</span>
                      )}
                    </div>
                    <div className='flex items-center justify-between gap-3 px-3 py-2'>
                      <span className='flex-none text-[#737373] dark:text-[#a3a3a3]'>Phone</span>
                      {lead.phone ? (
                        <span className='min-w-0 truncate text-[#404040] dark:text-[#d4d4d4]'>
                          {lead.phone}
                        </span>
                      ) : (
                        <span className='text-[#a3a3a3]'>—</span>
                      )}
                    </div>
                    <div className='flex items-center justify-between gap-3 px-3 py-2'>
                      <span className='flex-none text-[#737373] dark:text-[#a3a3a3]'>
                        Contact readiness
                      </span>
                      <span className='font-medium capitalize text-[#404040] dark:text-[#d4d4d4]'>
                        {(lead.contact_status || 'unknown').replaceAll('_', ' ')}
                      </span>
                    </div>
                    <div className='flex items-center justify-between gap-3 px-3 py-2'>
                      <span className='flex-none text-[#737373] dark:text-[#a3a3a3]'>
                        Branches / evidence
                      </span>
                      <span className='font-medium text-[#404040] dark:text-[#d4d4d4]'>
                        {lead.location_count || lead.locations?.length || 0} /{' '}
                        {lead.evidence_count ?? lead.evidence?.length ?? 0}
                      </span>
                    </div>
                  </div>

                  {lead.score_version && (
                    <div className='mt-3 text-[11px] text-[#737373] dark:text-[#a3a3a3]'>
                      Score {lead.score_version}
                    </div>
                  )}

                  {lead.score_breakdown && Object.keys(lead.score_breakdown).length > 0 && (
                    <details className='mt-3 text-[11px] text-[#737373] dark:text-[#a3a3a3]'>
                      <summary className='cursor-pointer font-semibold text-[#404040] dark:text-[#d4d4d4]'>
                        Fit score breakdown
                      </summary>
                      <div className='mt-2 grid grid-cols-2 gap-x-3 gap-y-1'>
                        {Object.entries(lead.score_breakdown).map(([key, value]) => (
                          <span key={key} className='truncate' title={String(value)}>
                            {key.replaceAll('_', ' ')}:{' '}
                            {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                          </span>
                        ))}
                      </div>
                    </details>
                  )}

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
                      <a
                        className={`${quietButton} flex-1`}
                        href={lead.url}
                        target='_blank'
                        rel='noreferrer'
                      >
                        Open site
                        <Icons.externalLink className='size-3.5' />
                      </a>
                    ) : (
                      <button type='button' className={quietButton} disabled style={{ flex: 1 }}>
                        No site
                      </button>
                    )}
                    {lead.outreach_status === 'sent' || lead.outreach_status === 'sending' ? (
                      <button type='button' className={primaryButton} style={{ flex: 1 }} disabled>
                        {lead.outreach_status === 'sending' ? (
                          <Icons.spinner className='size-3.5 animate-spin' />
                        ) : (
                          <Icons.check className='size-3.5' />
                        )}
                        {lead.outreach_status === 'sending' ? 'Sending…' : 'Sent'}
                      </button>
                    ) : lead.outreach_status !== 'delivery_uncertain' &&
                      !(
                        lead.review_status === 'approved' && lead.outreach_status === 'approved'
                      ) ? (
                      <Link
                        className={primaryButton}
                        style={{ flex: 1 }}
                        href={`/dashboard/leads/${encodeURIComponent(lead.id)}`}
                        title='Open the lead evidence and review page'
                      >
                        <Icons.check className='size-3.5' />
                        {lead.outreach_status === 'send_failed' ? 'Review again' : 'Review lead'}
                      </Link>
                    ) : (
                      <button
                        type='button'
                        className={primaryButton}
                        style={{ flex: 1 }}
                        onClick={() => void openDraft(lead)}
                        title={
                          lead.email ? `Review email for ${lead.email}` : 'Review email delivery'
                        }
                      >
                        <Icons.send className='size-3.5' />
                        {lead.outreach_status === 'delivery_uncertain'
                          ? 'Check delivery'
                          : 'Send mail'}
                      </button>
                    )}
                  </div>
                </article>
              );
            })}
            {(loadingPage || (refreshing && leads.length === 0)) &&
              Array.from({ length: 9 }, (_, index) => <LeadLoadingCard key={`loading-${index}`} />)}
          </div>
        )}

        {leads.length > 0 && !loadError && (
          <nav
            className={`${panelClass} flex flex-wrap items-center justify-between gap-3 px-4 py-3`}
            aria-label='Lead pages'
          >
            <span className='text-xs text-[#737373] dark:text-[#a3a3a3]'>
              Page {pageIndex + 1} · {leads.length} records ·{' '}
              {hasMore ? 'more results available' : 'end of results'}
            </span>
            <div className='flex items-center gap-2'>
              <button
                type='button'
                className={quietButton}
                onClick={goToPreviousPage}
                disabled={pageIndex === 0 || loadingPage || resultsOutdated}
              >
                Previous
              </button>
              <button
                type='button'
                className={primaryButton}
                onClick={goToNextPage}
                disabled={!hasMore || loadingPage || resultsOutdated}
              >
                {loadingPage && pageIndex > 0 ? (
                  <Icons.spinner className='size-3.5 animate-spin' />
                ) : null}
                Next page
              </button>
            </div>
          </nav>
        )}
      </div>

      <Dialog
        open={draftLead !== null}
        onOpenChange={(open) => {
          if (!open) {
            dialogRequestRef.current += 1;
            dialogLeadIdRef.current = null;
            setDraftLead(null);
            setDetailLead(null);
            setDraft(null);
            setDraftSubject('');
            setDraftBody('');
            setDraftError(null);
            setSent(false);
            setSending(false);
          }
        }}
      >
        <DialogContent className='max-h-[calc(100dvh-2rem)] w-[92vw] max-w-[min(92vw,920px)] overflow-y-auto sm:max-w-[min(92vw,920px)]'>
          <DialogHeader>
            <DialogTitle>
              {detailLead?.outreach_status === 'delivery_uncertain'
                ? 'Check email delivery'
                : 'Review and send email'}
            </DialogTitle>
            <DialogDescription>
              {draftLead ? (
                <>
                  {draftLead.name} · {draftLead.email || 'no published email'} · Fit{' '}
                  {draftLead.fit_score}
                </>
              ) : (
                'From your Gmail account to the address on this lead.'
              )}
            </DialogDescription>
          </DialogHeader>
          {detailLead?.outreach_status === 'delivery_uncertain' && (
            <p className='rounded-md border border-amber-500/35 bg-amber-500/10 p-3 text-sm text-amber-800 dark:text-amber-200'>
              Email delivery could not be confirmed. Check the sender&apos;s Sent folder before
              taking further action.
            </p>
          )}
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
              </div>
              <label
                htmlFor='lead-email-subject-list'
                className='block space-y-1.5 text-xs font-medium'
              >
                <span>Subject</span>
                <input
                  id='lead-email-subject-list'
                  className={`${inputClass} text-sm`}
                  aria-label='Email subject'
                  value={draftSubject}
                  onChange={(event) => setDraftSubject(event.target.value)}
                  maxLength={998}
                />
              </label>
              <label
                htmlFor='lead-email-body-list'
                className='block space-y-1.5 text-xs font-medium'
              >
                <span>Message</span>
                <Textarea
                  id='lead-email-body-list'
                  aria-label='Email message'
                  value={draftBody}
                  onChange={(event) => setDraftBody(event.target.value)}
                  maxLength={100000}
                  className='h-[min(45dvh,32rem)] min-h-40 resize-y text-sm leading-6'
                />
              </label>
              {!draft.configured && (
                <p className='text-sm text-destructive'>
                  Gmail does not use an API key. Add GMAIL_APP_PASSWORD to .env. Create it at
                  myaccount.google.com/apppasswords for {draft.from_email}.
                </p>
              )}
            </div>
          ) : detailLead?.outreach_status === 'delivery_uncertain' ? (
            <p className='text-sm text-muted-foreground'>
              A further send is locked until delivery is checked manually.
            </p>
          ) : detailLead?.review_status === 'approved' ? (
            <p className='text-sm text-muted-foreground'>
              This lead is approved, but no published email is available yet.
            </p>
          ) : (
            <p className='text-sm text-muted-foreground'>Preparing the lead details…</p>
          )}
          {draftError && <p className='text-sm text-destructive'>{draftError}</p>}
          {sent && (
            <p className='text-sm'>
              Sent from {draft?.from_email} to {draft?.to_email}.
            </p>
          )}
          <DialogFooter>
            <Button
              type='button'
              variant='outline'
              onClick={() => {
                setDraftLead(null);
                setDetailLead(null);
                setDraft(null);
                setDraftSubject('');
                setDraftBody('');
                setDraftError(null);
                setSent(false);
              }}
            >
              Cancel
            </Button>
            <Button
              type='button'
              onClick={() => void sendDraft()}
              disabled={
                !draft?.configured ||
                sending ||
                sent ||
                detailLead?.outreach_status !== 'approved' ||
                !draftSubject.trim() ||
                /[\r\n]/.test(draftSubject) ||
                !draftBody.trim()
              }
            >
              {sending ? 'Sending…' : sent ? 'Sent' : 'Send email'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </PageContainer>
  );
}
