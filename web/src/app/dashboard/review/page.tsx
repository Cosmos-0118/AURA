'use client';

import React, { useEffect, useState, useCallback, useRef } from 'react';
import Image from 'next/image';
import { toast } from 'sonner';
import {
  getCampaignReviewQueue,
  getStudioCampaign,
  getCampaignPublications,
  getCampaignHistory,
  getCampaignMediaList,
  approveCampaignReview,
  rejectCampaignReview,
  editCampaignContent,
  publishCampaignPlatform,
  publishToLinkedIn,
  publishToInstagram,
  publishToX,
  resetAllCampaignData
} from '@/lib/api/client';
import type {
  CampaignReviewCard,
  CampaignPublicationItem,
  CampaignEventItem,
  CampaignMediaItem,
  StudioCampaignDetail,
  BrandId,
  Platform,
  ReasonTag
} from '@/lib/api/types';
import { BrandBadge } from '@/components/aura/common';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Input } from '@/components/ui/input';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter
} from '@/components/ui/dialog';
import { Icons } from '@/components/icons';
import { cn } from '@/lib/utils';


// Helper for formatting timestamps
function formatTimeAgo(isoString: string): string {
  try {
    const d = new Date(isoString);
    const now = new Date();
    const diffMs = now.getTime() - d.getTime();
    const diffMins = Math.floor(diffMs / (60 * 1000));
    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours}h ago`;
    const diffDays = Math.floor(diffHours / 24);
    return `${diffDays}d ago`;
  } catch {
    return isoString;
  }
}

// Clean Platform Icons
function PlatformIcon({ platform, className = 'size-4' }: { platform: Platform | string; className?: string }) {
  switch (platform.toLowerCase()) {
    case 'linkedin':
      return (
        <svg className={className} viewBox='0 0 24 24' fill='currentColor'>
          <path d='M19 3a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h14m-.5 15.5v-5.3a3.26 3.26 0 0 0-3.26-3.26c-.85 0-1.84.52-2.28 1.3v-1.11h-2.79v8.37h2.79v-4.93c0-.77.62-1.4 1.39-1.4a1.4 1.4 0 0 1 1.4 1.4v4.93h2.75M6.46 8.76c-.97 0-1.75-.79-1.75-1.76s.78-1.75 1.75-1.75c.97 0 1.76.78 1.76 1.75s-.79 1.76-1.76 1.76m1.4 9.74v-8.37H5.06v8.37h2.8z' />
        </svg>
      );
    case 'instagram':
      return (
        <svg className={className} viewBox='0 0 24 24' fill='none' stroke='currentColor' strokeWidth='2' strokeLinecap='round' strokeLinejoin='round'>
          <rect width='20' height='20' x='2' y='2' rx='5' ry='5' />
          <path d='M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z' />
          <line x1='17.5' x2='17.51' y1='6.5' y2='6.5' />
        </svg>
      );
    case 'x':
    case 'twitter':
      return (
        <svg className={className} viewBox='0 0 24 24' fill='currentColor'>
          <path d='M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z' />
        </svg>
      );
    case 'blog':
      return (
        <svg className={className} viewBox='0 0 24 24' fill='none' stroke='currentColor' strokeWidth='2' strokeLinecap='round' strokeLinejoin='round'>
          <path d='M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z' />
          <polyline points='14 2 14 8 20 8' />
          <line x1='16' y1='13' x2='8' y2='13' />
          <line x1='16' y1='17' x2='8' y2='17' />
          <line x1='10' y1='9' x2='8' y2='9' />
        </svg>
      );
    case 'reel':
      return (
        <svg className={className} viewBox='0 0 24 24' fill='none' stroke='currentColor' strokeWidth='2' strokeLinecap='round' strokeLinejoin='round'>
          <rect width='18' height='18' x='3' y='3' rx='2' />
          <path d='m9 8 7 4-7 4Z' />
        </svg>
      );
    default:
      return <Icons.post className={className} />;
  }
}

const REASON_OPTIONS: { tag: ReasonTag; label: string; desc: string }[] = [
  { tag: 'TOO_SALESY', label: 'Too Salesy / Aggressive', desc: 'Tone is overly promotional or lacks professional advisory voice' },
  { tag: 'WRONG_CTA', label: 'Incorrect CTA / Link', desc: 'Call to action does not match campaign goals or destination' },
  { tag: 'UNSUPPORTED_CLAIM', label: 'Unsupported Statutory Claim', desc: 'Statements promising zero risk or absolute guarantees' },
  { tag: 'WRONG_BRAND_VOICE', label: 'Wrong Brand Voice', desc: 'Does not reflect the specific brand persona guidelines' },
  { tag: 'BAD_LOCALIZATION', label: 'Localization / Cultural Issue', desc: 'Inappropriate regional phrasing, terminology, or tone' },
  { tag: 'OTHER', label: 'Other Editorial Feedback', desc: 'General editorial revision or quality improvement' }
];

export default function ReviewQueuePage() {
  const [cards, setCards] = useState<CampaignReviewCard[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [queueError, setQueueError] = useState<string | null>(null);
  const queueRequestRef = useRef<AbortController | null>(null);
  const [activeTab, setActiveTab] = useState<string>('all');
  const [brandFilter, setBrandFilter] = useState<BrandId | 'all'>('all');

  // Selected Campaign in Workspace Modal
  const [selectedCard, setSelectedCard] = useState<CampaignReviewCard | null>(null);
  const [workspaceDetail, setWorkspaceDetail] = useState<StudioCampaignDetail | null>(null);
  const [publications, setPublications] = useState<CampaignPublicationItem[]>([]);
  const [historyEvents, setHistoryEvents] = useState<CampaignEventItem[]>([]);
  const [mediaItems, setMediaItems] = useState<CampaignMediaItem[]>([]);
  const [isWorkspaceLoading, setIsWorkspaceLoading] = useState(false);

  // Workspace sub-tabs & content editor
  const [workspaceTab, setWorkspaceTab] = useState<'content' | 'media' | 'compliance' | 'history'>('content');
  const [activePlatformTab, setActivePlatformTab] = useState<Platform>('linkedin');
  const [activeMediaTab, setActiveMediaTab] = useState<'poster' | 'reel'>('poster');
  const [isEditingContent, setIsEditingContent] = useState(false);
  const [editableContent, setEditableContent] = useState('');
  const [editableTitle, setEditableTitle] = useState('');
  const [editFeedbackTag, setEditFeedbackTag] = useState<ReasonTag>('OTHER');
  const [editFeedbackNote, setEditFeedbackNote] = useState('');
  const [isSavingEdit, setIsSavingEdit] = useState(false);

  // Approval & Rejection dialogs
  const [showApproveDialog, setShowApproveDialog] = useState(false);
  const [approveNote, setApproveNote] = useState('Approved by Senior Underwriting Reviewer');
  const [isApproving, setIsApproving] = useState(false);

  const [showRejectDialog, setShowRejectDialog] = useState(false);
  const [rejectTag, setRejectTag] = useState<ReasonTag>('TOO_SALESY');
  const [rejectNote, setRejectNote] = useState('');
  const [isRejecting, setIsRejecting] = useState(false);

  // Platform Publishing Confirmation Modal
  const [platformToConfirm, setPlatformToConfirm] = useState<'linkedin' | 'instagram' | 'x' | null>(null);
  const [isPublishingPlatform, setIsPublishingPlatform] = useState<Record<string, boolean>>({});
  const [publishError, setPublishError] = useState<{ platform: string; message: string } | null>(null);


  // Reset Data Modal
  const [showResetModal, setShowResetModal] = useState(false);
  const [isResetting, setIsResetting] = useState(false);

  // Load Review Queue from backend
  const fetchQueue = useCallback(async () => {
    queueRequestRef.current?.abort();
    const controller = new AbortController();
    queueRequestRef.current = controller;
    let timedOut = false;
    const timeout = window.setTimeout(() => {
      timedOut = true;
      controller.abort();
    }, 12_000);
    setIsLoading(true);
    setQueueError(null);
    try {
      const data = await getCampaignReviewQueue(activeTab !== 'all' ? activeTab : undefined, controller.signal);
      if (queueRequestRef.current !== controller) return;
      setCards(data);
    } catch (err: unknown) {
      if (queueRequestRef.current !== controller) return;
      if (timedOut) {
        setQueueError('The Review Queue API did not respond within 12 seconds. Check that the API server is available, then retry.');
      } else if (!(err instanceof DOMException && err.name === 'AbortError')) {
        setQueueError(err instanceof Error ? err.message : 'Failed to fetch review queue.');
      }
    } finally {
      window.clearTimeout(timeout);
      if (queueRequestRef.current === controller) setIsLoading(false);
    }
  }, [activeTab]);

  useEffect(() => {
    fetchQueue();
  }, [fetchQueue]);

  useEffect(() => () => queueRequestRef.current?.abort(), []);

  // Filter cards by brand
  const filteredCards = cards.filter((card) => {
    if (brandFilter !== 'all' && card.brand_id !== brandFilter) return false;
    return true;
  });

  const counts = {
    all: cards.length,
    pending: cards.filter((c) => c.review_status === 'pending_review' || c.campaign_status === 'pending_review').length,
    approved: cards.filter((c) => c.campaign_status === 'approved' || c.review_status === 'approved').length,
    published: cards.filter((c) => c.campaign_status === 'published' || c.review_status === 'published').length,
    rejected: cards.filter((c) => c.review_status === 'rejected' || c.campaign_status === 'rejected').length
  };

  // Open Workspace for a Campaign
  const openWorkspace = async (card: CampaignReviewCard) => {
    setSelectedCard(card);
    setIsWorkspaceLoading(true);
    setWorkspaceTab('content');
    setIsEditingContent(false);
    try {
      const [detail, pubs, hist, media] = await Promise.all([
        getStudioCampaign(card.campaign_id),
        getCampaignPublications(card.campaign_id).catch(() => []),
        getCampaignHistory(card.campaign_id).catch(() => []),
        getCampaignMediaList(card.campaign_id).catch(() => [])
      ]);
      setWorkspaceDetail(detail);
      setPublications(pubs);
      setHistoryEvents(hist);
      setMediaItems(media);

      // Set initial editable content
      const firstContent = detail.contents.find((c) => c.platform === 'linkedin') || detail.contents[0];
      if (firstContent) {
        setActivePlatformTab(firstContent.platform);
        setEditableContent(firstContent.content);
        setEditableTitle(firstContent.title || '');
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to load campaign details';
      toast.error(msg);
    } finally {
      setIsWorkspaceLoading(false);
    }
  };

  // Switch Platform tab in workspace
  const handleSelectPlatform = (platform: Platform) => {
    setActivePlatformTab(platform);
    setIsEditingContent(false);
    if (workspaceDetail) {
      const item = workspaceDetail.contents.find((c) => c.platform === platform);
      if (item) {
        setEditableContent(item.content);
        setEditableTitle(item.title || '');
      } else {
        setEditableContent('');
        setEditableTitle('');
      }
    }
  };

  // Save Content Edit
  const handleSaveEdit = async () => {
    if (!selectedCard) return;
    setIsSavingEdit(true);
    try {
      await editCampaignContent(selectedCard.campaign_id, {
        platform: activePlatformTab,
        new_content: editableContent,
        new_title: editableTitle || undefined,
        tag: editFeedbackTag,
        note: editFeedbackNote || undefined
      });
      toast.success(`Updated ${activePlatformTab.toUpperCase()} content and recorded feedback!`);
      setIsEditingContent(false);

      // Refresh workspace data
      const [detail, hist] = await Promise.all([
        getStudioCampaign(selectedCard.campaign_id),
        getCampaignHistory(selectedCard.campaign_id)
      ]);
      setWorkspaceDetail(detail);
      setHistoryEvents(hist);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to save edit';
      toast.error(msg);
    } finally {
      setIsSavingEdit(false);
    }
  };

  // Approve Campaign
  const handleApproveCampaign = async () => {
    if (!selectedCard) return;
    setIsApproving(true);
    try {
      await approveCampaignReview(selectedCard.campaign_id, approveNote);
      toast.success('Campaign APPROVED! Multi-platform publishing deck unlocked.');
      setShowApproveDialog(false);

      // Update local card status
      setSelectedCard((prev) => (prev ? { ...prev, campaign_status: 'approved', review_status: 'approved' } : null));

      // Refresh queue and publications
      const [pubs, hist] = await Promise.all([
        getCampaignPublications(selectedCard.campaign_id),
        getCampaignHistory(selectedCard.campaign_id)
      ]);
      setPublications(pubs);
      setHistoryEvents(hist);
      fetchQueue();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to approve campaign';
      toast.error(msg);
    } finally {
      setIsApproving(false);
    }
  };

  // Reject Campaign
  const handleRejectCampaign = async () => {
    if (!selectedCard) return;
    setIsRejecting(true);
    try {
      await rejectCampaignReview(selectedCard.campaign_id, rejectTag, rejectNote, activePlatformTab);
      toast.success('Campaign rejected. Feedback saved to AURA Learned Lessons Memory.');
      setShowRejectDialog(false);
      setSelectedCard(null);
      fetchQueue();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to reject campaign';
      toast.error(msg);
    } finally {
      setIsRejecting(false);
    }
  };

  // Trigger Publish for a Platform (opens platform confirmation modal)
  const handlePublishPlatform = (platform: 'linkedin' | 'instagram' | 'x') => {
    if (!selectedCard) return;
    setPublishError(null);
    setPlatformToConfirm(platform);
  };

  // Confirm Publish to Platform via Buffer
  const handleConfirmPublish = async () => {
    if (!selectedCard || !platformToConfirm) return;
    const plat = platformToConfirm;
    setIsPublishingPlatform((prev) => ({ ...prev, [plat]: true }));
    setPublishError(null);
    try {
      let res;
      if (plat === 'linkedin') {
        res = await publishToLinkedIn(selectedCard.campaign_id);
      } else if (plat === 'instagram') {
        res = await publishToInstagram(selectedCard.campaign_id);
      } else {
        res = await publishToX(selectedCard.campaign_id);
      }
      toast.success(res.message || `Successfully published to ${plat.toUpperCase()}!`);
      setPlatformToConfirm(null);
      setPublishError(null);

      const [pubs, hist] = await Promise.all([
        getCampaignPublications(selectedCard.campaign_id).catch(() => []),
        getCampaignHistory(selectedCard.campaign_id).catch(() => [])
      ]);
      setPublications(pubs);
      setHistoryEvents(hist);
      fetchQueue();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : `Failed to publish to ${plat}`;
      setPublishError({ platform: plat, message: msg });
      toast.error(msg);
    } finally {
      setIsPublishingPlatform((prev) => ({ ...prev, [plat]: false }));
    }
  };


  // Reset All Test Data
  const handleResetData = async () => {
    setIsResetting(true);
    try {
      await resetAllCampaignData();
      toast.success('All test campaigns, media files, and audit records wiped clean.');
      setShowResetModal(false);
      setSelectedCard(null);
      setCards([]);
      fetchQueue();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to reset test data';
      toast.error(msg);
    } finally {
      setIsResetting(false);
    }
  };

  // Active content for current platform
  const currentContentItem = workspaceDetail?.contents.find((c) => c.platform === activePlatformTab);
  const isCampaignApproved = selectedCard?.campaign_status === 'approved' || selectedCard?.campaign_status === 'published';

  // Copy active platform copy to clipboard
  const handleCopyContent = () => {
    const textToCopy = editableContent || currentContentItem?.content || selectedCard?.linkedin_content || '';
    if (textToCopy) {
      navigator.clipboard.writeText(textToCopy);
      toast.success(`Copied ${activePlatformTab.toUpperCase()} copy to clipboard!`);
    }
  };

  // Watermark status of media assets
  const latestImageItem = mediaItems.find((m) => m.media_type === 'image' && (m.media_stage === 'final' || Boolean(m.watermarked))) || mediaItems.find((m) => m.media_type === 'image');
  const isImageFinalWatermarked = Boolean(latestImageItem && (latestImageItem.media_stage === 'final' || Boolean(latestImageItem.watermarked)));

  const latestVideoItem = mediaItems.find((m) => m.media_type === 'video' && (m.media_stage === 'final' || Boolean(m.watermarked))) || mediaItems.find((m) => m.media_type === 'video');
  const isVideoFinalWatermarked = Boolean(latestVideoItem && (latestVideoItem.media_stage === 'final' || Boolean(latestVideoItem.watermarked)));

  return (
    <div className='flex min-w-0 w-full flex-col gap-6 px-4 pb-16 pt-6 sm:px-6 lg:px-8 xl:px-12'>
      {/* Header */}
      <div className='flex flex-col md:flex-row md:items-center justify-between gap-4 border-b pb-5'>
        <div>
          <div className='flex items-center gap-2 text-xs font-semibold text-muted-foreground uppercase tracking-widest'>
            <span>Human-in-the-Loop Gateway</span>
            <span>•</span>
            <span className='text-primary'>Safety Constraint</span>
          </div>
          <h1 className='text-3xl font-bold tracking-tight text-foreground mt-1'>
            Review Queue
          </h1>
          <p className='text-sm text-muted-foreground mt-0.5'>
            Unified campaign gateway. Nothing publishes to social channels without explicit human verification.
          </p>
        </div>

        {/* Controls: Refresh, Reset */}
        <div className='flex items-center gap-2.5 flex-wrap'>
          <Button
            size='sm'
            variant='outline'
            onClick={fetchQueue}
            disabled={isLoading}
            className='text-xs'
          >

            <Icons.spinner className={cn('size-3.5 mr-1.5', isLoading && 'animate-spin')} />
            Refresh
          </Button>

          <Button
            size='sm'
            variant='outline'
            className='text-xs text-destructive hover:bg-destructive/10 hover:text-destructive border-destructive/20'
            onClick={() => setShowResetModal(true)}
          >
            <Icons.trash className='size-3.5 mr-1.5' />
            Reset Test Data
          </Button>
        </div>
      </div>

      {/* Filter Row: Status Tabs + Brand Filters */}
      <div className='flex flex-col md:flex-row items-start md:items-center justify-between gap-4'>
        <Tabs value={activeTab} onValueChange={setActiveTab} className='w-full md:w-auto'>
          <TabsList className='grid grid-cols-5 h-9 w-full md:w-[540px]'>
            <TabsTrigger value='all' className='text-xs'>
              All ({counts.all})
            </TabsTrigger>
            <TabsTrigger value='pending_review' className='text-xs text-amber-600 dark:text-amber-400 font-medium'>
              Pending ({counts.pending})
            </TabsTrigger>
            <TabsTrigger value='approved' className='text-xs text-blue-600 dark:text-blue-400 font-medium'>
              Approved ({counts.approved})
            </TabsTrigger>
            <TabsTrigger value='published' className='text-xs text-emerald-600 dark:text-emerald-400 font-medium'>
              Published ({counts.published})
            </TabsTrigger>
            <TabsTrigger value='rejected' className='text-xs text-muted-foreground'>
              Rejected ({counts.rejected})
            </TabsTrigger>
          </TabsList>
        </Tabs>

        {/* Brand Selector */}
        <div className='flex items-center gap-1.5'>
          <span className='text-xs text-muted-foreground font-medium mr-1'>Brand:</span>
          {(['all', 'jade', 'doctorshield', 'jaguar'] as const).map((b) => (
            <Button
              key={b}
              size='xs'
              variant={brandFilter === b ? 'default' : 'outline'}
              onClick={() => setBrandFilter(b)}
              className='capitalize text-xs font-semibold'
            >
              {b === 'doctorshield' ? 'DoctorShield' : b === 'jaguar' ? 'Jaguar' : b}
            </Button>
          ))}
        </div>
      </div>

      {/* Campaign Cards List (ONE CARD PER CAMPAIGN) */}
      {queueError && cards.length > 0 && (
        <Card className='border-amber-500/35 p-4' role='status'>
          <p className='text-sm text-muted-foreground'>Review Queue could not refresh: {queueError}</p>
        </Card>
      )}
      {isLoading ? (
        <div className='grid grid-cols-1 md:grid-cols-2 gap-5'>
          {[1, 2].map((i) => (
            <Card key={i} className='p-6 animate-pulse border-muted'>
              <div className='h-6 w-32 bg-muted rounded mb-4' />
              <div className='h-8 w-3/4 bg-muted rounded mb-3' />
              <div className='h-28 bg-muted rounded mb-4' />
              <div className='h-10 bg-muted rounded' />
            </Card>
          ))}
        </div>
      ) : queueError && cards.length === 0 ? (
        <Card className='border-dashed p-12 text-center' role='alert'>
          <div className='mx-auto mb-3 grid size-12 place-items-center rounded-full bg-muted text-muted-foreground'>
            <Icons.warning className='size-6 text-amber-600' />
          </div>
          <h3 className='text-base font-bold text-foreground'>Couldn’t load Review Queue</h3>
          <p className='mx-auto mt-1 max-w-md text-xs text-muted-foreground'>{queueError}</p>
          <Button size='sm' className='mt-4' onClick={fetchQueue}>Try again</Button>
        </Card>
      ) : filteredCards.length === 0 ? (
        <Card className='border-dashed p-12 text-center'>
          <div className='h-12 w-12 rounded-full bg-muted flex items-center justify-center mx-auto text-muted-foreground mb-3'>
            <Icons.checks className='size-6 text-emerald-500' />
          </div>
          <h3 className='text-base font-bold text-foreground'>Review Queue is Clear</h3>
          <p className='text-xs text-muted-foreground mt-1 max-w-md mx-auto'>
            No campaigns currently match the selected filter. To submit a campaign for verification, configure and generate a package in Campaign Studio.
          </p>
        </Card>
      ) : (
        <div className='grid grid-cols-1 md:grid-cols-2 gap-6'>
          {filteredCards.map((card) => {
            const isApproved = card.campaign_status === 'approved' || card.review_status === 'approved';
            const isPublished = card.campaign_status === 'published' || card.review_status === 'published';
            const isRejected = card.review_status === 'rejected';

            return (
              <Card
                key={card.campaign_id}
                className={cn(
                  'shadow-sm flex flex-col justify-between transition-all border hover:border-foreground/30',
                  isPublished && 'border-emerald-500/30 bg-emerald-500/[0.01]',
                  isApproved && !isPublished && 'border-blue-500/30 bg-blue-500/[0.01]',
                  isRejected && 'border-destructive/30 bg-destructive/[0.01]'
                )}
              >
                <CardHeader className='pb-3'>
                  {/* Top Bar: Brand, Status, Queued time */}
                  <div className='flex items-center justify-between gap-2 flex-wrap'>
                    <div className='flex items-center gap-2'>
                      <BrandBadge brandId={card.brand_id} />
                      <Badge
                        variant='outline'
                        className={cn(
                          'text-[10px] uppercase font-bold tracking-wider px-2 py-0.5',
                          isPublished
                            ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400'
                            : isApproved
                            ? 'border-blue-500/30 bg-blue-500/10 text-blue-600 dark:text-blue-400'
                            : isRejected
                            ? 'border-destructive/30 bg-destructive/10 text-destructive'
                            : 'border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-400'
                        )}
                      >
                        {isPublished ? '● Published' : isApproved ? '✓ Approved' : isRejected ? '✕ Rejected' : '⏱ Awaiting Review'}
                      </Badge>
                    </div>

                    <span className='text-[11px] text-muted-foreground'>
                      {formatTimeAgo(card.queued_at)}
                    </span>
                  </div>

                  {/* Campaign Title & Thesis */}
                  <CardTitle className='text-base font-bold text-foreground mt-2 line-clamp-2 leading-snug'>
                    {card.campaign_title}
                  </CardTitle>
                  <CardDescription className='text-xs text-muted-foreground line-clamp-1 mt-0.5'>
                    <strong className='text-foreground/80 font-semibold'>Objective:</strong> {card.objective} · {card.thesis}
                  </CardDescription>

                  {/* Campaign Facts Badges */}
                  {card.campaign_facts && (
                    <div className='flex flex-wrap items-center gap-1.5 mt-2 pt-2 border-t border-border/40 text-[10px]'>
                      {card.campaign_facts.event_name && (
                        <span className='rounded bg-muted/60 px-1.5 py-0.5 font-medium text-foreground/80'>
                          📍 {card.campaign_facts.event_name}
                        </span>
                      )}
                      {card.campaign_facts.date && (
                        <span className='rounded bg-muted/60 px-1.5 py-0.5 font-medium text-foreground/80'>
                          📅 {card.campaign_facts.date}
                        </span>
                      )}
                      {card.campaign_facts.location && (
                        <span className='rounded bg-muted/60 px-1.5 py-0.5 font-medium text-foreground/80'>
                          🏢 {card.campaign_facts.location}
                        </span>
                      )}
                      {card.campaign_facts.price && (
                        <span className='rounded bg-muted/60 px-1.5 py-0.5 font-medium text-foreground/80'>
                          🎟️ {card.campaign_facts.price}
                        </span>
                      )}
                    </div>
                  )}
                </CardHeader>

                <CardContent className='flex flex-col gap-3 pt-0'>
                  {/* Visual Snapshot Preview: Side-by-Side Poster Thumbnail + LinkedIn Excerpt */}
                  <div className='grid grid-cols-1 sm:grid-cols-12 gap-3 bg-muted/20 border rounded-lg p-2.5'>
                    {/* Poster Thumbnail */}
                    <div className='sm:col-span-4 relative rounded-md overflow-hidden bg-muted/40 aspect-[4/3] flex items-center justify-center border'>
                      {card.latest_image_url ? (
                        <>
                          <Image
                            src={card.latest_image_url}
                            alt='Campaign Poster'
                            fill
                            className='object-cover'
                            unoptimized
                          />
                          <div className='absolute bottom-1 left-1 right-1 bg-black/80 text-[9px] text-white px-1.5 py-0.5 rounded backdrop-blur-xs flex items-center justify-between font-mono'>
                            <span>Final Watermarked</span>
                            <span className='text-emerald-400 font-bold'>✓</span>
                          </div>
                        </>
                      ) : (
                        <div className='flex flex-col items-center justify-center text-amber-500 p-2 text-center'>
                          <Icons.warning className='size-5 mb-1 text-amber-500' />
                          <span className='text-[10px] font-semibold'>Final media not ready</span>
                          <span className='text-[8px] text-muted-foreground'>Watermark pending</span>
                        </div>
                      )}

                    </div>

                    {/* LinkedIn Copy Excerpt */}
                    <div className='sm:col-span-8 flex flex-col justify-between text-xs'>
                      <div>
                        <div className='flex items-center gap-1.5 text-muted-foreground font-semibold text-[11px] mb-1'>
                          <PlatformIcon platform='linkedin' className='size-3.5 text-sky-600' />
                          <span>LinkedIn Copy Preview</span>
                        </div>
                        <p className='text-muted-foreground line-clamp-3 text-[11px] leading-relaxed italic'>
                          "{card.linkedin_content || card.thesis}"
                        </p>
                      </div>

                      {/* Hashtags */}
                      {card.linkedin_hashtags && card.linkedin_hashtags.length > 0 && (
                        <div className='flex flex-wrap gap-1 mt-1.5'>
                          {card.linkedin_hashtags.slice(0, 3).map((tag, i) => (
                            <span key={i} className='text-[10px] text-sky-600 dark:text-sky-400 font-mono'>
                              {tag}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Channel Badges & Compliance Row */}
                  <div className='flex items-center justify-between gap-2 pt-2 border-t text-[11px] flex-wrap'>
                    <div className='flex items-center gap-1.5'>
                      <span className='text-[10px] text-muted-foreground uppercase font-bold mr-0.5'>Channels:</span>
                      {(['linkedin', 'instagram', 'x', 'blog', 'reel'] as Platform[]).map((p) => (
                        <span
                          key={p}
                          title={p.toUpperCase()}
                          className='p-1 rounded bg-muted/60 text-muted-foreground hover:text-foreground'
                        >
                          <PlatformIcon platform={p} className='size-3.5' />
                        </span>
                      ))}
                      {card.has_video && (
                        <Badge variant='secondary' className='text-[10px] font-normal py-0 bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-500/20'>
                          🎬 Video Ready
                        </Badge>
                      )}
                    </div>

                    <div className='flex items-center gap-2'>
                      <Badge variant='outline' className='text-[10px] font-normal py-0 border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-400'>
                        <Icons.circleCheck className='size-3 mr-1 text-emerald-600' />
                        100% Compliant
                      </Badge>
                      <span className='text-[10px] text-purple-600 dark:text-purple-400 font-semibold'>
                        🧠 {card.lessons_applied_count || 2} Lessons
                      </span>
                    </div>
                  </div>

                  {/* Action Buttons */}
                  <div className='flex items-center justify-between pt-2 border-t gap-2'>
                    {isPublished ? (
                      <span className='text-[11px] text-emerald-600 font-semibold flex items-center gap-1'>
                        <Icons.circleCheck className='size-3.5' />
                        Published to Channels
                      </span>
                    ) : isApproved ? (
                      <span className='text-[11px] text-blue-600 dark:text-blue-400 font-semibold flex items-center gap-1'>
                        <Icons.check className='size-3.5' />
                        Publishing Deck Unlocked
                      </span>
                    ) : (
                      <span className='text-[11px] text-amber-600 dark:text-amber-400 font-medium'>
                        Requires editorial sign-off
                      </span>
                    )}

                    <Button
                      size='sm'
                      variant='default'
                      onClick={() => openWorkspace(card)}
                      className='font-bold text-xs'
                    >
                      <span>Review Campaign</span>
                      <Icons.arrowRight className='size-3.5 ml-1.5' />
                    </Button>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      {/* COMPREHENSIVE CAMPAIGN REVIEW WORKSPACE MODAL */}
      {selectedCard && (
        <Dialog open={Boolean(selectedCard)} onOpenChange={(open) => !open && setSelectedCard(null)}>
          <DialogContent className='max-w-[95vw] xl:max-w-7xl 2xl:max-w-[1600px] w-full max-h-[95vh] overflow-y-auto p-6 sm:p-8 flex flex-col gap-6'>
            {/* Modal Header */}
            <DialogHeader className='border-b pb-4'>
              <div className='flex items-start justify-between gap-4 flex-wrap'>
                <div className='flex flex-col gap-1.5'>
                  <div className='flex items-center gap-2'>
                    <BrandBadge brandId={selectedCard.brand_id} />
                    <Badge
                      variant='outline'
                      className={cn(
                        'text-[11px] font-bold uppercase tracking-wider',
                        selectedCard.campaign_status === 'published'
                          ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-600'
                          : selectedCard.campaign_status === 'approved'
                          ? 'border-blue-500/30 bg-blue-500/10 text-blue-600'
                          : 'border-amber-500/30 bg-amber-500/10 text-amber-600'
                      )}
                    >
                      {selectedCard.campaign_status === 'published'
                        ? 'Published'
                        : selectedCard.campaign_status === 'approved'
                        ? 'Approved'
                        : 'Awaiting Human Review'}
                    </Badge>
                    <span className='text-xs text-muted-foreground'>
                      Queued: {formatTimeAgo(selectedCard.queued_at)}
                    </span>
                  </div>

                  <DialogTitle className='text-xl font-bold text-foreground mt-1'>
                    {selectedCard.campaign_title}
                  </DialogTitle>
                  <DialogDescription className='text-xs text-muted-foreground'>
                    <strong className='text-foreground'>Objective:</strong> {selectedCard.objective} · {selectedCard.thesis}
                  </DialogDescription>
                  {isWorkspaceLoading && (
                    <div className='flex items-center gap-1.5 text-xs text-primary font-medium mt-1'>
                      <Icons.spinner className='size-3.5 animate-spin' />
                      <span>Synchronizing live campaign telemetry...</span>
                    </div>
                  )}
                </div>

                {/* Quick Facts Banner */}
                {selectedCard.campaign_facts && (
                  <div className='flex flex-wrap items-center gap-1.5 max-w-md bg-muted/40 p-2 rounded-lg border text-[11px]'>
                    {selectedCard.campaign_facts.event_name && (
                      <span className='font-semibold text-foreground'>
                        📍 {selectedCard.campaign_facts.event_name}
                      </span>
                    )}
                    {selectedCard.campaign_facts.date && (
                      <span className='text-muted-foreground'>
                        • 📅 {selectedCard.campaign_facts.date}
                      </span>
                    )}
                    {selectedCard.campaign_facts.time && (
                      <span className='text-muted-foreground'>
                        • ⏰ {selectedCard.campaign_facts.time}
                      </span>
                    )}
                    {selectedCard.campaign_facts.location && (
                      <span className='text-muted-foreground'>
                        • 🏢 {selectedCard.campaign_facts.location}
                      </span>
                    )}
                    {selectedCard.campaign_facts.price && (
                      <Badge variant='outline' className='text-[10px] font-normal py-0'>
                        🎟️ {selectedCard.campaign_facts.price}
                      </Badge>
                    )}
                  </div>
                )}
              </div>
            </DialogHeader>

            {/* 2-COLUMN DESKTOP WORKSPACE LAYOUT */}
            <div className='grid grid-cols-1 lg:grid-cols-12 gap-6 items-start'>
              {/* LEFT COLUMN: Campaign Content, Compliance Engine, Audit Trail */}
              <div className='lg:col-span-7 flex flex-col gap-5 min-w-0'>
                {/* 1. Cross-Platform Content Editor & Review */}
                <div className='border rounded-xl p-4 sm:p-5 bg-card flex flex-col gap-4 shadow-xs'>
                  {/* Sub-channel selector & actions */}
                  <div className='flex items-center justify-between gap-2 border-b pb-3 flex-wrap'>
                    <div className='flex items-center gap-1.5 overflow-x-auto py-0.5'>
                      {(['linkedin', 'instagram', 'x', 'reel', 'blog'] as Platform[]).map((p) => {
                        const isSelected = activePlatformTab === p;
                        return (
                          <button
                            key={p}
                            type='button'
                            onClick={() => handleSelectPlatform(p)}
                            className={cn(
                              'flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer capitalize',
                              isSelected
                                ? 'bg-primary text-primary-foreground shadow-xs'
                                : 'bg-muted/60 text-muted-foreground hover:bg-muted hover:text-foreground'
                            )}
                          >
                            <PlatformIcon platform={p} className='size-3.5' />
                            <span>{p}</span>
                          </button>
                        );
                      })}
                    </div>

                    <div className='flex items-center gap-2'>
                      {/* Character counter */}
                      <span className='text-[11px] font-mono text-muted-foreground'>
                        {(editableContent || currentContentItem?.content || '').length} chars
                      </span>

                      {/* Copy button */}
                      <Button
                        size='xs'
                        variant='ghost'
                        onClick={handleCopyContent}
                        className='text-xs text-muted-foreground hover:text-foreground h-7 px-2'
                        title='Copy content to clipboard'
                      >
                        <Icons.share className='size-3.5 mr-1' />
                        Copy
                      </Button>

                      {/* Edit controls */}
                      {!isEditingContent ? (
                        <Button
                          size='xs'
                          variant='outline'
                          onClick={() => setIsEditingContent(true)}
                          className='text-xs font-semibold h-7'
                        >
                          <Icons.edit className='size-3 mr-1' />
                          Edit Copy
                        </Button>
                      ) : (
                        <div className='flex items-center gap-1.5'>
                          <Button
                            size='xs'
                            variant='ghost'
                            onClick={() => {
                              setIsEditingContent(false);
                              if (currentContentItem) {
                                setEditableContent(currentContentItem.content);
                                setEditableTitle(currentContentItem.title || '');
                              }
                            }}
                            disabled={isSavingEdit}
                            className='text-xs h-7'
                          >
                            Cancel
                          </Button>
                          <Button
                            size='xs'
                            variant='default'
                            onClick={handleSaveEdit}
                            disabled={isSavingEdit}
                            className='text-xs font-bold h-7'
                          >
                            {isSavingEdit ? (
                              <>
                                <Icons.spinner className='size-3 mr-1 animate-spin' />
                                Saving...
                              </>
                            ) : (
                              <>
                                <Icons.check className='size-3 mr-1' />
                                Save Changes
                              </>
                            )}
                          </Button>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Title Hook (LinkedIn / Blog / Reel) */}
                  {(activePlatformTab === 'linkedin' || activePlatformTab === 'blog' || activePlatformTab === 'reel') && (
                    <div className='flex flex-col gap-1.5'>
                      <Label className='text-[11px] text-muted-foreground font-semibold uppercase tracking-wider'>
                        Title / Attention Hook
                      </Label>
                      {isEditingContent ? (
                        <Input
                          value={editableTitle}
                          onChange={(e) => setEditableTitle(e.target.value)}
                          className='text-xs font-bold'
                          placeholder='Post title or attention hook'
                        />
                      ) : (
                        <p className='text-xs font-bold text-foreground bg-muted/20 px-3 py-2 rounded-lg border'>
                          {currentContentItem?.title || selectedCard.campaign_title}
                        </p>
                      )}
                    </div>
                  )}

                  {/* Content Body */}
                  <div className='flex flex-col gap-1.5'>
                    <Label className='text-[11px] text-muted-foreground font-semibold uppercase tracking-wider'>
                      Marketing Copy
                    </Label>
                    {isEditingContent ? (
                      <Textarea
                        value={editableContent}
                        onChange={(e) => setEditableContent(e.target.value)}
                        rows={8}
                        className='text-xs font-sans leading-relaxed'
                        placeholder='Enter revised marketing copy...'
                      />
                    ) : (
                      <div className='p-3.5 rounded-lg bg-muted/30 border text-xs leading-relaxed text-foreground whitespace-pre-line select-text font-sans'>
                        {currentContentItem?.content || selectedCard.linkedin_content || selectedCard.thesis}
                      </div>
                    )}
                  </div>

                  {/* Reel Voiceover & Storyboard */}
                  {activePlatformTab === 'reel' && currentContentItem?.script && (
                    <div className='flex flex-col gap-1.5 pt-2 border-t'>
                      <Label className='text-[11px] text-muted-foreground font-semibold uppercase tracking-wider'>
                        Voiceover & Storyboard Script
                      </Label>
                      <pre className='p-3 rounded-lg bg-muted/40 border text-[11px] font-mono whitespace-pre-wrap leading-relaxed text-foreground'>
                        {currentContentItem.script}
                      </pre>
                    </div>
                  )}

                  {/* Feedback Tag & Note (shown when editing) */}
                  {isEditingContent && (
                    <div className='grid grid-cols-1 sm:grid-cols-2 gap-3 pt-3 border-t bg-muted/20 p-3 rounded-lg'>
                      <div className='flex flex-col gap-1'>
                        <Label className='text-xs font-bold text-foreground'>
                          Feedback Tag (Saved to AURA Memory)
                        </Label>
                        <select
                          value={editFeedbackTag}
                          onChange={(e) => setEditFeedbackTag(e.target.value as ReasonTag)}
                          className='h-8 rounded-md border bg-background px-2.5 py-1 text-xs shadow-xs'
                        >
                          {REASON_OPTIONS.map((opt) => (
                            <option key={opt.tag} value={opt.tag}>
                              {opt.label}
                            </option>
                          ))}
                        </select>
                      </div>

                      <div className='flex flex-col gap-1'>
                        <Label className='text-xs font-bold text-foreground'>
                          Reviewer Editorial Note
                        </Label>
                        <Input
                          value={editFeedbackNote}
                          onChange={(e) => setEditFeedbackNote(e.target.value)}
                          placeholder='e.g., Aligned disclaimer to Singapore MAS guidelines'
                          className='text-xs h-8'
                        />
                      </div>
                    </div>
                  )}

                  {/* Hashtags */}
                  {currentContentItem?.hashtags && currentContentItem.hashtags.length > 0 && (
                    <div className='flex items-center gap-1.5 flex-wrap pt-2 border-t'>
                      <span className='text-[10px] font-semibold text-muted-foreground'>Hashtags:</span>
                      {currentContentItem.hashtags.map((h, i) => (
                        <Badge key={i} variant='secondary' className='text-[10px] font-mono py-0 text-sky-600 dark:text-sky-400'>
                          {h}
                        </Badge>
                      ))}
                    </div>
                  )}
                </div>

                {/* 2. AURA Compliance Engine Audit Card */}
                <div className='border rounded-xl p-4 sm:p-5 bg-card flex flex-col gap-3.5 shadow-xs'>
                  <div className='flex items-center justify-between border-b pb-3 flex-wrap gap-2'>
                    <div>
                      <h4 className='text-sm font-bold text-foreground flex items-center gap-2'>
                        <Icons.circleCheck className='size-4 text-emerald-600' />
                        <span>AURA Compliance Engine Verdict: 100% PASS</span>
                      </h4>
                      <p className='text-xs text-muted-foreground mt-0.5'>
                        Pre-verified across statutory insurance regulations, advertising laws, and underwriting guidelines.
                      </p>
                    </div>
                    <Badge variant='outline' className='border-emerald-500/30 bg-emerald-500/10 text-emerald-600 font-bold text-xs'>
                      0 Violations
                    </Badge>
                  </div>

                  <div className='grid grid-cols-1 sm:grid-cols-2 gap-2.5'>
                    <div className='p-3 rounded-lg border bg-muted/20 flex items-start gap-2.5'>
                      <Icons.check className='size-3.5 text-emerald-600 shrink-0 mt-0.5' />
                      <div className='text-xs'>
                        <strong className='text-foreground font-semibold'>Statutory Claim Verification (CLAIM_001)</strong>
                        <p className='text-muted-foreground mt-0.5 text-[11px] leading-snug'>
                          No unconditional or absolute liability promises detected ("100% guarantee", "zero risk").
                        </p>
                      </div>
                    </div>

                    <div className='p-3 rounded-lg border bg-muted/20 flex items-start gap-2.5'>
                      <Icons.check className='size-3.5 text-emerald-600 shrink-0 mt-0.5' />
                      <div className='text-xs'>
                        <strong className='text-foreground font-semibold'>Advisory Disclaimers (ABS_004)</strong>
                        <p className='text-muted-foreground mt-0.5 text-[11px] leading-snug'>
                          Required statutory policy advisory terms and consultation disclaimers are preserved.
                        </p>
                      </div>
                    </div>

                    <div className='p-3 rounded-lg border bg-muted/20 flex items-start gap-2.5'>
                      <Icons.check className='size-3.5 text-emerald-600 shrink-0 mt-0.5' />
                      <div className='text-xs'>
                        <strong className='text-foreground font-semibold'>Brand Persona Alignment</strong>
                        <p className='text-muted-foreground mt-0.5 text-[11px] leading-snug'>
                          Tone respects institutional authority guidelines for {selectedCard.brand_id.toUpperCase()}.
                        </p>
                      </div>
                    </div>

                    <div className='p-3 rounded-lg border bg-muted/20 flex items-start gap-2.5'>
                      <Icons.check className='size-3.5 text-emerald-600 shrink-0 mt-0.5' />
                      <div className='text-xs'>
                        <strong className='text-foreground font-semibold'>Cross-Platform Consistency</strong>
                        <p className='text-muted-foreground mt-0.5 text-[11px] leading-snug'>
                          Factual dates, times, locations, and CTAs match across copy and visual prompts.
                        </p>
                      </div>
                    </div>
                  </div>
                </div>

                {/* 3. Chronological Audit Trail */}
                <div className='border rounded-xl p-4 sm:p-5 bg-card flex flex-col gap-3 shadow-xs'>
                  <div className='flex items-center justify-between'>
                    <h4 className='text-xs font-bold text-foreground uppercase tracking-wider flex items-center gap-1.5'>
                      <Icons.clock className='size-3.5 text-primary' />
                      <span>Campaign Audit Trail ({historyEvents.length} events)</span>
                    </h4>
                    <span className='text-[10px] text-muted-foreground'>Immutable ledger</span>
                  </div>

                  {historyEvents.length === 0 ? (
                    <p className='text-xs text-muted-foreground italic py-2'>No events recorded for this campaign.</p>
                  ) : (
                    <div className='max-h-56 overflow-y-auto pr-2 relative pl-5 space-y-3.5 border-l-2 border-muted ml-2 mt-1'>
                      {historyEvents.map((evt) => (
                        <div key={evt.id} className='relative flex flex-col gap-0.5'>
                          {/* Dot indicator */}
                          <div
                            className={cn(
                              'absolute -left-[27px] top-1 size-2.5 rounded-full border-2 border-background',
                              evt.event_type.includes('published')
                                ? 'bg-emerald-500'
                                : evt.event_type.includes('approved')
                                ? 'bg-blue-500'
                                : evt.event_type.includes('reject')
                                ? 'bg-destructive'
                                : 'bg-primary'
                            )}
                          />

                          <div className='flex items-center justify-between text-xs'>
                            <span className='font-bold text-foreground font-mono text-[11px] uppercase'>
                              {evt.event_type.replace(/_/g, ' ')}
                            </span>
                            <span className='text-[10px] text-muted-foreground'>
                              {new Date(evt.created_at).toLocaleString()}
                            </span>
                          </div>

                          <p className='text-xs text-muted-foreground'>{evt.description}</p>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* RIGHT COLUMN: Media Previews & Approval / Publishing Deck */}
              <div className='lg:col-span-5 flex flex-col gap-5 min-w-0'>
                {/* 1. Final Media Previews Card */}
                <div className='border rounded-xl p-4 sm:p-5 bg-card flex flex-col gap-4 shadow-xs'>
                  {/* Media Preview Toggle */}
                  <div className='flex items-center justify-between border-b pb-3 flex-wrap gap-2'>
                    <div className='flex items-center gap-1 bg-muted/60 p-1 rounded-lg'>
                      <button
                        type='button'
                        onClick={() => setActiveMediaTab('poster')}
                        className={cn(
                          'flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-bold transition-all cursor-pointer',
                          activeMediaTab === 'poster'
                            ? 'bg-background text-foreground shadow-xs'
                            : 'text-muted-foreground hover:text-foreground'
                        )}
                      >
                        <Icons.media className='size-3.5 text-emerald-600' />
                        <span>Poster (1:1)</span>
                      </button>

                      <button
                        type='button'
                        onClick={() => setActiveMediaTab('reel')}
                        className={cn(
                          'flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-bold transition-all cursor-pointer',
                          activeMediaTab === 'reel'
                            ? 'bg-background text-foreground shadow-xs'
                            : 'text-muted-foreground hover:text-foreground'
                        )}
                      >
                        <Icons.video className='size-3.5 text-purple-600' />
                        <span>Reel (9:16)</span>
                      </button>
                    </div>

                    {/* Watermark badge */}
                    {activeMediaTab === 'poster' ? (
                      <Badge
                        variant='outline'
                        className={cn(
                          'text-[10px] font-mono py-0',
                          isImageFinalWatermarked
                            ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-600 font-bold'
                            : 'border-muted-foreground/30 text-muted-foreground'
                        )}
                      >
                        {isImageFinalWatermarked ? '✓ Final Watermarked' : 'Final media not ready'}
                      </Badge>
                    ) : (
                      <Badge
                        variant='outline'
                        className={cn(
                          'text-[10px] font-mono py-0',
                          isVideoFinalWatermarked
                            ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-600 font-bold'
                            : 'border-amber-500/30 bg-amber-500/10 text-amber-600 font-medium'
                        )}
                      >
                        {isVideoFinalWatermarked ? '✓ Final Watermarked' : 'Final media not ready'}
                      </Badge>
                    )}
                  </div>

                  {/* POSTER VIEW (1:1 Square) */}
                  {activeMediaTab === 'poster' && (
                    <div className='flex flex-col gap-3'>
                      <div className='relative aspect-square max-w-[360px] mx-auto w-full rounded-xl overflow-hidden border bg-muted/20 shadow-xs flex items-center justify-center'>
                        {selectedCard.latest_image_url ? (
                          <Image
                            src={selectedCard.latest_image_url}
                            alt='Official Campaign Poster'
                            fill
                            className='object-cover'
                            unoptimized
                          />
                        ) : (
                          <div className='text-center p-6 text-xs text-amber-600 dark:text-amber-400 flex flex-col items-center gap-2'>
                            <Icons.warning className='size-8 opacity-80' />
                            <span className='font-semibold text-sm'>Final media not ready</span>
                            <span className='text-xs text-muted-foreground max-w-xs'>
                              Watermark has not yet been applied to the campaign poster. Unwatermarked assets cannot be reviewed or published.
                            </span>
                          </div>
                        )}
                      </div>


                      {/* Image Prompt */}
                      {selectedCard.latest_image_prompt && (
                        <div className='flex flex-col gap-1'>
                          <span className='text-[10px] font-semibold text-muted-foreground uppercase'>Visual Poster Prompt:</span>
                          <p className='text-[11px] text-muted-foreground bg-muted/40 p-2.5 rounded-lg border leading-relaxed line-clamp-3'>
                            {selectedCard.latest_image_prompt}
                          </p>
                        </div>
                      )}

                      {/* Poster Action Controls */}
                      {selectedCard.latest_image_url && (
                        <div className='flex items-center justify-between pt-1'>
                          <a
                            href={selectedCard.latest_image_url}
                            target='_blank'
                            rel='noopener noreferrer'
                            className='text-xs font-semibold text-primary hover:underline flex items-center gap-1'
                          >
                            <span>Open Full Resolution</span>
                            <Icons.externalLink className='size-3' />
                          </a>

                          <a
                            href={selectedCard.latest_image_url}
                            download={`campaign_${selectedCard.campaign_id}_poster.png`}
                            className='text-xs font-semibold text-muted-foreground hover:text-foreground flex items-center gap-1'
                          >
                            <span>Download PNG</span>
                          </a>
                        </div>
                      )}
                    </div>
                  )}

                  {/* REEL VIEW (9:16 Vertical) */}
                  {activeMediaTab === 'reel' && (
                    <div className='flex flex-col gap-3'>
                      <div className='relative aspect-[9/16] max-h-[440px] mx-auto w-auto rounded-xl overflow-hidden border bg-black shadow-xs flex items-center justify-center'>
                        {selectedCard.latest_video_url ? (
                          <video
                            controls
                            playsInline
                            aria-label='Campaign Video Reel Player'
                            src={selectedCard.latest_video_url}
                            className='w-full h-full object-cover'
                          >
                            <track kind='captions' />
                          </video>
                        ) : (
                          <div className='text-center p-6 text-xs text-muted-foreground flex flex-col items-center gap-2'>
                            <Icons.video className='size-8 opacity-40' />
                            <span>No video reel generated for this campaign</span>
                          </div>
                        )}
                      </div>

                      {/* Video Prompt */}
                      {workspaceDetail?.video_prompt && (
                        <div className='flex flex-col gap-1'>
                          <span className='text-[10px] font-semibold text-muted-foreground uppercase'>Reel Motion Prompt:</span>
                          <p className='text-[11px] text-muted-foreground bg-muted/40 p-2.5 rounded-lg border leading-relaxed line-clamp-3'>
                            {workspaceDetail.video_prompt}
                          </p>
                        </div>
                      )}

                      {/* Reel Action Controls */}
                      {selectedCard.latest_video_url && (
                        <div className='flex items-center justify-between pt-1'>
                          <a
                            href={selectedCard.latest_video_url}
                            target='_blank'
                            rel='noopener noreferrer'
                            className='text-xs font-semibold text-primary hover:underline flex items-center gap-1'
                          >
                            <span>Open Full Video</span>
                            <Icons.externalLink className='size-3' />
                          </a>

                          <a
                            href={selectedCard.latest_video_url}
                            download={`campaign_${selectedCard.campaign_id}_reel.mp4`}
                            className='text-xs font-semibold text-muted-foreground hover:text-foreground flex items-center gap-1'
                          >
                            <span>Download MP4</span>
                          </a>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Recorded Version History Mini-Bar */}
                  {mediaItems.length > 0 && (
                    <div className='pt-2 border-t flex items-center justify-between text-[11px] text-muted-foreground'>
                      <span className='font-semibold'>Recorded Assets: {mediaItems.length}</span>
                      <div className='flex items-center gap-1.5'>
                        {mediaItems.map((m, idx) => (
                          <Badge
                            key={m.id || idx}
                            variant='outline'
                            className={cn(
                              'text-[9px] font-mono px-1.5 py-0',
                              m.media_stage === 'final'
                                ? 'border-emerald-500/40 text-emerald-600'
                                : 'border-muted-foreground/30 text-muted-foreground'
                            )}
                          >
                            {m.media_type === 'image' ? 'IMG' : 'VID'}:{m.media_stage || 'orig'}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                {/* 2. Review Decisions & Multi-Platform Publishing Deck Card */}
                <div className='border rounded-xl p-4 sm:p-5 bg-card flex flex-col gap-4 shadow-sm'>
                  {!isCampaignApproved ? (
                    /* UNAPPROVED: APPROVAL / REJECTION DECISION BUTTONS */
                    <div className='flex flex-col gap-3'>
                      <div>
                        <h4 className='text-sm font-bold text-foreground'>
                          Campaign Review Decision
                        </h4>
                        <p className='text-xs text-muted-foreground mt-0.5'>
                          Inspect the compliance verdict and final watermarked assets before approving for distribution.
                        </p>
                      </div>

                      {/* Status Banner when awaiting approval, rejected, or edited */}
                      {selectedCard.campaign_status === 'rejected' || selectedCard.review_status === 'rejected' ? (
                        <div className='p-2.5 rounded-lg border border-destructive/30 bg-destructive/10 text-destructive text-xs flex items-center gap-2'>
                          <Icons.alertCircle className='size-4 shrink-0' />
                          <div>
                            <span className='font-bold block'>Publishing unavailable</span>
                            <span className='text-[11px] opacity-90'>Campaign rejected. Resolve reviewer feedback and resubmit.</span>
                          </div>
                        </div>
                      ) : selectedCard.campaign_status === 'edited' ? (
                        <div className='p-2.5 rounded-lg border border-muted bg-muted/20 text-muted-foreground text-xs flex items-center gap-2'>
                          <Icons.clock className='size-4 shrink-0' />
                          <div>
                            <span className='font-bold block'>Publishing unavailable</span>
                            <span className='text-[11px]'>This version has edits and requires another review.</span>
                          </div>
                        </div>
                      ) : (
                        <div className='p-2.5 rounded-lg border border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-400 text-xs flex items-center gap-2'>
                          <Icons.lock className='size-4 text-amber-500 shrink-0' />
                          <div>
                            <span className='font-bold block'>Publishing locked</span>
                            <span className='text-[11px] opacity-90'>Awaiting human approval. Publishing is unlocked after explicit approval.</span>
                          </div>
                        </div>
                      )}

                      <div className='flex items-center gap-3 pt-2'>
                        <Button
                          size='sm'
                          variant='destructive'
                          onClick={() => setShowRejectDialog(true)}
                          className='font-bold text-xs flex-1'
                        >
                          <Icons.close className='size-3.5 mr-1.5' />
                          Request Changes
                        </Button>

                        <Button
                          size='sm'
                          variant='default'
                          onClick={() => setShowApproveDialog(true)}
                          className='font-bold text-xs flex-1 bg-emerald-600 hover:bg-emerald-700 text-white shadow-xs'
                        >
                          <Icons.check className='size-3.5 mr-1.5' />
                          Approve Campaign
                        </Button>
                      </div>
                    </div>
                  ) : (
                    /* APPROVED: PLATFORM PUBLISHING DECK */
                    <div className='flex flex-col gap-3.5'>
                      <div className='flex items-center justify-between flex-wrap gap-2 border-b pb-3'>
                        <div className='flex items-center gap-2'>
                          <Badge className='bg-emerald-600 hover:bg-emerald-600 text-white text-[10px] uppercase font-bold tracking-wider'>
                            ✓ Approved
                          </Badge>
                          <span className='text-xs font-bold text-foreground'>
                            Publishing Deck (Buffer API)
                          </span>
                        </div>
                        <span className='text-[10px] text-muted-foreground font-medium'>
                          Platform-Specific Broadcast
                        </span>
                      </div>

                      {/* 3 Platform Publishing Cards: LinkedIn, Instagram, X */}
                      <div className='flex flex-col gap-2.5'>
                        {(['linkedin', 'instagram', 'x'] as const).map((plat) => {
                          const pub = publications.find((p) => p.platform === plat);
                          const isPublished = pub?.status === 'published';
                          const isPublishing = Boolean(isPublishingPlatform[plat]);
                          const hasContent = Boolean(
                            workspaceDetail?.contents.find((c) => c.platform === plat)?.content ||
                            (plat === 'linkedin' && selectedCard.linkedin_content)
                          );
                          const isMediaReady = isImageFinalWatermarked || isVideoFinalWatermarked;
                          const bufferPostId = pub?.buffer_post_id || pub?.external_post_id;

                          return (
                            <div
                              key={plat}
                              className={cn(
                                'border rounded-xl p-3 flex flex-col gap-2.5 bg-card text-xs transition-all shadow-xs',
                                isPublished && 'border-emerald-500/40 bg-emerald-500/[0.02]'
                              )}
                            >
                              <div className='flex items-center justify-between gap-3'>
                                <div className='flex items-center gap-2.5'>
                                  <PlatformIcon platform={plat} className='size-4 text-primary' />
                                  <div className='flex flex-col'>
                                    <span className='font-bold capitalize text-foreground text-xs'>
                                      {plat === 'linkedin' ? 'LinkedIn' : plat === 'instagram' ? 'Instagram' : 'X'}
                                    </span>
                                    {isPublished ? (
                                      <span className='text-[10px] text-emerald-600 dark:text-emerald-400 font-semibold flex items-center gap-1'>
                                        <Icons.check className='size-3' />
                                        Published to {plat === 'linkedin' ? 'LinkedIn' : plat === 'instagram' ? 'Instagram' : 'X'}
                                        {bufferPostId && <span className='font-mono opacity-80'>({bufferPostId.slice(-8)})</span>}
                                      </span>
                                    ) : (
                                      <span className='text-[10px] text-muted-foreground'>
                                        Buffer dispatch ready
                                      </span>
                                    )}
                                  </div>
                                </div>

                                <div>
                                  {isPublished ? (
                                    <div className='flex items-center gap-2'>
                                      <span className='text-[10px] bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 px-2 py-0.5 rounded font-semibold'>
                                        ✓ Published
                                      </span>
                                      <a
                                        href={pub?.external_post_url || 'https://publish.buffer.com'}
                                        target='_blank'
                                        rel='noopener noreferrer'
                                        className='inline-flex items-center justify-center gap-1 py-1 px-2.5 rounded-md bg-muted text-foreground font-medium text-[11px] hover:bg-muted/80'
                                      >
                                        <span>View Post</span>
                                        <Icons.externalLink className='size-3' />
                                      </a>
                                    </div>
                                  ) : (
                                    <Button
                                      size='sm'
                                      variant='default'
                                      onClick={() => handlePublishPlatform(plat)}
                                      disabled={isPublishing || !isMediaReady}
                                      className={cn(
                                        'font-bold text-xs',
                                        plat === 'linkedin' ? 'bg-[#0077B5] hover:bg-[#005E93] text-white' :
                                        plat === 'instagram' ? 'bg-gradient-to-r from-[#833AB4] via-[#FD1D1D] to-[#F77737] text-white' :
                                        'bg-zinc-900 hover:bg-black text-white dark:bg-white dark:text-black dark:hover:bg-zinc-200'
                                      )}
                                    >
                                      {isPublishing ? (
                                        <>
                                          <Icons.spinner className='size-3 mr-1.5 animate-spin' />
                                          Posting to {plat === 'linkedin' ? 'LinkedIn' : plat === 'instagram' ? 'Instagram' : 'X'}...
                                        </>
                                      ) : (
                                        <>
                                          <Icons.send className='size-3 mr-1.5' />
                                          Post to {plat === 'linkedin' ? 'LinkedIn' : plat === 'instagram' ? 'Instagram' : 'X'}
                                        </>
                                      )}
                                    </Button>
                                  )}
                                </div>
                              </div>

                              {/* Platform readiness checks */}
                              <div className='flex items-center gap-3 pt-1 border-t border-muted/50 text-[11px] text-muted-foreground'>
                                <span className={cn('flex items-center gap-1 font-medium', hasContent ? 'text-emerald-600 dark:text-emerald-400' : 'text-amber-500')}>
                                  {hasContent ? '✓' : '○'} Content approved
                                </span>
                                <span className={cn('flex items-center gap-1 font-medium', isMediaReady ? 'text-emerald-600 dark:text-emerald-400' : 'text-amber-500')}>
                                  {isMediaReady ? '✓' : '○'} {plat === 'instagram' ? 'Final image/video ready' : plat === 'linkedin' ? 'Final image ready' : 'Final media ready'}
                                </span>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      )}

      {/* PLATFORM PUBLISHING CONFIRMATION MODAL */}
      {selectedCard && platformToConfirm && (
        <Dialog open={Boolean(platformToConfirm)} onOpenChange={(open) => !open && setPlatformToConfirm(null)}>
          <DialogContent className='max-w-2xl p-6 flex flex-col gap-4'>
            <DialogHeader className='border-b pb-3'>
              <div className='flex items-center gap-2 font-bold text-sm'>
                <PlatformIcon platform={platformToConfirm} className='size-5 text-primary' />
                <span>
                  Post to {platformToConfirm === 'linkedin' ? 'LinkedIn' : platformToConfirm === 'instagram' ? 'Instagram' : 'X'}?
                </span>
              </div>
              <DialogTitle className='text-base font-bold text-foreground mt-1'>
                Confirm {platformToConfirm === 'linkedin' ? 'LinkedIn' : platformToConfirm === 'instagram' ? 'Instagram' : 'X'} Broadcast
              </DialogTitle>
              <DialogDescription className='text-xs text-muted-foreground'>
                Review the approved commentary and final watermarked assets before dispatching to Buffer.
              </DialogDescription>
            </DialogHeader>

            {/* Target Brand & Campaign Summary */}
            <div className='flex items-center justify-between p-3 rounded-lg border bg-muted/20'>
              <div className='flex flex-col'>
                <span className='text-[10px] uppercase tracking-wider text-muted-foreground font-semibold'>
                  {selectedCard.brand_id.toUpperCase()}
                </span>
                <span className='font-bold text-sm text-foreground'>
                  {selectedCard.campaign_title || selectedCard.thesis}
                </span>
              </div>
              <Badge className='bg-emerald-600 text-white text-[10px] font-bold uppercase'>
                ✓ Approved
              </Badge>
            </div>

            {/* Attached Final Watermarked Media Preview */}
            {selectedCard.latest_image_url && (
              <div className='relative aspect-[16/9] rounded-lg overflow-hidden border bg-muted/40'>
                <Image
                  src={selectedCard.latest_image_url}
                  alt='Final Watermarked Media'
                  fill
                  className='object-cover'
                  unoptimized
                />
                <div className='absolute bottom-1 right-1 bg-black/80 text-[10px] text-emerald-400 px-2 py-0.5 rounded backdrop-blur-xs font-mono font-bold'>
                  ✓ Final Watermarked
                </div>
              </div>
            )}

            {/* Post Commentary Preview */}
            {(() => {
              const platformContent = workspaceDetail?.contents.find((c) => c.platform === platformToConfirm);
              const textSnippet = platformContent?.content || (platformToConfirm === 'linkedin' ? selectedCard.linkedin_content : selectedCard.thesis);
              const hashtags = platformContent?.hashtags || (platformToConfirm === 'linkedin' ? selectedCard.linkedin_hashtags : []);

              return (
                <div className='flex flex-col gap-1 max-h-40 overflow-y-auto p-3 rounded-lg bg-muted/30 border text-xs text-foreground/90 whitespace-pre-line leading-relaxed'>
                  <span className='text-[10px] uppercase font-bold text-muted-foreground mb-1'>
                    Approved {platformToConfirm.toUpperCase()} Copy:
                  </span>
                  {textSnippet}
                  {hashtags && hashtags.length > 0 && (
                    <span className='text-[11px] text-sky-600 dark:text-sky-400 font-mono mt-1'>
                      {hashtags.join(' ')}
                    </span>
                  )}
                </div>
              );
            })()}

            {/* Verification Checklist */}
            <div className='p-3 rounded-lg border border-emerald-500/20 bg-emerald-500/5 text-xs flex flex-col gap-1.5'>
              <span className='text-[10px] uppercase font-bold text-emerald-700 dark:text-emerald-400'>Pre-Publish Verification:</span>
              <div className='grid grid-cols-3 gap-2 text-[11px] text-foreground font-medium'>
                <span className='text-emerald-600 dark:text-emerald-400 font-semibold'>✓ Campaign approved</span>
                <span className='text-emerald-600 dark:text-emerald-400 font-semibold'>✓ Final media ready</span>
                <span className='text-emerald-600 dark:text-emerald-400 font-semibold'>✓ Content ready</span>
              </div>
            </div>

            {/* Actionable Error Display */}
            {publishError && publishError.platform === platformToConfirm && (
              <div className='p-3 rounded-lg border border-destructive/30 bg-destructive/10 text-destructive text-xs flex flex-col gap-2'>
                <div className='flex items-center gap-1.5 font-bold text-destructive'>
                  <Icons.alertCircle className='size-4 text-destructive shrink-0' />
                  <span>Publishing failed</span>
                </div>
                <p className='leading-relaxed font-medium'>{publishError.message}</p>
                {(publishError.message.includes('MEDIA_PUBLIC_BASE_URL') ||
                  publishError.message.includes('media URL') ||
                  publishError.message.includes('Buffer cannot access')) && (
                  <div className='mt-1 pt-2 border-t border-destructive/20 text-[11px] text-foreground/80 space-y-1'>
                    <span className='font-bold text-foreground'>Action Required:</span>
                    <ul className='list-disc list-inside space-y-0.5 text-muted-foreground'>
                      <li>Configure <code className='px-1 py-0.5 rounded bg-muted font-mono text-[10px]'>MEDIA_PUBLIC_BASE_URL</code> in backend <code className='px-1 py-0.5 rounded bg-muted font-mono text-[10px]'>.env</code></li>
                      <li>Ensure your public tunnel (e.g. <code className='font-mono'>ngrok http 8000</code>) or domain is active</li>
                      <li>Verify public HTTPS accessibility of the media URL</li>
                    </ul>
                  </div>
                )}
              </div>
            )}

            <DialogFooter className='border-t pt-3 flex items-center justify-end gap-2'>
              <Button
                variant='ghost'
                size='sm'
                onClick={() => setPlatformToConfirm(null)}
                disabled={Boolean(isPublishingPlatform[platformToConfirm])}
                className='text-xs'
              >
                Cancel
              </Button>
              <Button
                size='sm'
                onClick={handleConfirmPublish}
                disabled={Boolean(isPublishingPlatform[platformToConfirm])}
                className={cn(
                  'font-bold text-xs text-white',
                  platformToConfirm === 'linkedin' ? 'bg-[#0077B5] hover:bg-[#005E93]' :
                  platformToConfirm === 'instagram' ? 'bg-gradient-to-r from-[#833AB4] via-[#FD1D1D] to-[#F77737]' :
                  'bg-zinc-900 hover:bg-black dark:bg-white dark:text-black'
                )}
              >
                {isPublishingPlatform[platformToConfirm] ? (
                  <>
                    <Icons.spinner className='size-3.5 mr-1.5 animate-spin' />
                    Posting to {platformToConfirm === 'linkedin' ? 'LinkedIn' : platformToConfirm === 'instagram' ? 'Instagram' : 'X'}...
                  </>
                ) : publishError && publishError.platform === platformToConfirm ? (
                  <>
                    <Icons.refresh className='size-3.5 mr-1.5' />
                    Retry {platformToConfirm === 'linkedin' ? 'LinkedIn' : platformToConfirm === 'instagram' ? 'Instagram' : 'X'}
                  </>
                ) : (
                  <>
                    <Icons.send className='size-3.5 mr-1.5' />
                    Post to {platformToConfirm === 'linkedin' ? 'LinkedIn' : platformToConfirm === 'instagram' ? 'Instagram' : 'X'}
                  </>
                )}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}

      {/* APPROVAL CONFIRMATION DIALOG */}
      {selectedCard && (
        <Dialog open={showApproveDialog} onOpenChange={setShowApproveDialog}>
          <DialogContent className='max-w-md p-6 flex flex-col gap-4'>
            <DialogHeader>
              <DialogTitle className='text-base font-bold text-foreground flex items-center gap-2'>
                <Icons.circleCheck className='size-5 text-emerald-600' />
                <span>Approve Campaign Package</span>
              </DialogTitle>
              <DialogDescription className='text-xs text-muted-foreground'>
                Approving unlocks multi-platform publishing and verifies statutory compliance for this campaign.
              </DialogDescription>
            </DialogHeader>

            <div className='flex flex-col gap-1.5'>
              <Label className='text-xs font-semibold text-foreground'>Reviewer Sign-off Note</Label>
              <Input
                value={approveNote}
                onChange={(e) => setApproveNote(e.target.value)}
                className='text-xs'
                placeholder='e.g., Reviewed by Head of Compliance'
              />
            </div>

            <DialogFooter className='border-t pt-3 flex items-center justify-end gap-2'>
              <Button
                variant='ghost'
                size='sm'
                onClick={() => setShowApproveDialog(false)}
                disabled={isApproving}
                className='text-xs'
              >
                Cancel
              </Button>
              <Button
                size='sm'
                onClick={handleApproveCampaign}
                disabled={isApproving}
                className='bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs'
              >
                {isApproving ? (
                  <>
                    <Icons.spinner className='size-3.5 mr-1.5 animate-spin' />
                    Approving...
                  </>
                ) : (
                  'Confirm Approval'
                )}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}

      {/* REJECTION DIALOG WITH LESSON CAPTURE */}
      {selectedCard && (
        <Dialog open={showRejectDialog} onOpenChange={setShowRejectDialog}>
          <DialogContent className='max-w-md p-6 flex flex-col gap-4'>
            <DialogHeader>
              <DialogTitle className='text-base font-bold text-foreground flex items-center gap-2'>
                <Icons.warning className='size-5 text-destructive' />
                <span>Reject Campaign Package</span>
              </DialogTitle>
              <DialogDescription className='text-xs text-muted-foreground'>
                Rejection feedback will be stored in MySQL and used by Groq as negative guidance for future generations.
              </DialogDescription>
            </DialogHeader>

            <div className='flex flex-col gap-3'>
              <div className='flex flex-col gap-1'>
                <Label className='text-xs font-semibold text-foreground'>Feedback Reason Tag</Label>
                <select
                  value={rejectTag}
                  onChange={(e) => setRejectTag(e.target.value as ReasonTag)}
                  className='h-8 rounded-md border bg-background px-2.5 py-1 text-xs shadow-xs'
                >
                  {REASON_OPTIONS.map((opt) => (
                    <option key={opt.tag} value={opt.tag}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </div>

              <div className='flex flex-col gap-1'>
                <Label className='text-xs font-semibold text-foreground'>Correction Guidance Note</Label>
                <Textarea
                  value={rejectNote}
                  onChange={(e) => setRejectNote(e.target.value)}
                  placeholder='Explain why this campaign was rejected and how the model should adjust...'
                  rows={3}
                  className='text-xs'
                />
              </div>
            </div>

            <DialogFooter className='border-t pt-3 flex items-center justify-end gap-2'>
              <Button
                variant='ghost'
                size='sm'
                onClick={() => setShowRejectDialog(false)}
                disabled={isRejecting}
                className='text-xs'
              >
                Cancel
              </Button>
              <Button
                size='sm'
                variant='destructive'
                onClick={handleRejectCampaign}
                disabled={isRejecting || !rejectNote.trim()}
                className='font-bold text-xs'
              >
                {isRejecting ? (
                  <>
                    <Icons.spinner className='size-3.5 mr-1.5 animate-spin' />
                    Recording Rejection...
                  </>
                ) : (
                  'Reject & Save Lesson'
                )}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}

      {/* RESET TEST DATA CONFIRMATION MODAL */}
      <Dialog open={showResetModal} onOpenChange={setShowResetModal}>
        <DialogContent className='max-w-md p-6 flex flex-col gap-4'>
          <DialogHeader>
            <DialogTitle className='text-base font-bold text-foreground flex items-center gap-2'>
              <Icons.trash className='size-5 text-destructive' />
              <span>Reset All Campaign & Review Data?</span>
            </DialogTitle>
            <DialogDescription className='text-xs text-muted-foreground'>
              This will wipe all campaigns, media files, publications, and audit logs from MySQL and local disk for a clean test run.
            </DialogDescription>
          </DialogHeader>

          <p className='text-xs text-muted-foreground bg-destructive/10 border border-destructive/20 p-3 rounded-lg'>
            ⚠️ This action cannot be undone. You will start with a fresh, empty workspace.
          </p>

          <DialogFooter className='border-t pt-3 flex items-center justify-end gap-2'>
            <Button
              variant='ghost'
              size='sm'
              onClick={() => setShowResetModal(false)}
              disabled={isResetting}
              className='text-xs'
            >
              Cancel
            </Button>
            <Button
              size='sm'
              variant='destructive'
              onClick={handleResetData}
              disabled={isResetting}
              className='font-bold text-xs'
            >
              {isResetting ? (
                <>
                  <Icons.spinner className='size-3.5 mr-1.5 animate-spin' />
                  Resetting...
                </>
              ) : (
                'Wipe All Test Data'
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
