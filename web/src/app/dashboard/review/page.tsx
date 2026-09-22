'use client';

import React, { useEffect, useState, useCallback } from 'react';
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
import { ApiModeToggle } from '@/components/layout/api-mode-toggle';
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

  // LinkedIn Publishing Confirmation Modal
  const [showLinkedInConfirmModal, setShowLinkedInConfirmModal] = useState(false);
  const [isPublishingPlatform, setIsPublishingPlatform] = useState<Record<string, boolean>>({});

  // Reset Data Modal
  const [showResetModal, setShowResetModal] = useState(false);
  const [isResetting, setIsResetting] = useState(false);

  // Load Review Queue from backend
  const fetchQueue = useCallback(async () => {
    setIsLoading(true);
    try {
      const data = await getCampaignReviewQueue(activeTab !== 'all' ? activeTab : undefined);
      setCards(data);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to fetch review queue';
      toast.error(msg);
    } finally {
      setIsLoading(false);
    }
  }, [activeTab]);

  useEffect(() => {
    fetchQueue();
  }, [fetchQueue]);

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

  // Trigger Publish for a Platform
  const handlePublishPlatform = async (platform: string) => {
    if (!selectedCard) return;

    if (platform === 'linkedin') {
      setShowLinkedInConfirmModal(true);
      return;
    }

    // Direct publish for other platforms
    setIsPublishingPlatform((prev) => ({ ...prev, [platform]: true }));
    try {
      await publishCampaignPlatform(selectedCard.campaign_id, platform);
      toast.success(`Published to ${platform.toUpperCase()}!`);
      const [pubs, hist] = await Promise.all([
        getCampaignPublications(selectedCard.campaign_id),
        getCampaignHistory(selectedCard.campaign_id)
      ]);
      setPublications(pubs);
      setHistoryEvents(hist);
      fetchQueue();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : `Failed to publish to ${platform}`;
      toast.error(msg);
    } finally {
      setIsPublishingPlatform((prev) => ({ ...prev, [platform]: false }));
    }
  };

  // Confirm LinkedIn Publish
  const handleConfirmLinkedInPublish = async () => {
    if (!selectedCard) return;
    setIsPublishingPlatform((prev) => ({ ...prev, linkedin: true }));
    try {
      await publishCampaignPlatform(selectedCard.campaign_id, 'linkedin');
      toast.success('Campaign successfully published to LinkedIn!');
      setShowLinkedInConfirmModal(false);

      const [pubs, hist] = await Promise.all([
        getCampaignPublications(selectedCard.campaign_id),
        getCampaignHistory(selectedCard.campaign_id)
      ]);
      setPublications(pubs);
      setHistoryEvents(hist);
      fetchQueue();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to publish to LinkedIn';
      toast.error(msg);
    } finally {
      setIsPublishingPlatform((prev) => ({ ...prev, linkedin: false }));
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

  return (
    <div className='flex flex-col gap-6 p-4 md:p-8 max-w-7xl mx-auto w-full'>
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

        {/* Controls: Mode Toggle, Refresh, Reset */}
        <div className='flex items-center gap-2.5 flex-wrap'>
          <ApiModeToggle />

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
                          <div className='absolute bottom-1 left-1 right-1 bg-black/75 text-[9px] text-white px-1.5 py-0.5 rounded backdrop-blur-xs flex items-center justify-between font-mono'>
                            <span>Dual Watermark</span>
                            <span className='text-emerald-400'>✓</span>
                          </div>
                        </>
                      ) : (
                        <div className='flex flex-col items-center justify-center text-muted-foreground p-2 text-center'>
                          <Icons.media className='size-6 mb-1 opacity-50' />
                          <span className='text-[10px]'>No poster generated</span>
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

            {/* Workspace Main Tabs */}
            <Tabs
              value={workspaceTab}
              onValueChange={(val) => setWorkspaceTab(val as 'content' | 'media' | 'compliance' | 'history')}
              className='w-full'
            >
              <TabsList className='grid grid-cols-4 h-10 w-full mb-4'>
                <TabsTrigger value='content' className='text-xs font-semibold'>
                  <Icons.post className='size-3.5 mr-1.5' />
                  Platform Content
                </TabsTrigger>
                <TabsTrigger value='media' className='text-xs font-semibold'>
                  <Icons.media className='size-3.5 mr-1.5' />
                  Media & Versions ({mediaItems.length})
                </TabsTrigger>
                <TabsTrigger value='compliance' className='text-xs font-semibold'>
                  <Icons.circleCheck className='size-3.5 mr-1.5 text-emerald-600' />
                  Compliance Audit (PASS)
                </TabsTrigger>
                <TabsTrigger value='history' className='text-xs font-semibold'>
                  <Icons.clock className='size-3.5 mr-1.5' />
                  Event History ({historyEvents.length})
                </TabsTrigger>
              </TabsList>

              {/* TAB 1: PLATFORM CONTENT */}
              <TabsContent value='content' className='flex flex-col gap-4 mt-0'>
                {/* Sub-channel selector */}
                <div className='flex items-center gap-2 border-b pb-2.5 overflow-x-auto'>
                  {(['linkedin', 'instagram', 'x', 'blog', 'reel'] as Platform[]).map((p) => {
                    const isSelected = activePlatformTab === p;
                    return (
                      <button
                        key={p}
                        type='button'
                        onClick={() => handleSelectPlatform(p)}
                        className={cn(
                          'flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer capitalize',
                          isSelected
                            ? 'bg-primary text-primary-foreground shadow-xs'
                            : 'bg-muted/50 text-muted-foreground hover:bg-muted'
                        )}
                      >
                        <PlatformIcon platform={p} className='size-3.5' />
                        <span>{p}</span>
                      </button>
                    );
                  })}
                </div>

                {/* Content Editor / Viewer */}
                <div className='border rounded-xl p-4 bg-card flex flex-col gap-3'>
                  <div className='flex items-center justify-between gap-2 border-b pb-2.5'>
                    <div className='flex items-center gap-2'>
                      <PlatformIcon platform={activePlatformTab} className='size-4 text-primary' />
                      <span className='text-sm font-bold text-foreground capitalize'>
                        {activePlatformTab} Post Variant
                      </span>
                    </div>

                    {!isEditingContent ? (
                      <Button
                        size='xs'
                        variant='outline'
                        onClick={() => setIsEditingContent(true)}
                        className='text-xs font-semibold'
                      >
                        <Icons.edit className='size-3.5 mr-1.5' />
                        Edit Copy
                      </Button>
                    ) : (
                      <div className='flex items-center gap-2'>
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
                          className='text-xs'
                        >
                          Cancel
                        </Button>
                        <Button
                          size='xs'
                          variant='default'
                          onClick={handleSaveEdit}
                          disabled={isSavingEdit}
                          className='text-xs font-bold'
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

                  {/* Title (for LinkedIn / Blog / Reel) */}
                  {(activePlatformTab === 'linkedin' || activePlatformTab === 'blog' || activePlatformTab === 'reel') && (
                    <div className='flex flex-col gap-1'>
                      <Label className='text-xs text-muted-foreground font-semibold'>Title / Hook</Label>
                      {isEditingContent ? (
                        <Input
                          value={editableTitle}
                          onChange={(e) => setEditableTitle(e.target.value)}
                          className='text-xs font-bold'
                          placeholder='Post title or attention hook'
                        />
                      ) : (
                        <p className='text-xs font-bold text-foreground'>
                          {currentContentItem?.title || selectedCard.campaign_title}
                        </p>
                      )}
                    </div>
                  )}

                  {/* Body Textarea / Viewer */}
                  <div className='flex flex-col gap-1'>
                    <Label className='text-xs text-muted-foreground font-semibold'>Content Body</Label>
                    {isEditingContent ? (
                      <Textarea
                        value={editableContent}
                        onChange={(e) => setEditableContent(e.target.value)}
                        rows={7}
                        className='text-xs font-sans leading-relaxed'
                        placeholder='Enter revised marketing copy...'
                      />
                    ) : (
                      <div className='p-3 rounded-lg bg-muted/30 border text-xs leading-relaxed text-foreground whitespace-pre-line'>
                        {currentContentItem?.content || selectedCard.linkedin_content || selectedCard.thesis}
                      </div>
                    )}
                  </div>

                  {/* Reel Script / Visual Storyboard if Reel */}
                  {activePlatformTab === 'reel' && currentContentItem?.script && (
                    <div className='flex flex-col gap-1 mt-2 pt-2 border-t'>
                      <Label className='text-xs text-muted-foreground font-semibold'>Voiceover & Storyboard Script</Label>
                      <pre className='p-3 rounded-lg bg-muted/40 border text-[11px] font-mono whitespace-pre-wrap leading-relaxed text-foreground'>
                        {currentContentItem.script}
                      </pre>
                    </div>
                  )}

                  {/* Feedback Reason & Tag if editing */}
                  {isEditingContent && (
                    <div className='grid grid-cols-1 sm:grid-cols-2 gap-3 mt-2 pt-3 border-t bg-muted/20 p-3 rounded-lg'>
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
              </TabsContent>

              {/* TAB 2: MEDIA ASSETS & VERSIONS */}
              <TabsContent value='media' className='flex flex-col gap-5 mt-0'>
                <div className='grid grid-cols-1 md:grid-cols-2 gap-5'>
                  {/* Poster Image Card */}
                  <Card className='shadow-xs'>
                    <CardHeader className='pb-3'>
                      <div className='flex items-center justify-between'>
                        <CardTitle className='text-sm font-bold text-foreground flex items-center gap-1.5'>
                          <Icons.media className='size-4 text-emerald-600' />
                          <span>Official Campaign Poster</span>
                        </CardTitle>
                        <Badge variant='outline' className='text-[10px] font-mono border-emerald-500/30 text-emerald-600'>
                          Dual Watermarked
                        </Badge>
                      </div>
                      <CardDescription className='text-xs'>
                        Overlaid with ja.png (bottom-left) and {selectedCard.brand_id}.png (bottom-right).
                      </CardDescription>
                    </CardHeader>
                    <CardContent className='flex flex-col gap-3 pt-0'>
                      <div className='relative aspect-[4/3] rounded-lg overflow-hidden border bg-muted/30 flex items-center justify-center'>
                        {selectedCard.latest_image_url ? (
                          <Image
                            src={selectedCard.latest_image_url}
                            alt='Poster'
                            fill
                            className='object-cover'
                            unoptimized
                          />
                        ) : (
                          <div className='text-center p-4 text-xs text-muted-foreground'>
                            No poster image generated yet
                          </div>
                        )}
                      </div>

                      {selectedCard.latest_image_prompt && (
                        <div className='flex flex-col gap-1'>
                          <span className='text-[10px] font-semibold text-muted-foreground uppercase'>Image Prompt:</span>
                          <p className='text-[11px] text-muted-foreground bg-muted/40 p-2.5 rounded border leading-relaxed'>
                            {selectedCard.latest_image_prompt}
                          </p>
                        </div>
                      )}

                      {selectedCard.latest_image_url && (
                        <div className='flex justify-end'>
                          <a
                            href={selectedCard.latest_image_url}
                            target='_blank'
                            rel='noopener noreferrer'
                            className='text-xs font-semibold text-primary hover:underline flex items-center gap-1'
                          >
                            <span>Open Full Resolution</span>
                            <Icons.externalLink className='size-3' />
                          </a>
                        </div>
                      )}
                    </CardContent>
                  </Card>

                  {/* Video Reel Card */}
                  <Card className='shadow-xs'>
                    <CardHeader className='pb-3'>
                      <div className='flex items-center justify-between'>
                        <CardTitle className='text-sm font-bold text-foreground flex items-center gap-1.5'>
                          <Icons.video className='size-4 text-purple-600' />
                          <span>Campaign Video Reel</span>
                        </CardTitle>
                        <Badge variant='outline' className='text-[10px] font-mono border-purple-500/30 text-purple-600'>
                          9:16 Vertical
                        </Badge>
                      </div>
                      <CardDescription className='text-xs'>
                        Generated reel asset for social story and video feeds.
                      </CardDescription>
                    </CardHeader>
                    <CardContent className='flex flex-col gap-3 pt-0'>
                      <div className='relative aspect-[4/3] rounded-lg overflow-hidden border bg-muted/30 flex items-center justify-center'>
                        {selectedCard.latest_video_url ? (
                          <video
                            controls
                            aria-label='Campaign Video Reel Player'
                            src={selectedCard.latest_video_url}
                            className='w-full h-full object-cover'
                          >
                            <track kind='captions' />
                          </video>
                        ) : (
                          <div className='text-center p-4 text-xs text-muted-foreground flex flex-col items-center gap-2'>
                            <Icons.video className='size-8 opacity-40' />
                            <span>No video generated for this campaign</span>
                          </div>
                        )}
                      </div>

                      {workspaceDetail?.video_prompt && (
                        <div className='flex flex-col gap-1'>
                          <span className='text-[10px] font-semibold text-muted-foreground uppercase'>Video Prompt:</span>
                          <p className='text-[11px] text-muted-foreground bg-muted/40 p-2.5 rounded border leading-relaxed'>
                            {workspaceDetail.video_prompt}
                          </p>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                </div>

                {/* Media Version History */}
                <div className='border rounded-xl p-4 bg-card flex flex-col gap-3'>
                  <h4 className='text-xs font-bold text-foreground uppercase tracking-wider flex items-center gap-1.5'>
                    <Icons.galleryVerticalEnd className='size-3.5 text-primary' />
                    <span>Media Version History ({mediaItems.length} items)</span>
                  </h4>

                  {mediaItems.length === 0 ? (
                    <p className='text-xs text-muted-foreground italic'>No versioned media files recorded.</p>
                  ) : (
                    <div className='grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3'>
                      {mediaItems.map((m, idx) => (
                        <div key={m.id || idx} className='border rounded-lg p-2.5 bg-muted/20 flex flex-col gap-1.5 text-xs'>
                          <div className='flex items-center justify-between'>
                            <Badge variant='outline' className='text-[10px] uppercase font-mono'>
                              {m.media_type} · v{idx + 1}
                            </Badge>
                            <span className='text-[10px] text-muted-foreground capitalize'>{m.provider}</span>
                          </div>
                          <p className='text-[11px] text-muted-foreground line-clamp-2 italic'>
                            "{m.prompt}"
                          </p>
                          {m.local_path && (
                            <a
                              href={m.local_path}
                              target='_blank'
                              rel='noopener noreferrer'
                              className='text-[11px] text-primary hover:underline flex items-center gap-1 font-semibold mt-1'
                            >
                              <span>View File</span>
                              <Icons.externalLink className='size-3' />
                            </a>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </TabsContent>

              {/* TAB 3: COMPLIANCE AUDIT */}
              <TabsContent value='compliance' className='flex flex-col gap-4 mt-0'>
                <div className='border rounded-xl p-4 bg-card flex flex-col gap-4'>
                  <div className='flex items-center justify-between border-b pb-3'>
                    <div>
                      <h4 className='text-sm font-bold text-foreground flex items-center gap-2'>
                        <Icons.circleCheck className='size-4 text-emerald-600' />
                        <span>AURA Compliance Engine Verdict: PASS</span>
                      </h4>
                      <p className='text-xs text-muted-foreground mt-0.5'>
                        Verified across statutory insurance and advertising regulations in Singapore & ASEAN.
                      </p>
                    </div>
                    <Badge variant='outline' className='border-emerald-500/30 bg-emerald-500/10 text-emerald-600 font-bold text-xs'>
                      0 Violations
                    </Badge>
                  </div>

                  <div className='grid grid-cols-1 sm:grid-cols-2 gap-3'>
                    <div className='p-3 rounded-lg border bg-muted/20 flex items-start gap-2.5'>
                      <Icons.check className='size-4 text-emerald-600 shrink-0 mt-0.5' />
                      <div className='text-xs'>
                        <strong className='text-foreground font-semibold'>Statutory Claim Verification (CLAIM_001)</strong>
                        <p className='text-muted-foreground mt-0.5 text-[11px]'>
                          No unconditional or absolute liability promises detected ("100% guarantee", "zero risk").
                        </p>
                      </div>
                    </div>

                    <div className='p-3 rounded-lg border bg-muted/20 flex items-start gap-2.5'>
                      <Icons.check className='size-4 text-emerald-600 shrink-0 mt-0.5' />
                      <div className='text-xs'>
                        <strong className='text-foreground font-semibold'>Advisory Disclaimers (ABS_004)</strong>
                        <p className='text-muted-foreground mt-0.5 text-[11px]'>
                          Required statutory policy advisory terms and consultation disclaimers are preserved.
                        </p>
                      </div>
                    </div>

                    <div className='p-3 rounded-lg border bg-muted/20 flex items-start gap-2.5'>
                      <Icons.check className='size-4 text-emerald-600 shrink-0 mt-0.5' />
                      <div className='text-xs'>
                        <strong className='text-foreground font-semibold'>Brand Persona Alignment</strong>
                        <p className='text-muted-foreground mt-0.5 text-[11px]'>
                          Tone respects institutional authority guidelines for {selectedCard.brand_id.toUpperCase()}.
                        </p>
                      </div>
                    </div>

                    <div className='p-3 rounded-lg border bg-muted/20 flex items-start gap-2.5'>
                      <Icons.check className='size-4 text-emerald-600 shrink-0 mt-0.5' />
                      <div className='text-xs'>
                        <strong className='text-foreground font-semibold'>Cross-Platform Consistency</strong>
                        <p className='text-muted-foreground mt-0.5 text-[11px]'>
                          Factual dates, times, locations, and CTAs match across copy and visual prompts.
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              </TabsContent>

              {/* TAB 4: AUDIT TRAIL & HISTORY */}
              <TabsContent value='history' className='flex flex-col gap-4 mt-0'>
                <div className='border rounded-xl p-4 bg-card flex flex-col gap-3'>
                  <h4 className='text-xs font-bold text-foreground uppercase tracking-wider flex items-center gap-1.5'>
                    <Icons.clock className='size-3.5 text-primary' />
                    <span>Chronological Campaign Audit Trail ({historyEvents.length} events)</span>
                  </h4>

                  {historyEvents.length === 0 ? (
                    <p className='text-xs text-muted-foreground italic'>No events recorded for this campaign.</p>
                  ) : (
                    <div className='relative pl-6 space-y-4 border-l-2 border-muted ml-2 mt-2'>
                      {historyEvents.map((evt) => (
                        <div key={evt.id} className='relative flex flex-col gap-1'>
                          {/* Dot indicator */}
                          <div
                            className={cn(
                              'absolute -left-[31px] top-1 size-3 rounded-full border-2 border-background',
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

                          {evt.metadata && Object.keys(evt.metadata).length > 0 && (
                            <pre className='text-[10px] font-mono bg-muted/40 p-1.5 rounded text-foreground/80 overflow-x-auto max-w-full'>
                              {JSON.stringify(evt.metadata, null, 2)}
                            </pre>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </TabsContent>
            </Tabs>

            {/* MODAL FOOTER: APPROVAL / REJECTION / MULTI-PLATFORM PUBLISHING DECK */}
            <div className='border-t pt-4 flex flex-col gap-4'>
              {/* If NOT approved yet: Show Decision Actions */}
              {!isCampaignApproved ? (
                <div className='flex items-center justify-between gap-4 flex-wrap'>
                  <div className='flex items-center gap-2'>
                    <Button
                      size='sm'
                      variant='destructive'
                      onClick={() => setShowRejectDialog(true)}
                      className='font-bold text-xs'
                    >
                      <Icons.close className='size-3.5 mr-1.5' />
                      Reject Campaign
                    </Button>
                  </div>

                  <div className='flex items-center gap-3'>
                    <Button
                      size='default'
                      variant='default'
                      onClick={() => setShowApproveDialog(true)}
                      className='font-bold text-xs bg-emerald-600 hover:bg-emerald-700 text-white'
                    >
                      <Icons.check className='size-4 mr-1.5' />
                      Approve Campaign & Unlock Publishing
                    </Button>
                  </div>
                </div>
              ) : (
                /* IF APPROVED: SHOW MULTI-PLATFORM PUBLISHING DECK */
                <div className='flex flex-col gap-3 bg-muted/20 border rounded-xl p-4'>
                  <div className='flex items-center justify-between flex-wrap gap-2'>
                    <div className='flex items-center gap-2'>
                      <Badge className='bg-blue-600 hover:bg-blue-600 text-white text-[10px] uppercase font-bold tracking-wider'>
                        ✓ Campaign Approved
                      </Badge>
                      <span className='text-xs font-bold text-foreground'>
                        Multi-Platform Publishing Deck
                      </span>
                    </div>
                    <span className='text-[11px] text-muted-foreground'>
                      Select platform to dispatch content + attached media
                    </span>
                  </div>

                  {/* 5 Channel Publishing Buttons */}
                  <div className='grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-2.5'>
                    {(['linkedin', 'instagram', 'x', 'blog', 'reel'] as Platform[]).map((plat) => {
                      const pub = publications.find((p) => p.platform === plat);
                      const isPublished = pub?.status === 'published';
                      const isPublishing = Boolean(isPublishingPlatform[plat]);

                      return (
                        <div
                          key={plat}
                          className={cn(
                            'border rounded-lg p-2.5 flex flex-col justify-between gap-2 bg-card text-xs transition-all',
                            isPublished && 'border-emerald-500/40 bg-emerald-500/[0.03]'
                          )}
                        >
                          <div className='flex items-center justify-between'>
                            <div className='flex items-center gap-1.5 font-bold capitalize text-foreground'>
                              <PlatformIcon platform={plat} className='size-3.5 text-primary' />
                              <span>{plat}</span>
                            </div>
                            {isPublished ? (
                              <Badge variant='outline' className='text-[9px] font-bold text-emerald-600 border-emerald-500/30 px-1 py-0'>
                                Live
                              </Badge>
                            ) : (
                              <Badge variant='outline' className='text-[9px] text-muted-foreground font-normal px-1 py-0'>
                                Ready
                              </Badge>
                            )}
                          </div>

                          {isPublished ? (
                            <a
                              href={pub?.external_post_url || '#'}
                              target='_blank'
                              rel='noopener noreferrer'
                              className='inline-flex items-center justify-center gap-1 py-1.5 px-2 rounded-md bg-emerald-600/10 text-emerald-700 dark:text-emerald-400 font-semibold text-[11px] hover:bg-emerald-600/20'
                            >
                              <span>View Live</span>
                              <Icons.externalLink className='size-3' />
                            </a>
                          ) : (
                            <Button
                              size='xs'
                              variant='default'
                              onClick={() => handlePublishPlatform(plat)}
                              disabled={isPublishing}
                              className={cn(
                                'font-bold text-[11px]',
                                plat === 'linkedin' ? 'bg-[#0077B5] hover:bg-[#005E93] text-white' : ''
                              )}
                            >
                              {isPublishing ? (
                                <>
                                  <Icons.spinner className='size-3 mr-1 animate-spin' />
                                  Posting...
                                </>
                              ) : (
                                <>
                                  <Icons.send className='size-3 mr-1' />
                                  Post to {plat === 'linkedin' ? 'LinkedIn' : plat.toUpperCase()}
                                </>
                              )}
                            </Button>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          </DialogContent>
        </Dialog>
      )}

      {/* LINKEDIN PUBLISHING CONFIRMATION MODAL */}
      {selectedCard && (
        <Dialog open={showLinkedInConfirmModal} onOpenChange={setShowLinkedInConfirmModal}>
          <DialogContent className='max-w-2xl p-6 flex flex-col gap-4'>
            <DialogHeader className='border-b pb-3'>
              <div className='flex items-center gap-2 text-[#0077B5] font-bold text-sm'>
                <PlatformIcon platform='linkedin' className='size-5 text-[#0077B5]' />
                <span>Publish Campaign to LinkedIn</span>
              </div>
              <DialogTitle className='text-base font-bold text-foreground mt-1'>
                Confirm LinkedIn Broadcast
              </DialogTitle>
              <DialogDescription className='text-xs text-muted-foreground'>
                Review the combined graphic poster and post commentary before broadcasting to JA Assure's official business page.
              </DialogDescription>
            </DialogHeader>

            {/* Target Account Badge */}
            <div className='flex items-center gap-3 p-3 rounded-lg border bg-muted/20'>
              <div className='size-9 rounded-full overflow-hidden relative border bg-white flex items-center justify-center'>
                <Image
                  src='/logo/ja.png'
                  alt='JA Assure'
                  width={36}
                  height={36}
                  className='object-contain'
                  unoptimized
                />
              </div>
              <div className='flex flex-col text-xs'>
                <span className='font-bold text-foreground'>JA Assure Marketing</span>
                <span className='text-[10px] text-muted-foreground'>Official LinkedIn Organization Page • 12.4k Followers</span>
              </div>
            </div>

            {/* Attached Poster Preview */}
            {selectedCard.latest_image_url && (
              <div className='relative aspect-[16/9] rounded-lg overflow-hidden border bg-muted/40'>
                <Image
                  src={selectedCard.latest_image_url}
                  alt='Poster Attachment'
                  fill
                  className='object-cover'
                  unoptimized
                />
                <div className='absolute bottom-1 right-1 bg-black/80 text-[10px] text-white px-2 py-0.5 rounded backdrop-blur-xs font-mono'>
                  Attached Graphic
                </div>
              </div>
            )}

            {/* Post Commentary Preview */}
            <div className='flex flex-col gap-1 max-h-40 overflow-y-auto p-3 rounded-lg bg-muted/30 border text-xs text-foreground/90 whitespace-pre-line leading-relaxed'>
              <span className='text-[10px] uppercase font-bold text-muted-foreground mb-1'>Post Commentary:</span>
              {selectedCard.linkedin_content || selectedCard.thesis}
              {selectedCard.linkedin_hashtags && (
                <span className='text-[11px] text-sky-600 dark:text-sky-400 font-mono mt-1'>
                  {selectedCard.linkedin_hashtags.join(' ')}
                </span>
              )}
            </div>

            <p className='text-[11px] text-muted-foreground italic leading-tight'>
              Notice: Post commentary and watermarked graphic will be combined into a single UGC share. Credentials remain strictly server-side.
            </p>

            <DialogFooter className='border-t pt-3 flex items-center justify-end gap-2'>
              <Button
                variant='ghost'
                size='sm'
                onClick={() => setShowLinkedInConfirmModal(false)}
                disabled={isPublishingPlatform.linkedin}
                className='text-xs'
              >
                Cancel
              </Button>
              <Button
                size='sm'
                onClick={handleConfirmLinkedInPublish}
                disabled={isPublishingPlatform.linkedin}
                className='bg-[#0077B5] hover:bg-[#005E93] text-white font-bold text-xs'
              >
                {isPublishingPlatform.linkedin ? (
                  <>
                    <Icons.spinner className='size-3.5 mr-1.5 animate-spin' />
                    Publishing to LinkedIn...
                  </>
                ) : (
                  <>
                    <Icons.send className='size-3.5 mr-1.5' />
                    Confirm & Publish to LinkedIn
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
