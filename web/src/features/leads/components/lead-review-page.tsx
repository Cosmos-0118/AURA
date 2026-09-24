'use client';

import Link from 'next/link';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Icons } from '@/components/icons';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { getLead, getLeadEmailDraft, reviewLead, sendLeadEmail } from '@/lib/api/client';
import type { Lead, LeadEmailDraft, LeadReviewRequest } from '@/lib/api/types';

function brandLabel(brand: string) {
  if (brand === 'doctorshield') return 'DoctorShield';
  if (brand === 'jaguar') return 'Jaguar Transit';
  if (brand === 'jade') return 'Jade';
  return brand;
}

function readable(value: string | null | undefined, fallback = 'Not available') {
  return value?.trim() || fallback;
}

function labelize(value: string) {
  return value.replaceAll('_', ' ').replace(/\b\w/g, (character) => character.toUpperCase());
}

function formatDate(value: string | null | undefined) {
  if (!value) return 'Not recorded';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? 'Not recorded' : date.toLocaleString();
}

function safeHttpUrl(value: string | null | undefined) {
  if (!value) return null;
  try {
    const url = new URL(value);
    return url.protocol === 'https:' || url.protocol === 'http:' ? url.toString() : null;
  } catch {
    return null;
  }
}

function scoreTone(score: number) {
  if (score >= 85)
    return 'border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300';
  if (score >= 70) return 'border-blue-500/30 bg-blue-500/10 text-blue-700 dark:text-blue-300';
  return 'border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-300';
}

function reviewStatusTone(status: string | undefined) {
  if (status === 'approved')
    return {
      badge: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300',
      hover: 'hover:border-emerald-500/40 hover:bg-emerald-500/[0.035]',
      label: 'Approved'
    };
  if (status === 'rejected')
    return {
      badge: 'border-rose-500/30 bg-rose-500/10 text-rose-700 dark:text-rose-300',
      hover: 'hover:border-rose-500/40 hover:bg-rose-500/[0.035]',
      label: 'Rejected'
    };
  return {
    badge: 'border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-300',
    hover: 'hover:border-amber-500/40 hover:bg-amber-500/[0.035]',
    label: 'Pending'
  };
}

function contactStatusLabel(value: string | undefined) {
  switch (value) {
    case 'hunter_verified':
      return 'Hunter verified';
    case 'mx_valid':
      return 'Email domain has MX records';
    case 'unverified':
      return 'Email found, not verified';
    case 'phone_only':
      return 'Phone only';
    default:
      return 'No usable contact found';
  }
}

function evidenceSource(value: string) {
  if (value === 'overture_maps') return 'Overture Maps';
  if (value === 'company_website' || value === 'website') return 'Company website';
  if (value.startsWith('hunter')) return 'Hunter';
  return labelize(value || 'Source not recorded');
}

function isTerminalOutreach(value: string | undefined) {
  return value === 'sent' || value === 'sending' || value === 'delivery_uncertain';
}

function FieldValue({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className='min-w-0'>
      <p className='text-xs font-medium text-muted-foreground'>{label}</p>
      <div className='mt-1 break-words text-sm text-foreground'>{children}</div>
    </div>
  );
}

export default function LeadReviewPage({ leadId }: { leadId: string }) {
  const currentLeadId = useRef(leadId);
  currentLeadId.current = leadId;
  const [lead, setLead] = useState<Lead | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionNotice, setActionNotice] = useState<string | null>(null);
  const [reviewDialogOpen, setReviewDialogOpen] = useState(false);
  const [emailDialogOpen, setEmailDialogOpen] = useState(false);
  const [reviewer, setReviewer] = useState('local-user');
  const [reviewNote, setReviewNote] = useState('');
  const [reviewing, setReviewing] = useState(false);
  const [sending, setSending] = useState(false);
  const [sendReconciliationRequired, setSendReconciliationRequired] = useState(false);
  const [refreshingSendStatus, setRefreshingSendStatus] = useState(false);
  const [sentTo, setSentTo] = useState<string | null>(null);
  const [draft, setDraft] = useState<LeadEmailDraft | null>(null);
  const [draftLoading, setDraftLoading] = useState(false);
  const [draftError, setDraftError] = useState<string | null>(null);
  const [draftRetry, setDraftRetry] = useState(0);
  const [emailSubject, setEmailSubject] = useState('');
  const [emailBody, setEmailBody] = useState('');
  const draftEmailAddress =
    lead?.review_status === 'approved' && lead.outreach_status === 'approved'
      ? lead.email || lead.public_email || null
      : null;
  const draftLeadId = draftEmailAddress ? (lead?.id ?? null) : null;

  const loadLead = useCallback(
    async (signal?: AbortSignal) => {
      setLoading(true);
      setLoadError(null);
      try {
        const result = await getLead(leadId, signal);
        if (!signal?.aborted) setLead(result);
      } catch (error) {
        if (!signal?.aborted)
          setLoadError(error instanceof Error ? error.message : 'Could not load this lead.');
      } finally {
        if (!signal?.aborted) setLoading(false);
      }
    },
    [leadId]
  );

  useEffect(() => {
    const controller = new AbortController();
    setLead(null);
    setDraft(null);
    setEmailSubject('');
    setEmailBody('');
    setActionError(null);
    setActionNotice(null);
    setReviewDialogOpen(false);
    setEmailDialogOpen(false);
    setReviewing(false);
    setSending(false);
    setRefreshingSendStatus(false);
    setSentTo(null);
    setSendReconciliationRequired(false);
    void loadLead(controller.signal);
    return () => controller.abort();
  }, [loadLead]);

  useEffect(() => {
    if (!draftLeadId) {
      setDraft(null);
      setDraftLoading(false);
      setDraftError(null);
      return;
    }

    let active = true;
    setDraft(null);
    setDraftError(null);
    setDraftLoading(true);
    getLeadEmailDraft(draftLeadId)
      .then((result) => {
        if (active) {
          setDraft(result);
          setEmailSubject(result.subject);
          setEmailBody(result.body);
        }
      })
      .catch((error: unknown) => {
        if (active)
          setDraftError(
            error instanceof Error ? error.message : 'Could not prepare the email draft.'
          );
      })
      .finally(() => {
        if (active) setDraftLoading(false);
      });
    return () => {
      active = false;
    };
  }, [draftEmailAddress, draftLeadId, draftRetry]);

  const scoreFactors = useMemo(
    () =>
      Object.entries(lead?.score_breakdown ?? {})
        .filter((entry): entry is [string, number] => typeof entry[1] === 'number')
        .filter(([key]) => key !== 'version'),
    [lead?.score_breakdown]
  );

  const scoreMatches = useMemo(() => {
    const matches = lead?.score_breakdown?.matches;
    return Array.isArray(matches)
      ? matches.filter((value): value is string => typeof value === 'string')
      : [];
  }, [lead?.score_breakdown]);

  const canApprove = lead?.status === 'qualified' && lead.stage === 'qualified';
  const alreadyApproved = lead?.review_status === 'approved' && lead.outreach_status === 'approved';
  const outreachBlocked = isTerminalOutreach(lead?.outreach_status);
  const emailAddress = lead?.email || lead?.public_email || null;
  const reviewTone = reviewStatusTone(lead?.review_status);

  const submitDecision = async (decision: LeadReviewRequest['decision']) => {
    if (!lead || reviewing || sending || !reviewer.trim()) return;
    const actionLeadId = lead.id;
    setReviewing(true);
    setActionError(null);
    setActionNotice(null);
    try {
      const updated = await reviewLead(lead.id, {
        decision,
        reviewer: reviewer.trim(),
        note: reviewNote.trim() || undefined
      });
      if (currentLeadId.current !== actionLeadId) return;
      setLead(updated);
      setReviewNote('');
      setActionNotice(
        decision === 'approved'
          ? emailAddress
            ? 'Approved for outreach. Open Outreach email to review the message before sending.'
            : 'Approved for outreach. No public email is available, so nothing can be sent yet.'
          : 'Lead rejected. It will not be eligible for outreach.'
      );
    } catch (error) {
      if (currentLeadId.current !== actionLeadId) return;
      setActionError(
        error instanceof Error ? error.message : 'Could not save the review decision.'
      );
    } finally {
      if (currentLeadId.current === actionLeadId) setReviewing(false);
    }
  };

  const sendEmail = async () => {
    if (!lead || !draft?.configured || sending || sendReconciliationRequired || !alreadyApproved)
      return;
    const actionLeadId = lead.id;
    setSending(true);
    setActionError(null);
    setActionNotice(null);
    try {
      const result = await sendLeadEmail(lead.id, {
        subject: emailSubject.trim(),
        body: emailBody.trim()
      });
      if (currentLeadId.current !== actionLeadId) return;
      setSentTo(result.to_email);
      const updated = await getLead(actionLeadId).catch(() => null);
      if (updated && currentLeadId.current === actionLeadId) setLead(updated);
    } catch (error) {
      if (currentLeadId.current !== actionLeadId) return;
      setActionError(error instanceof Error ? error.message : 'Could not send this email.');
      const updated = await getLead(actionLeadId).catch(() => null);
      if (currentLeadId.current !== actionLeadId) return;
      if (updated) {
        setLead(updated);
        setSendReconciliationRequired(false);
      } else {
        setSendReconciliationRequired(true);
      }
    } finally {
      if (currentLeadId.current === actionLeadId) setSending(false);
    }
  };

  const refreshSendStatus = async () => {
    if (!lead || refreshingSendStatus) return;
    const actionLeadId = lead.id;
    setRefreshingSendStatus(true);
    try {
      const updated = await getLead(actionLeadId);
      if (currentLeadId.current !== actionLeadId) return;
      setLead(updated);
      setSendReconciliationRequired(false);
      setActionError(null);
    } catch (error) {
      if (currentLeadId.current !== actionLeadId) return;
      setActionError(error instanceof Error ? error.message : 'Could not refresh the send status.');
    } finally {
      if (currentLeadId.current === actionLeadId) setRefreshingSendStatus(false);
    }
  };

  const leadUrl = safeHttpUrl(lead?.url);
  const locations = lead?.locations ?? [];
  const evidence = lead?.evidence ?? [];
  const contacts = lead?.contacts ?? [];
  const qualifiedLabel =
    lead?.status === 'qualified' && lead.stage === 'qualified'
      ? 'Qualified'
      : labelize(lead?.stage || 'discovered');

  return (
    <main className='mx-auto flex w-full max-w-[1440px] flex-col gap-5 px-4 pb-16 pt-6 sm:px-6 lg:px-8 xl:px-12'>
      <div className='flex flex-wrap items-center justify-between gap-3'>
        <div className='flex items-center gap-2 text-sm text-muted-foreground'>
          <Link
            href='/dashboard/leads'
            className='inline-flex items-center gap-1.5 transition hover:text-foreground'
          >
            <Icons.chevronLeft className='size-4' /> All leads
          </Link>
          <span aria-hidden='true'>/</span>
          <span className='text-foreground'>Review</span>
        </div>
        <Button
          variant='outline'
          size='sm'
          onClick={() => void loadLead()}
          disabled={loading || reviewing || sending}
        >
          <Icons.refresh className='mr-1.5 size-4' /> Refresh details
        </Button>
      </div>

      {loading ? (
        <div className='grid gap-4'>
          <Card className='animate-pulse p-6'>
            <div className='h-7 w-2/5 rounded bg-muted' />
            <div className='mt-4 h-4 w-3/5 rounded bg-muted' />
            <div className='mt-8 h-48 rounded bg-muted' />
          </Card>
        </div>
      ) : loadError || !lead ? (
        <Card className='border-destructive/30 p-8 text-center' role='alert'>
          <Icons.warning className='mx-auto mb-3 size-6 text-destructive' />
          <h1 className='text-lg font-semibold'>Could not load this lead</h1>
          <p className='mx-auto mt-1 max-w-xl text-sm text-muted-foreground'>
            {loadError || 'This lead may have been removed.'}
          </p>
          <Button className='mt-4' variant='outline' onClick={() => void loadLead()}>
            Try again
          </Button>
        </Card>
      ) : (
        <>
          <Card className={`overflow-hidden transition-colors ${reviewTone.hover}`}>
            <CardContent className='flex flex-col gap-6 p-5 sm:p-7 lg:flex-row lg:items-center lg:justify-between'>
              <div className='min-w-0'>
                <div className='mb-3 flex flex-wrap items-center gap-2'>
                  <Badge variant='outline'>{brandLabel(lead.brand_id)}</Badge>
                  <Badge variant='outline' className={scoreTone(lead.fit_score)}>
                    {qualifiedLabel}
                  </Badge>
                  <Badge variant='outline' className={`gap-1.5 ${reviewTone.badge}`}>
                    <span className='size-1.5 rounded-full bg-current' aria-hidden='true' />
                    {reviewTone.label}
                  </Badge>
                </div>
                <h1 className='break-words text-3xl font-semibold tracking-tight text-foreground sm:text-4xl'>
                  {lead.name}
                </h1>
                <p className='mt-2 max-w-3xl text-sm leading-6 text-muted-foreground'>
                  {readable(
                    lead.why,
                    'Review the public evidence and confirm whether this business fits the selected AURA brand.'
                  )}
                </p>
                <div className='mt-4 flex flex-wrap gap-x-5 gap-y-2 text-sm text-muted-foreground'>
                  <span>{readable(lead.category, 'Category not listed')}</span>
                  <span>
                    {[lead.location, lead.country].filter(Boolean).join(', ') ||
                      'Location not listed'}
                  </span>
                  {lead.domain && <span>{lead.domain}</span>}
                </div>
              </div>
              <div className='w-full rounded-xl border bg-muted/30 p-4 lg:max-w-[260px] lg:flex-none'>
                <div className='flex items-end justify-between gap-4'>
                  <div>
                    <p className='text-xs font-medium uppercase tracking-wide text-muted-foreground'>
                      Fit score
                    </p>
                    <p className='mt-1 text-4xl font-semibold tabular-nums'>
                      {lead.fit_score}
                      <span className='ml-1 text-base font-normal text-muted-foreground'>
                        / 100
                      </span>
                    </p>
                  </div>
                  <Icons.circleCheck
                    className='mb-1 size-7 text-muted-foreground'
                    aria-hidden='true'
                  />
                </div>
                <div className='mt-3 h-2 overflow-hidden rounded-full bg-muted'>
                  <div
                    className='h-full rounded-full bg-foreground transition-all'
                    style={{ width: `${Math.max(0, Math.min(100, lead.fit_score))}%` }}
                  />
                </div>
                <p className='mt-2 text-xs text-muted-foreground'>
                  Calculated from source category, website fit, location, and contact evidence.
                </p>
              </div>
            </CardContent>
          </Card>

          <div className='grid items-start gap-5'>
            <div className='grid min-w-0 gap-5'>
              <Card>
                <CardHeader className='pb-4'>
                  <CardTitle className='text-base'>Company overview</CardTitle>
                  <CardDescription>
                    Public company details and the source fields used to identify this lead.
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className='grid gap-x-8 gap-y-5 sm:grid-cols-2 lg:grid-cols-3'>
                    <FieldValue label='Website'>
                      {leadUrl ? (
                        <a
                          className='inline-flex items-center gap-1.5 font-medium underline decoration-border underline-offset-4 hover:text-primary'
                          href={leadUrl}
                          target='_blank'
                          rel='noreferrer'
                        >
                          {lead.domain || new URL(leadUrl).hostname}
                          <Icons.externalLink className='size-3.5' />
                        </a>
                      ) : (
                        readable(lead.domain)
                      )}
                    </FieldValue>
                    <FieldValue label='Business category'>{readable(lead.category)}</FieldValue>
                    <FieldValue label='Location'>
                      {[lead.location, lead.country].filter(Boolean).join(', ') || 'Not listed'}
                    </FieldValue>
                    <FieldValue label='Operating status'>
                      {labelize(lead.operating_status || 'not provided')}
                    </FieldValue>
                    <FieldValue label='Overture confidence'>
                      {lead.overture_confidence == null
                        ? 'Not provided'
                        : `${Math.round(lead.overture_confidence * 100)}%`}
                    </FieldValue>
                    <FieldValue label='Source release'>{readable(lead.source_release)}</FieldValue>
                  </div>
                  {lead.description && (
                    <p className='mt-5 border-t pt-4 text-sm leading-6 text-muted-foreground'>
                      {lead.description}
                    </p>
                  )}
                </CardContent>
              </Card>

              <Card>
                <CardHeader className='pb-4'>
                  <CardTitle className='text-base'>Fit assessment</CardTitle>
                  <CardDescription>
                    Signals behind the score. Use the linked evidence below to verify the match.
                  </CardDescription>
                </CardHeader>
                <CardContent className='space-y-5'>
                  <p className='text-sm leading-6'>
                    {readable(lead.why, 'No fit explanation was recorded.')}
                  </p>
                  {scoreMatches.length > 0 && (
                    <div className='flex flex-wrap gap-2'>
                      {scoreMatches.map((match) => (
                        <Badge key={match} variant='secondary'>
                          {match}
                        </Badge>
                      ))}
                    </div>
                  )}
                  {scoreFactors.length > 0 && (
                    <div className='grid gap-2 border-t pt-4 sm:grid-cols-2'>
                      {scoreFactors.map(([key, value]) => (
                        <div key={key} className='flex items-center justify-between gap-3 text-sm'>
                          <span className='text-muted-foreground'>{labelize(key)}</span>
                          <span className='font-medium tabular-nums'>
                            {value > 0 ? `+${value}` : value}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>

              <Card>
                <CardHeader className='pb-4'>
                  <CardTitle className='text-base'>Contacts</CardTitle>
                  <CardDescription>
                    Reachability and contact details currently supported by evidence.
                  </CardDescription>
                </CardHeader>
                <CardContent className='space-y-5'>
                  <div className='grid gap-4 sm:grid-cols-2'>
                    <FieldValue label='Public email'>
                      {emailAddress ? (
                        <a
                          className='underline decoration-border underline-offset-4 hover:text-primary'
                          href={`mailto:${emailAddress}`}
                        >
                          {emailAddress}
                        </a>
                      ) : (
                        'No public email found'
                      )}
                    </FieldValue>
                    <FieldValue label='Phone'>
                      {lead.phone ? (
                        <a
                          className='underline decoration-border underline-offset-4 hover:text-primary'
                          href={`tel:${lead.phone}`}
                        >
                          {lead.phone}
                        </a>
                      ) : (
                        'No phone listed'
                      )}
                    </FieldValue>
                    <FieldValue label='Contact readiness'>
                      {contactStatusLabel(lead.contact_status)}
                    </FieldValue>
                    <FieldValue label='Last checked'>
                      {formatDate(lead.last_verified_at)}
                    </FieldValue>
                  </div>
                  {contacts.length > 0 && (
                    <div className='space-y-2 border-t pt-4'>
                      <h3 className='text-xs font-semibold uppercase tracking-wide text-muted-foreground'>
                        Contact evidence
                      </h3>
                      {contacts.map((contact) => (
                        <div
                          key={contact.id}
                          className='flex flex-wrap items-center justify-between gap-2 rounded-lg border px-3 py-2.5 text-sm'
                        >
                          <div className='min-w-0'>
                            <span className='font-medium'>
                              {labelize(contact.contact_type)} · {contact.value}
                            </span>
                            <span className='ml-2 text-xs text-muted-foreground'>
                              via {evidenceSource(contact.source)}
                            </span>
                          </div>
                          <Badge variant='outline'>
                            {labelize(contact.verification_status || 'unverified')}
                          </Badge>
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>

              <Card>
                <CardHeader className='pb-4'>
                  <CardTitle className='text-base'>
                    Locations{' '}
                    <Badge variant='secondary' className='ml-2 align-middle'>
                      {lead.location_count ?? locations.length}
                    </Badge>
                  </CardTitle>
                  <CardDescription>
                    Overture place records grouped under this company.
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  {locations.length === 0 ? (
                    <p className='text-sm text-muted-foreground'>
                      No separate branch records are available.
                    </p>
                  ) : (
                    <div className='divide-y'>
                      {locations.map((location) => {
                        const locationUrl = safeHttpUrl(location.url);
                        return (
                          <div
                            key={location.id}
                            className='flex flex-col gap-2 py-3 first:pt-0 last:pb-0 sm:flex-row sm:items-start sm:justify-between'
                          >
                            <div className='min-w-0'>
                              <p className='font-medium'>{location.name}</p>
                              <p className='mt-0.5 text-sm text-muted-foreground'>
                                {[location.location, location.country].filter(Boolean).join(', ') ||
                                  'Address not listed'}
                              </p>
                              {location.category && (
                                <p className='mt-1 text-xs text-muted-foreground'>
                                  {labelize(location.category)}
                                </p>
                              )}
                            </div>
                            <div className='flex flex-wrap gap-3 text-xs text-muted-foreground'>
                              {location.confidence != null && (
                                <span>
                                  {Math.round(location.confidence * 100)}% source confidence
                                </span>
                              )}
                              {locationUrl && (
                                <a
                                  className='inline-flex items-center gap-1 underline underline-offset-4 hover:text-foreground'
                                  href={locationUrl}
                                  target='_blank'
                                  rel='noreferrer'
                                >
                                  Website <Icons.externalLink className='size-3' />
                                </a>
                              )}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </CardContent>
              </Card>

              <Card>
                <CardHeader className='pb-4'>
                  <CardTitle className='text-base'>
                    Evidence{' '}
                    <Badge variant='secondary' className='ml-2 align-middle'>
                      {lead.evidence_count ?? evidence.length}
                    </Badge>
                  </CardTitle>
                  <CardDescription>
                    Source-backed facts used to evaluate this company.
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  {evidence.length === 0 ? (
                    <div className='rounded-lg border border-dashed p-5 text-sm text-muted-foreground'>
                      No extracted evidence is available yet. Check the company website and source
                      record before approving.
                    </div>
                  ) : (
                    <div className='space-y-3'>
                      {evidence.slice(0, 10).map((item) => {
                        const sourceUrl = safeHttpUrl(item.source_url);
                        return (
                          <article key={item.id} className='rounded-lg border p-3.5'>
                            <div className='flex flex-wrap items-center justify-between gap-2'>
                              <div className='flex flex-wrap items-center gap-2'>
                                <Badge variant='outline'>{labelize(item.evidence_type)}</Badge>
                                <span className='text-xs text-muted-foreground'>
                                  {evidenceSource(item.source)}
                                </span>
                              </div>
                              <span className='text-xs text-muted-foreground'>
                                {formatDate(item.observed_at)}
                              </span>
                            </div>
                            <p className='mt-2 break-words text-sm leading-6'>{item.value}</p>
                            {sourceUrl && (
                              <a
                                className='mt-2 inline-flex items-center gap-1 text-xs font-medium underline decoration-border underline-offset-4 hover:text-primary'
                                href={sourceUrl}
                                target='_blank'
                                rel='noreferrer'
                              >
                                Open source <Icons.externalLink className='size-3' />
                              </a>
                            )}
                          </article>
                        );
                      })}
                      {evidence.length > 10 && (
                        <details className='rounded-lg border px-4 py-3'>
                          <summary className='cursor-pointer text-sm font-medium'>
                            Show {evidence.length - 10} more evidence items
                          </summary>
                          <div className='mt-3 space-y-3'>
                            {evidence.slice(10).map((item) => (
                              <div key={item.id} className='rounded-lg bg-muted/40 p-3'>
                                <div className='flex flex-wrap items-center gap-2 text-xs text-muted-foreground'>
                                  <Badge variant='outline'>{labelize(item.evidence_type)}</Badge>
                                  {evidenceSource(item.source)} · {formatDate(item.observed_at)}
                                </div>
                                <p className='mt-2 break-words text-sm leading-6'>{item.value}</p>
                                {safeHttpUrl(item.source_url) && (
                                  <a
                                    className='mt-1 inline-flex items-center gap-1 text-xs underline underline-offset-4'
                                    href={safeHttpUrl(item.source_url) ?? undefined}
                                    target='_blank'
                                    rel='noreferrer'
                                  >
                                    Open source <Icons.externalLink className='size-3' />
                                  </a>
                                )}
                              </div>
                            ))}
                          </div>
                        </details>
                      )}
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>

            <Card>
              <CardHeader className='pb-3'>
                <CardTitle className='text-base'>Review record</CardTitle>
                <CardDescription>Source and history for this company record.</CardDescription>
              </CardHeader>
              <CardContent className='grid gap-4 text-sm sm:grid-cols-2 lg:grid-cols-4'>
                <FieldValue label='Lead source'>
                  {evidenceSource(lead.source || 'source not recorded')}
                </FieldValue>
                <FieldValue label='First added'>{formatDate(lead.created_at)}</FieldValue>
                <FieldValue label='Last updated'>{formatDate(lead.updated_at)}</FieldValue>
                <FieldValue label='Score version'>{readable(lead.score_version)}</FieldValue>
              </CardContent>
            </Card>

            <Card className='border-foreground/15'>
              <CardContent className='flex flex-col gap-4 p-4 sm:flex-row sm:items-center sm:justify-between sm:p-5'>
                <div>
                  <p className='font-medium'>Next steps</p>
                  <p className='mt-1 text-sm text-muted-foreground'>
                    Review the evidence, then prepare an editable outreach email if the lead is
                    approved.
                  </p>
                </div>
                <div className='grid gap-2 sm:flex sm:shrink-0'>
                  <Button
                    variant='outline'
                    onClick={() => {
                      setActionError(null);
                      setActionNotice(null);
                      setReviewDialogOpen(true);
                    }}
                  >
                    <Icons.check className='mr-2 size-4' />
                    {alreadyApproved ? 'Review decision' : 'Review lead'}
                  </Button>
                  <Button
                    onClick={() => {
                      setActionError(null);
                      setEmailDialogOpen(true);
                    }}
                  >
                    <Icons.send className='mr-2 size-4' />
                    Outreach email
                  </Button>
                </div>
              </CardContent>
            </Card>

            <Dialog open={reviewDialogOpen} onOpenChange={setReviewDialogOpen}>
              <DialogContent className='max-h-[90vh] max-w-xl overflow-y-auto'>
                <DialogHeader>
                  <DialogTitle>Human review</DialogTitle>
                  <DialogDescription>
                    Confirm the evidence and record whether this business fits{' '}
                    {brandLabel(lead.brand_id)}. Approval does not send an email.
                  </DialogDescription>
                </DialogHeader>

                {alreadyApproved ? (
                  <div className='rounded-lg border border-emerald-500/30 bg-emerald-500/5 p-4'>
                    <p className='font-medium text-emerald-800 dark:text-emerald-300'>
                      Approved for outreach
                    </p>
                    <p className='mt-1 text-sm text-muted-foreground'>
                      Reviewed by {readable(lead.reviewed_by, 'Unknown reviewer')} ·{' '}
                      {formatDate(lead.reviewed_at)}
                    </p>
                    {lead.review_note && <p className='mt-3 text-sm'>{lead.review_note}</p>}
                  </div>
                ) : lead.review_status === 'rejected' && outreachBlocked ? (
                  <div className='rounded-lg border border-destructive/25 bg-destructive/5 p-4 text-sm'>
                    This lead was rejected and its outreach state is locked.
                    {lead.review_note && <p className='mt-2'>{lead.review_note}</p>}
                  </div>
                ) : (
                  <div className='space-y-4'>
                    <div className='rounded-lg border bg-muted/30 p-3 text-sm'>
                      <p className='font-medium'>{reviewTone.label} review</p>
                      <p className='mt-1 text-muted-foreground'>
                        {canApprove
                          ? 'This lead meets the current qualification rules. Confirm the evidence before approving.'
                          : 'Approval is unavailable until qualification is complete.'}
                      </p>
                    </div>
                    <div className='space-y-2'>
                      <Label htmlFor='lead-reviewer'>Reviewed by</Label>
                      <Input
                        id='lead-reviewer'
                        value={reviewer}
                        onChange={(event) => setReviewer(event.target.value)}
                        maxLength={255}
                      />
                    </div>
                    <div className='space-y-2'>
                      <Label htmlFor='lead-review-note'>
                        Review note{' '}
                        <span className='font-normal text-muted-foreground'>(optional)</span>
                      </Label>
                      <Textarea
                        id='lead-review-note'
                        value={reviewNote}
                        onChange={(event) => setReviewNote(event.target.value)}
                        maxLength={2000}
                        placeholder='Record why you approved or rejected this company.'
                        className='min-h-24 resize-y'
                      />
                    </div>
                  </div>
                )}

                {actionError && (
                  <p
                    className='rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive'
                    role='alert'
                  >
                    {actionError}
                  </p>
                )}
                {actionNotice && (
                  <p className='rounded-lg border bg-muted/40 p-3 text-sm' role='status'>
                    {actionNotice}
                  </p>
                )}
                <DialogFooter>
                  <Button variant='outline' onClick={() => setReviewDialogOpen(false)}>
                    Close
                  </Button>
                  {!alreadyApproved && !outreachBlocked && (
                    <>
                      <Button
                        variant='outline'
                        onClick={() => void submitDecision('rejected')}
                        disabled={reviewing || sending || !reviewer.trim()}
                      >
                        {reviewing && <Icons.spinner className='mr-2 size-4 animate-spin' />}
                        Reject
                      </Button>
                      <Button
                        onClick={() => void submitDecision('approved')}
                        disabled={!canApprove || reviewing || sending || !reviewer.trim()}
                      >
                        {reviewing ? (
                          <Icons.spinner className='mr-2 size-4 animate-spin' />
                        ) : (
                          <Icons.check className='mr-2 size-4' />
                        )}
                        Approve lead
                      </Button>
                    </>
                  )}
                </DialogFooter>
              </DialogContent>
            </Dialog>

            <Dialog
              open={emailDialogOpen}
              onOpenChange={(open) => {
                setEmailDialogOpen(open);
                if (!open) setActionError(null);
              }}
            >
              <DialogContent className='max-h-[calc(100dvh-2rem)] w-[92vw] max-w-[min(92vw,920px)] overflow-y-auto sm:max-w-[min(92vw,920px)]'>
                <DialogHeader>
                  <DialogTitle>Outreach email</DialogTitle>
                  <DialogDescription>
                    Review and edit the message before it is sent to the published business contact.
                  </DialogDescription>
                </DialogHeader>

                {lead.outreach_status === 'delivery_uncertain' && (
                  <p
                    className='rounded-lg border border-amber-500/30 bg-amber-500/5 p-3 text-sm'
                    role='alert'
                  >
                    Delivery is unresolved. Check the sender&apos;s Sent folder before taking
                    another action.
                  </p>
                )}
                {lead.outreach_status === 'sent' && (
                  <p
                    className='rounded-lg border border-emerald-500/30 bg-emerald-500/5 p-3 text-sm'
                    role='status'
                  >
                    This lead has already received an outreach email
                    {lead.outreach_sent_at ? ` · ${formatDate(lead.outreach_sent_at)}` : ''}.
                  </p>
                )}
                {sendReconciliationRequired && (
                  <div
                    className='rounded-lg border border-amber-500/30 bg-amber-500/5 p-3 text-sm'
                    role='alert'
                  >
                    <p>
                      The send result could not be confirmed. Refresh this lead&apos;s status before
                      attempting another send.
                    </p>
                    <Button
                      className='mt-3'
                      variant='outline'
                      onClick={() => void refreshSendStatus()}
                      disabled={refreshingSendStatus}
                    >
                      {refreshingSendStatus && (
                        <Icons.spinner className='mr-2 size-4 animate-spin' />
                      )}
                      {refreshingSendStatus ? 'Refreshing status…' : 'Refresh send status'}
                    </Button>
                  </div>
                )}
                {draftLoading ? (
                  <p className='flex items-center gap-2 py-6 text-sm text-muted-foreground'>
                    <Icons.spinner className='size-4 animate-spin' /> Preparing email draft…
                  </p>
                ) : draftError ? (
                  <div
                    className='space-y-3 rounded-lg border border-destructive/30 bg-destructive/5 p-4 text-sm'
                    role='alert'
                  >
                    <p>{draftError}</p>
                    <Button
                      size='sm'
                      variant='outline'
                      onClick={() => setDraftRetry((retry) => retry + 1)}
                    >
                      Retry email draft
                    </Button>
                  </div>
                ) : draft && alreadyApproved ? (
                  <div className='space-y-4'>
                    <div className='grid gap-3 rounded-lg border bg-muted/20 p-4 sm:grid-cols-2'>
                      <FieldValue label='From'>{draft.from_email}</FieldValue>
                      <FieldValue label='To'>{draft.to_email}</FieldValue>
                    </div>
                    <div className='space-y-2'>
                      <Label htmlFor='lead-email-subject'>Subject</Label>
                      <Input
                        id='lead-email-subject'
                        value={emailSubject}
                        onChange={(event) => setEmailSubject(event.target.value)}
                        maxLength={998}
                      />
                    </div>
                    <div className='space-y-2'>
                      <Label htmlFor='lead-email-body'>Message</Label>
                      <Textarea
                        id='lead-email-body'
                        value={emailBody}
                        onChange={(event) => setEmailBody(event.target.value)}
                        maxLength={100000}
                        className='h-[min(45dvh,32rem)] min-h-40 resize-y leading-6'
                      />
                    </div>
                    {!draft.configured && (
                      <p className='text-sm text-amber-700 dark:text-amber-300'>
                        Email sending is not configured for this workspace. Your approval and draft
                        are saved; an administrator must configure the authorized sender before
                        sending.
                      </p>
                    )}
                  </div>
                ) : lead.outreach_status === 'sent' ||
                  lead.outreach_status === 'sending' ||
                  lead.outreach_status === 'delivery_uncertain' ? (
                  <p className='rounded-lg border bg-muted/30 p-4 text-sm text-muted-foreground'>
                    {lead.outreach_status === 'sent'
                      ? 'This email has already been sent.'
                      : lead.outreach_status === 'sending'
                        ? 'This email is currently being sent.'
                        : 'Email delivery is unresolved. Check the sender’s Sent folder before taking another action.'}
                  </p>
                ) : lead.outreach_status === 'send_failed' ? (
                  <p className='rounded-lg border bg-muted/30 p-4 text-sm text-muted-foreground'>
                    The previous send failed. Review the lead again before retrying.
                  </p>
                ) : lead.review_status !== 'approved' || lead.outreach_status !== 'approved' ? (
                  <p className='rounded-lg border bg-muted/30 p-4 text-sm text-muted-foreground'>
                    Approve this lead in the review dialog before preparing an outreach email.
                  </p>
                ) : !draftEmailAddress ? (
                  <p className='rounded-lg border bg-muted/30 p-4 text-sm text-muted-foreground'>
                    No published business email is available, so there is no email to send.
                  </p>
                ) : (
                  <div className='space-y-3 rounded-lg border bg-muted/30 p-4 text-sm'>
                    <p className='text-muted-foreground'>The email draft is unavailable.</p>
                    <Button
                      size='sm'
                      variant='outline'
                      onClick={() => setDraftRetry((retry) => retry + 1)}
                    >
                      Retry email draft
                    </Button>
                  </div>
                )}

                {actionError && (
                  <p
                    className='rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive'
                    role='alert'
                  >
                    {actionError}
                  </p>
                )}
                {sentTo && (
                  <p
                    className='rounded-lg border border-emerald-500/30 bg-emerald-500/5 p-3 text-sm'
                    role='status'
                  >
                    Email sent to {sentTo}.
                  </p>
                )}
                <DialogFooter>
                  <Button variant='outline' onClick={() => setEmailDialogOpen(false)}>
                    Close
                  </Button>
                  {draft && alreadyApproved && (
                    <Button
                      onClick={() => void sendEmail()}
                      disabled={
                        !draft.configured ||
                        sending ||
                        Boolean(sentTo) ||
                        sendReconciliationRequired ||
                        !emailSubject.trim() ||
                        /[\r\n]/.test(emailSubject) ||
                        !emailBody.trim()
                      }
                    >
                      {sending ? (
                        <Icons.spinner className='mr-2 size-4 animate-spin' />
                      ) : (
                        <Icons.send className='mr-2 size-4' />
                      )}
                      {sending ? 'Sending…' : sentTo ? 'Email sent' : 'Send email'}
                    </Button>
                  )}
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>
        </>
      )}
    </main>
  );
}
