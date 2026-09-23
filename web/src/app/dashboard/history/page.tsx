'use client';

import React, { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { toast } from 'sonner';
import { getHistoryList, resubmitCampaignReview } from '@/lib/api/client';
import type { HistoryCampaignSummary } from '@/lib/api/types';
import { Button, buttonVariants } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle
} from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter
} from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Icons } from '@/components/icons';
import { cn } from '@/lib/utils';

export default function HistoryPage() {
  const [campaigns, setCampaigns] = useState<HistoryCampaignSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [brandFilter, setBrandFilter] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<string>('all');

  // Resubmit modal state
  const [resubmitTarget, setResubmitTarget] = useState<HistoryCampaignSummary | null>(null);
  const [resubmitNote, setResubmitNote] = useState('');
  const [isResubmitting, setIsResubmitting] = useState(false);

  const fetchCampaigns = useCallback(async () => {
    setIsLoading(true);
    try {
      const data = await getHistoryList();
      setCampaigns(data);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to fetch campaign history';
      toast.error(msg);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchCampaigns();
  }, [fetchCampaigns]);

  const handleResubmit = async () => {
    if (!resubmitTarget) return;
    setIsResubmitting(true);
    try {
      const res = await resubmitCampaignReview(resubmitTarget.id, resubmitNote);
      toast.success(res.message || `Campaign resubmitted for Review Cycle ${res.review_cycle}`);
      setResubmitTarget(null);
      setResubmitNote('');
      fetchCampaigns();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Resubmission failed';
      toast.error(msg);
    } finally {
      setIsResubmitting(false);
    }
  };

  // Filtered campaigns
  const filteredCampaigns = campaigns.filter((c) => {
    if (brandFilter !== 'all' && c.brand_id !== brandFilter) return false;
    if (statusFilter !== 'all' && c.status !== statusFilter) return false;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchTitle = (c.title || '').toLowerCase().includes(q);
      const matchThesis = (c.thesis || '').toLowerCase().includes(q);
      const matchBrand = (c.brand_id || '').toLowerCase().includes(q);
      if (!matchTitle && !matchThesis && !matchBrand) return false;
    }
    return true;
  });

  const totalCount = campaigns.length;
  const inReviewCount = campaigns.filter((c) => c.status === 'pending_review').length;
  const approvedCount = campaigns.filter((c) => c.status === 'approved').length;
  const publishedCount = campaigns.filter((c) => c.status === 'published' || c.publications_count > 0).length;

  const brandBadges: Record<string, { label: string; className: string }> = {
    jade: { label: 'Jade', className: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400' },
    doctorshield: { label: 'DoctorShield', className: 'border-sky-500/30 bg-sky-500/10 text-sky-600 dark:text-sky-400' },
    jaguar: { label: 'Jaguar Transit', className: 'border-amber-500/30 bg-amber-500/10 text-amber-600 dark:text-amber-400' }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'published':
        return <Badge className='bg-purple-600 text-white border-purple-700'>Published</Badge>;
      case 'approved':
        return <Badge className='bg-emerald-600 text-white border-emerald-700'>Approved</Badge>;
      case 'pending_review':
        return <Badge className='bg-blue-600 text-white border-blue-700'>In Review</Badge>;
      case 'rejected':
        return <Badge variant='destructive'>Rejected</Badge>;
      case 'generated':
      case 'draft':
      default:
        return <Badge variant='secondary'>{status.toUpperCase()}</Badge>;
    }
  };

  return (
    <div className='flex min-w-0 w-full flex-col gap-6 px-4 pb-16 pt-6 sm:px-6 lg:px-8 xl:px-12'>
      {/* Page Header */}
      <div className='flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b pb-5'>
        <div>
          <div className='flex items-center gap-2'>
            <Badge variant='outline' className='text-xs font-mono uppercase text-muted-foreground'>
              Audit &amp; Workspace Archive
            </Badge>
          </div>
          <h1 className='text-3xl font-bold tracking-tight text-foreground mt-1'>
            Campaign History
          </h1>
          <p className='text-sm text-muted-foreground mt-0.5'>
            Inspect versioned campaign contents, prompt history, watermarked media records, review cycles, and publication audits.
          </p>
        </div>

        <div className='flex items-center gap-2.5'>
          <Button
            size='sm'
            variant='outline'
            onClick={fetchCampaigns}
            disabled={isLoading}
            className='text-xs'
          >
            <Icons.spinner className={cn('size-3.5 mr-1.5', isLoading && 'animate-spin')} />
            Refresh
          </Button>

          <Link
            href='/dashboard/studio'
            className={cn(buttonVariants({ size: 'sm' }), 'text-xs font-bold gap-1.5')}
          >
            <Icons.add className='size-3.5' />
            <span>Create Campaign</span>
          </Link>
        </div>
      </div>

      {/* Summary KPI Cards */}
      <div className='grid grid-cols-2 sm:grid-cols-4 gap-4'>
        <Card className='shadow-xs'>
          <CardHeader className='pb-2 pt-4 px-4'>
            <CardDescription className='text-xs font-medium'>Total Campaigns</CardDescription>
            <CardTitle className='text-2xl font-bold'>{totalCount}</CardTitle>
          </CardHeader>
        </Card>

        <Card className='shadow-xs'>
          <CardHeader className='pb-2 pt-4 px-4'>
            <CardDescription className='text-xs font-medium text-blue-600 dark:text-blue-400'>
              In Review Queue
            </CardDescription>
            <CardTitle className='text-2xl font-bold text-blue-600 dark:text-blue-400'>
              {inReviewCount}
            </CardTitle>
          </CardHeader>
        </Card>

        <Card className='shadow-xs'>
          <CardHeader className='pb-2 pt-4 px-4'>
            <CardDescription className='text-xs font-medium text-emerald-600 dark:text-emerald-400'>
              Approved Campaigns
            </CardDescription>
            <CardTitle className='text-2xl font-bold text-emerald-600 dark:text-emerald-400'>
              {approvedCount}
            </CardTitle>
          </CardHeader>
        </Card>

        <Card className='shadow-xs'>
          <CardHeader className='pb-2 pt-4 px-4'>
            <CardDescription className='text-xs font-medium text-purple-600 dark:text-purple-400'>
              Published Live
            </CardDescription>
            <CardTitle className='text-2xl font-bold text-purple-600 dark:text-purple-400'>
              {publishedCount}
            </CardTitle>
          </CardHeader>
        </Card>
      </div>

      {/* Filter and Search Bar */}
      <div className='flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 bg-muted/40 p-3 rounded-xl border'>
        <div className='flex items-center gap-2 flex-1 max-w-md'>
          <div className='relative w-full'>
            <Icons.search className='size-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground' />
            <Input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder='Search campaigns by title, thesis, or brand...'
              className='h-9 pl-9 text-xs bg-background'
            />
          </div>
        </div>

        <div className='flex items-center gap-2 flex-wrap'>
          {/* Brand Filter */}
          <div className='flex items-center gap-1 bg-background rounded-lg border p-1'>
            {['all', 'jade', 'doctorshield', 'jaguar'].map((b) => (
              <button
                key={b}
                type='button'
                onClick={() => setBrandFilter(b)}
                className={`px-2.5 py-1 text-xs rounded-md transition-colors ${
                  brandFilter === b
                    ? 'bg-primary text-primary-foreground font-semibold shadow-xs'
                    : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                {b === 'all' ? 'All Brands' : b === 'doctorshield' ? 'DoctorShield' : b.toUpperCase()}
              </button>
            ))}
          </div>

          {/* Status Filter */}
          <div className='flex items-center gap-1 bg-background rounded-lg border p-1'>
            {[
              { id: 'all', label: 'All Status' },
              { id: 'pending_review', label: 'Review' },
              { id: 'approved', label: 'Approved' },
              { id: 'published', label: 'Published' }
            ].map((s) => (
              <button
                key={s.id}
                type='button'
                onClick={() => setStatusFilter(s.id)}
                className={`px-2.5 py-1 text-xs rounded-md transition-colors ${
                  statusFilter === s.id
                    ? 'bg-primary text-primary-foreground font-semibold shadow-xs'
                    : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                {s.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Campaigns Archive Grid */}
      {isLoading ? (
        <div className='flex flex-col items-center justify-center p-16 space-y-3 text-muted-foreground'>
          <Icons.spinner className='size-8 animate-spin text-primary' />
          <span className='text-xs'>Loading campaign history archive...</span>
        </div>
      ) : filteredCampaigns.length === 0 ? (
        <Card className='p-12 text-center border-dashed'>
          <div className='flex flex-col items-center justify-center space-y-3 max-w-sm mx-auto'>
            <Icons.history className='size-10 text-muted-foreground stroke-[1.2]' />
            <h3 className='text-base font-bold'>No campaigns match your filter</h3>
            <p className='text-xs text-muted-foreground'>
              Try adjusting your search query or brand/status filter. You can also generate a new campaign in the Studio.
            </p>
            <Link
              href='/dashboard/studio'
              className={cn(buttonVariants({ size: 'sm' }), 'mt-2')}
            >
              Open Campaign Studio
            </Link>
          </div>
        </Card>
      ) : (
        <div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4'>
          {filteredCampaigns.map((camp) => {
            const brandMeta = brandBadges[camp.brand_id] || {
              label: camp.brand_id.toUpperCase(),
              className: 'border-muted text-muted-foreground'
            };

            const createdDate = new Date(camp.created_at).toLocaleDateString('en-US', {
              month: 'short',
              day: 'numeric',
              year: 'numeric'
            });

            return (
              <Card
                key={camp.id}
                className='flex flex-col justify-between hover:shadow-md transition-shadow border-border/80'
              >
                <CardHeader className='pb-3'>
                  <div className='flex items-center justify-between gap-2 mb-2'>
                    <Badge variant='outline' className={cn('text-[11px] font-semibold', brandMeta.className)}>
                      {brandMeta.label}
                    </Badge>
                    <div className='flex items-center gap-1.5'>
                      <Badge variant='outline' className='text-[10px] font-mono'>
                        Cycle {camp.review_cycle}
                      </Badge>
                      {getStatusBadge(camp.status)}
                    </div>
                  </div>

                  <CardTitle className='text-base font-bold line-clamp-2 leading-tight'>
                    {camp.title || camp.thesis || 'Untitled Campaign'}
                  </CardTitle>
                  <CardDescription className='text-xs line-clamp-2 mt-1 leading-relaxed'>
                    {camp.thesis || 'No thesis provided'}
                  </CardDescription>
                </CardHeader>

                <CardContent className='pt-0 pb-3 flex flex-col gap-2.5 text-xs text-muted-foreground'>
                  {/* Media Status Indicators */}
                  <div className='flex items-center justify-between pt-2 border-t'>
                    <span className='text-[11px] font-medium'>Watermarked Image:</span>
                    {camp.has_final_image ? (
                      <span className='text-emerald-600 dark:text-emerald-400 font-semibold flex items-center gap-1 text-[11px]'>
                        <Icons.check className='size-3' />
                        ✓ Final Ready
                      </span>
                    ) : (
                      <span className='text-amber-500 font-medium flex items-center gap-1 text-[11px]'>
                        <Icons.warning className='size-3' />
                        Watermark Pending
                      </span>
                    )}
                  </div>

                  <div className='flex items-center justify-between'>
                    <span className='text-[11px] font-medium'>Reel Video:</span>
                    {camp.has_final_video ? (
                      <span className='text-emerald-600 dark:text-emerald-400 font-semibold flex items-center gap-1 text-[11px]'>
                        <Icons.check className='size-3' />
                        ✓ Final Ready
                      </span>
                    ) : (
                      <span className='text-muted-foreground text-[11px]'>None generated</span>
                    )}
                  </div>

                  <div className='flex items-center justify-between'>
                    <span className='text-[11px] font-medium'>Created:</span>
                    <span className='font-mono text-[11px]'>{createdDate}</span>
                  </div>
                </CardContent>

                <div className='p-4 pt-2 border-t bg-muted/20 rounded-b-xl flex items-center justify-between gap-2'>
                  <Link
                    href={`/dashboard/history/${camp.id}`}
                    className={cn(buttonVariants({ size: 'sm' }), 'text-xs flex-1 font-bold')}
                  >
                    <Icons.page className='size-3.5 mr-1' />
                    Open Workspace
                  </Link>

                  <Button
                    size='sm'
                    variant='outline'
                    className='text-xs'
                    onClick={() => {
                      setResubmitTarget(camp);
                      setResubmitNote('');
                    }}
                    title='Resubmit for review (Cycle n+1)'
                  >
                    <Icons.refresh className='size-3.5 mr-1' />
                    Resubmit
                  </Button>
                </div>
              </Card>
            );
          })}
        </div>
      )}

      {/* Resubmit for Review Confirmation Dialog */}
      <Dialog open={!!resubmitTarget} onOpenChange={(open) => !open && setResubmitTarget(null)}>
        <DialogContent className='max-w-md'>
          <DialogHeader>
            <DialogTitle className='text-base font-bold'>Resubmit Campaign for Review</DialogTitle>
            <DialogDescription className='text-xs'>
              This will increment the campaign to{' '}
              <strong className='text-foreground'>
                Review Cycle {(resubmitTarget?.review_cycle || 1) + 1}
              </strong>
              , reset its status to &apos;pending_review&apos;, and re-enqueue it in the human verification Review Queue.
            </DialogDescription>
          </DialogHeader>

          <div className='space-y-3 py-2'>
            <div className='p-2.5 rounded-lg bg-muted/40 border text-xs space-y-1'>
              <div className='font-bold text-foreground'>{resubmitTarget?.title}</div>
              <div className='text-muted-foreground line-clamp-1'>{resubmitTarget?.thesis}</div>
            </div>

            <div className='space-y-1.5'>
              <Label className='text-xs font-semibold'>Resubmission Note / Revision Summary</Label>
              <Textarea
                value={resubmitNote}
                onChange={(e) => setResubmitNote(e.target.value)}
                placeholder='e.g., Updated LinkedIn copy with professional disclaimer; applied new high-contrast watermark.'
                className='text-xs min-h-[80px]'
              />
            </div>
          </div>

          <DialogFooter className='gap-2'>
            <Button
              type='button'
              variant='outline'
              size='sm'
              onClick={() => setResubmitTarget(null)}
              disabled={isResubmitting}
              className='text-xs'
            >
              Cancel
            </Button>
            <Button
              type='button'
              size='sm'
              onClick={handleResubmit}
              disabled={isResubmitting}
              className='text-xs font-bold gap-1.5'
            >
              {isResubmitting ? (
                <>
                  <Icons.spinner className='size-3.5 animate-spin' />
                  <span>Resubmitting...</span>
                </>
              ) : (
                <>
                  <Icons.checks className='size-3.5' />
                  <span>Confirm Resubmission</span>
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
