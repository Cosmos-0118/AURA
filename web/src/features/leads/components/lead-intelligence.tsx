'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Icons } from '@/components/icons';
import PageContainer from '@/components/layout/page-container';
import { Badge } from '@/components/ui/badge';
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

function formatWhen(value: string | null) {
  if (!value) return 'Not yet';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return 'Not yet';
  return date.toLocaleString();
}

function LeadLoadingCard({ label }: { label: string }) {
  return (
    <Card className='border-primary/30' aria-busy='true' aria-live='polite'>
      <CardHeader>
        <CardTitle className='flex items-center gap-2 text-base'>
          <Icons.spinner className='size-4 animate-spin text-primary' />
          {label}
        </CardTitle>
        <CardDescription>The next company will appear in this card.</CardDescription>
      </CardHeader>
      <CardContent className='space-y-3'>
        <Skeleton className='h-5 w-16' />
        <Skeleton className='h-3 w-full' />
        <Skeleton className='h-3 w-11/12' />
        <Skeleton className='h-3 w-2/3' />
        <div className='h-1 overflow-hidden rounded-full bg-muted'>
          <div className='h-full w-1/3 animate-pulse rounded-full bg-primary' />
        </div>
      </CardContent>
    </Card>
  );
}

export default function LeadIntelligence() {
  const [brand, setBrand] = useState<(typeof BRANDS)[number]['id']>('all');
  const [leads, setLeads] = useState<Lead[]>([]);
  const [shown, setShown] = useState<Lead[]>([]);
  const [status, setStatus] = useState<LeadRefreshStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [draftLead, setDraftLead] = useState<Lead | null>(null);
  const [draft, setDraft] = useState<LeadEmailDraft | null>(null);
  const [draftError, setDraftError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState(false);
  const [queued, setQueued] = useState(0);
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
      setLeads(rows);
      setStatus(refresh);
      if (!refresh.refreshing) setPending(false);
      setError(null);
    } catch (err) {
      if (request !== requestRef.current) return;
      setError(err instanceof Error ? err.message : 'Could not load leads.');
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
      seededRef.current = true;
      seenRef.current = new Set(leads.map((lead) => lead.id));
      queueRef.current = [];
      setQueued(0);
      setShown(leads);
      return;
    }
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
  }, [leads, brand, refreshing, status]);

  useEffect(() => {
    const timer = window.setInterval(() => {
      const next = queueRef.current.shift();
      if (!next) return;
      setQueued(queueRef.current.length);
      setShown((current) => (current.some((item) => item.id === next.id) ? current : [...current, next]));
    }, 450);
    return () => window.clearInterval(timer);
  }, []);

  const awaiting = status === null && !error;
  const loadingCompanies = refreshing || queued > 0 || awaiting;

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

  const average = useMemo(() => {
    if (!shown.length) return 0;
    return Math.round(shown.reduce((sum, lead) => sum + lead.fit_score, 0) / shown.length);
  }, [shown]);

  return (
    <PageContainer>
      <div className='flex flex-1 flex-col space-y-6 pb-12'>
        <div className='flex flex-col justify-between gap-4 md:flex-row md:items-center'>
          <div>
            <div className='flex items-center gap-2'>
              <h1 className='text-3xl font-bold tracking-tight'>Lead Intelligence</h1>
              <Badge variant='outline' className='border-primary/40 bg-primary/10 text-primary'>
                Daily refresh
              </Badge>
            </div>
            <p className='mt-1 text-sm text-muted-foreground'>
              Companies and public posts are found by searching the web for each product. Cards show
              the site, requirements, and any published email or phone.
            </p>
          </div>
          <Button
            type='button'
            variant='outline'
            onClick={() => {
              setPending(true);
              seenRef.current = new Set();
              queueRef.current = [];
              setQueued(0);
              setShown([]);
              setLeads([]);
              void refreshLeads().then(() => load());
            }}
            disabled={refreshing}
          >
            {refreshing ? <Icons.spinner className='size-4 animate-spin' /> : <Icons.search className='size-4' />}
            {refreshing ? 'Refreshing…' : 'Refresh now'}
          </Button>
        </div>

        <div className='flex flex-wrap items-center gap-2'>
          {BRANDS.map((item) => (
            <Button
              key={item.id}
              type='button'
              size='sm'
              variant={brand === item.id ? 'default' : 'outline'}
              onClick={() => setBrand(item.id)}
            >
              {item.label}
            </Button>
          ))}
          <Badge variant='secondary'>Last update {formatWhen(status?.last_scraped_at ?? null)}</Badge>
          <Badge variant='outline'>Average fit {average}</Badge>
          {loadingCompanies && (
            <Badge variant='outline' className='border-primary/40 text-primary'>
              <Icons.spinner className='size-3 animate-spin' />
              Loading companies
            </Badge>
          )}
        </div>

        {status && status.configured === false && (
          <Card>
            <CardHeader>
              <CardTitle className='text-base'>Discovery is not configured</CardTitle>
              <CardDescription>
                Add TinyFish_API_KEY to the project .env, then refresh. Lead Intelligence does not
                use a preset company list.
              </CardDescription>
            </CardHeader>
          </Card>
        )}

        {error && <p className='text-sm text-destructive'>{error}</p>}
        {status?.last_error && (
          <p className='text-sm text-destructive'>Discovery: {status.last_error}</p>
        )}

        {shown.length === 0 && !loadingCompanies ? (
          <Card>
            <CardHeader>
              <CardTitle className='text-base'>No companies yet</CardTitle>
              <CardDescription>
                Refresh to search the web. Each company card appears as soon as its public page is
                read.
              </CardDescription>
            </CardHeader>
          </Card>
        ) : (
          <div className='grid gap-4 md:grid-cols-2 xl:grid-cols-3'>
            {shown.map((lead) => (
              <Card key={lead.id} className='animate-in fade-in slide-in-from-bottom-2 duration-500'>
                <CardHeader>
                  <CardTitle className='text-base'>{lead.name}</CardTitle>
                  <CardDescription>
                    {lead.country || 'Country not on the page'} · {lead.brand_id}
                  </CardDescription>
                </CardHeader>
                <CardContent className='space-y-3'>
                  <Badge variant='outline'>Fit {lead.fit_score}</Badge>
                  <div>
                    <p className='text-xs font-medium uppercase tracking-wide text-muted-foreground'>
                      Requirements
                    </p>
                    <p className='mt-1 text-sm leading-relaxed'>{lead.requirements || lead.why}</p>
                  </div>
                  <div className='space-y-1 text-sm'>
                    <p>
                      <span className='text-muted-foreground'>Website </span>
                      {lead.url ? (
                        <a className='font-medium text-primary underline-offset-4 hover:underline' href={lead.url} target='_blank' rel='noreferrer'>
                          {lead.url.replace(/^https?:\/\//, '')}
                        </a>
                      ) : (
                        'Not listed'
                      )}
                    </p>
                    <p>
                      <span className='text-muted-foreground'>Email </span>
                      {lead.email || 'Not published on the site'}
                    </p>
                    <p>
                      <span className='text-muted-foreground'>Phone </span>
                      {lead.phone || 'Not published on the site'}
                    </p>
                    {lead.source_url && (
                      <p>
                        <span className='text-muted-foreground'>Found from </span>
                        <a
                          className='font-medium text-primary underline-offset-4 hover:underline'
                          href={lead.source_url}
                          target='_blank'
                          rel='noreferrer'
                        >
                          {lead.source_title || lead.source_url.replace(/^https?:\/\//, '')}
                        </a>
                      </p>
                    )}
                  </div>
                  <Button type='button' size='sm' disabled={!lead.email} onClick={() => void openDraft(lead)}>
                    <Icons.send className='size-4' />
                    Send email
                  </Button>
                </CardContent>
              </Card>
            ))}
            {loadingCompanies &&
              Array.from({ length: shown.length === 0 ? 3 : 1 }, (_, index) => (
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
            <DialogTitle>Send email</DialogTitle>
            <DialogDescription>
              From your Gmail account to the address on this lead.
            </DialogDescription>
          </DialogHeader>
          {draft ? (
            <div className='space-y-3'>
              <p className='text-sm'>
                <span className='text-muted-foreground'>From </span>
                {draft.from_email}
              </p>
              <p className='text-sm'>
                <span className='text-muted-foreground'>To </span>
                {draft.to_email}
              </p>
              <p className='text-sm'>
                <span className='text-muted-foreground'>Subject </span>
                {draft.subject}
              </p>
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
            <Button type='button' onClick={() => void sendDraft()} disabled={!draft?.configured || sending || sent}>
              {sending ? 'Sending…' : sent ? 'Sent' : 'Send'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </PageContainer>
  );
}
