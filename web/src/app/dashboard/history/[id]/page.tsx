'use client';

import React, { useState, useEffect, useCallback, use } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { toast } from 'sonner';
import {
  getCampaignWorkspaceHistory,
  resubmitCampaignReview,
  assistantChat
} from '@/lib/api/client';
import type {
  CampaignWorkspaceHistory,
  CampaignPlatformContentItem,
  CampaignMediaItem,
  Platform
} from '@/lib/api/types';
import { Button, buttonVariants } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
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
import { Checkbox } from '@/components/ui/checkbox';
import { Icons } from '@/components/icons';
import { cn } from '@/lib/utils';

interface PageProps {
  params: Promise<{ id: string }>;
}

export default function HistoryDetailPage({ params }: PageProps) {
  const resolvedParams = use(params);
  const campaignId = resolvedParams.id;

  const [workspace, setWorkspace] = useState<CampaignWorkspaceHistory | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Selected content platform & version tab
  const [selectedPlatform, setSelectedPlatform] = useState<Platform>('linkedin');
  const [selectedVersion, setSelectedVersion] = useState<number>(1);

  // Resubmit modal state
  const [isResubmitOpen, setIsResubmitOpen] = useState(false);
  const [resubmitNote, setResubmitNote] = useState('');
  const [isResubmitting, setIsResubmitting] = useState(false);

  // AURA Assistant Chat state
  const [chatInstruction, setChatInstruction] = useState('');
  const [chatTargetPlatform, setChatTargetPlatform] = useState<string>('all');
  const [chatRegenMedia, setChatRegenMedia] = useState(false);
  const [chatMediaType, setChatMediaType] = useState<'image' | 'video'>('image');
  const [isChatSubmitting, setIsChatSubmitting] = useState(false);
  const [chatMessages, setChatMessages] = useState<
    Array<{
      sender: 'user' | 'assistant';
      text: string;
      compliance?: Record<string, any>;
      platforms?: string[];
      timestamp: string;
    }>
  >([]);

  const fetchWorkspace = useCallback(
    async (showLoading = false) => {
      if (showLoading) setIsLoading(true);
      try {
        const data = await getCampaignWorkspaceHistory(campaignId);
        setWorkspace(data);
        return data;
      } catch (err: unknown) {
        const msg =
          err instanceof Error ? err.message : 'Failed to fetch campaign history workspace';
        toast.error(msg);
        return null;
      } finally {
        if (showLoading) setIsLoading(false);
      }
    },
    [campaignId]
  );

  useEffect(() => {
    fetchWorkspace(true);
  }, [fetchWorkspace]);

  // When platform changes, select its latest version
  useEffect(() => {
    if (!workspace) return;
    const platContents = workspace.contents.filter((c) => c.platform === selectedPlatform);
    if (platContents.length > 0) {
      const maxV = Math.max(...platContents.map((c) => c.version || 1));
      setSelectedVersion(maxV);
    }
  }, [selectedPlatform]);

  // Ensure selectedVersion is valid whenever workspace updates
  useEffect(() => {
    if (!workspace) return;
    const platContents = workspace.contents.filter((c) => c.platform === selectedPlatform);
    if (platContents.length > 0) {
      const exists = platContents.some((c) => (c.version || 1) === selectedVersion);
      if (!exists) {
        const maxV = Math.max(...platContents.map((c) => c.version || 1));
        setSelectedVersion(maxV);
      }
    }
  }, [workspace, selectedPlatform, selectedVersion]);

  const handleResubmit = async () => {
    setIsResubmitting(true);
    try {
      const res = await resubmitCampaignReview(campaignId, resubmitNote);
      toast.success(res.message || `Resubmitted for Review Cycle ${res.review_cycle}`);
      setIsResubmitOpen(false);
      setResubmitNote('');
      fetchWorkspace(false);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Resubmission failed';
      toast.error(msg);
    } finally {
      setIsResubmitting(false);
    }
  };

  const handleAssistantSend = async () => {
    if (!chatInstruction.trim()) return;
    const userText = chatInstruction;
    setChatInstruction('');

    const newMsg = {
      sender: 'user' as const,
      text: userText,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };
    setChatMessages((prev) => [...prev, newMsg]);
    setIsChatSubmitting(true);

    try {
      const res = await assistantChat(campaignId, {
        message: userText,
        target_platform: chatTargetPlatform === 'all' ? null : chatTargetPlatform,
        regenerate_media: chatRegenMedia,
        media_type: chatMediaType
      });

      setChatMessages((prev) => [
        ...prev,
        {
          sender: 'assistant' as const,
          text: res.reply,
          compliance: res.compliance_results,
          platforms: res.regenerated_platforms,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }
      ]);

      // Optimistically update workspace in-memory immediately with regenerated content
      if (res.updated_contents && res.updated_contents.length > 0) {
        const updatedPlatforms = new Set(res.updated_contents.map((c) => c.platform));
        setWorkspace((prev) => {
          if (!prev) return prev;
          const oldContents = prev.contents.map((c) =>
            updatedPlatforms.has(c.platform) ? { ...c, is_current: false } : c
          );
          return {
            ...prev,
            contents: [...oldContents, ...res.updated_contents],
            media: res.new_media ? [...prev.media, res.new_media] : prev.media
          };
        });

        // Determine which platform to focus: prefer the user's selected platform if updated, else the first updated platform
        const matchedUpdated =
          res.updated_contents.find((c) => c.platform === selectedPlatform) ||
          res.updated_contents[0];
        if (matchedUpdated) {
          const newPlatform = matchedUpdated.platform as Platform;
          const newVersion = matchedUpdated.version || 1;
          setSelectedPlatform(newPlatform);
          setSelectedVersion(newVersion);
        }
      }

      toast.success('Campaign revised! New version(s) saved.');

      // Background sync from database to confirm persistent state
      const freshData = await fetchWorkspace(false);
      if (freshData && res.updated_contents && res.updated_contents.length > 0) {
        const matchedUpdated =
          res.updated_contents.find((c) => c.platform === selectedPlatform) ||
          res.updated_contents[0];
        if (matchedUpdated) {
          const newPlatform = matchedUpdated.platform as Platform;
          const platContents = freshData.contents.filter((c) => c.platform === newPlatform);
          if (platContents.length > 0) {
            const maxV = Math.max(...platContents.map((c) => c.version || 1));
            setSelectedPlatform(newPlatform);
            setSelectedVersion(maxV);
          }
        }
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'AURA Assistant revision failed';
      toast.error(msg);
      setChatMessages((prev) => [
        ...prev,
        {
          sender: 'assistant' as const,
          text: `Revision error: ${msg}`,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }
      ]);
    } finally {
      setIsChatSubmitting(false);
    }
  };

  if (isLoading || !workspace) {
    return (
      <div className='flex flex-col items-center justify-center p-24 space-y-4 text-muted-foreground'>
        <Icons.spinner className='size-9 animate-spin text-primary' />
        <span className='text-sm font-medium'>Loading Campaign Workspace History...</span>
      </div>
    );
  }

  const camp = workspace.campaign;
  const currentCycle =
    workspace.review_cycles.length > 0
      ? Math.max(...workspace.review_cycles.map((r) => r.review_cycle || 1))
      : 1;

  // Contents for selected platform
  const platformVersions = workspace.contents
    .filter((c) => c.platform === selectedPlatform)
    .sort((a, b) => (a.version || 1) - (b.version || 1));

  const activeContentItem =
    platformVersions.find((c) => (c.version || 1) === selectedVersion) ||
    platformVersions[platformVersions.length - 1];

  // Media items
  const imageMedia = workspace.media.filter((m) => m.media_type === 'image');
  const videoMedia = workspace.media.filter((m) => m.media_type === 'video');

  const originalImage = imageMedia.find((m) => m.media_stage === 'original');
  const finalImage = imageMedia.find((m) => m.media_stage === 'final' && m.status === 'completed');

  const originalVideo = videoMedia.find((m) => m.media_stage === 'original');
  const finalVideo = videoMedia.find((m) => m.media_stage === 'final' && m.status === 'completed');

  const brandBadges: Record<string, { label: string; className: string }> = {
    jade: {
      label: 'Jade',
      className: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400'
    },
    doctorshield: {
      label: 'DoctorShield',
      className: 'border-sky-500/30 bg-sky-500/10 text-sky-600 dark:text-sky-400'
    },
    jaguar: {
      label: 'Jaguar Transit',
      className: 'border-amber-500/30 bg-amber-500/10 text-amber-600 dark:text-amber-400'
    }
  };
  const brandMeta = brandBadges[camp.brand_id] || {
    label: (camp.brand_id || 'BRAND').toUpperCase(),
    className: 'border-muted text-muted-foreground'
  };

  return (
    <div className='flex flex-col gap-6 p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto w-full'>
      {/* Top Header & Breadcrumb Navigation */}
      <div className='flex flex-col gap-3 border-b pb-4'>
        <div className='flex items-center gap-2 text-xs text-muted-foreground'>
          <Link
            href='/dashboard/history'
            className='hover:text-foreground flex items-center gap-1 font-medium'
          >
            <Icons.chevronLeft className='size-3.5' />
            <span>Back to Campaign History</span>
          </Link>
          <span>/</span>
          <span className='font-mono text-foreground font-semibold'>
            {campaignId.slice(0, 8)}...
          </span>
        </div>

        <div className='flex flex-col md:flex-row md:items-center justify-between gap-4'>
          <div>
            <div className='flex items-center gap-2 flex-wrap'>
              <Badge variant='outline' className={cn('text-xs font-semibold', brandMeta.className)}>
                {brandMeta.label}
              </Badge>
              <Badge variant='outline' className='text-xs font-mono font-semibold bg-muted'>
                Review Cycle {currentCycle}
              </Badge>
              <Badge
                variant={
                  camp.status === 'approved'
                    ? 'default'
                    : camp.status === 'published'
                      ? 'secondary'
                      : 'outline'
                }
              >
                {camp.status?.toUpperCase() || 'DRAFT'}
              </Badge>
            </div>
            <h1 className='text-2xl font-bold tracking-tight text-foreground mt-1'>
              {camp.title || camp.thesis || 'Campaign Workspace'}
            </h1>
            <p className='text-xs text-muted-foreground mt-0.5 max-w-3xl leading-relaxed'>
              {camp.thesis}
            </p>
          </div>

          <div className='flex items-center gap-2.5 shrink-0'>
            <Button
              variant='outline'
              size='sm'
              onClick={() => setIsResubmitOpen(true)}
              className='text-xs font-bold gap-1.5 border-primary/40 text-primary hover:bg-primary/10'
            >
              <Icons.refresh className='size-3.5' />
              <span>Resubmit for Review</span>
            </Button>

            <Link
              href={`/dashboard/studio?id=${campaignId}`}
              className={cn(buttonVariants({ size: 'sm', variant: 'outline' }), 'text-xs')}
            >
              <Icons.edit className='size-3.5 mr-1' />
              Open Studio
            </Link>
          </div>
        </div>
      </div>

      {/* Main 2-Column Split Workspace */}
      <div className='grid grid-cols-1 lg:grid-cols-12 gap-6 items-start'>
        {/* Left Column: Full Workspace Tabs (8 cols) */}
        <div className='lg:col-span-8 flex flex-col gap-5'>
          <Tabs defaultValue='content' className='w-full'>
            <TabsList className='grid grid-cols-6 h-9 p-1 bg-muted/60 text-xs w-full'>
              <TabsTrigger value='content' className='text-xs'>
                Content
              </TabsTrigger>
              <TabsTrigger value='prompts' className='text-xs'>
                Prompts
              </TabsTrigger>
              <TabsTrigger value='media' className='text-xs'>
                Media
              </TabsTrigger>
              <TabsTrigger value='reviews' className='text-xs'>
                Reviews ({workspace.review_cycles.length})
              </TabsTrigger>
              <TabsTrigger value='pubs' className='text-xs'>
                Pubs ({workspace.publications.length})
              </TabsTrigger>
              <TabsTrigger value='events' className='text-xs'>
                Audit ({workspace.events.length})
              </TabsTrigger>
            </TabsList>

            {/* TAB 1: PLATFORM CONTENT VERSIONS */}
            <TabsContent value='content' className='space-y-4 pt-3'>
              {/* Platform Selector */}
              <div className='flex items-center justify-between gap-2 border-b pb-2 flex-wrap'>
                <div className='flex items-center gap-1.5'>
                  {(['linkedin', 'instagram', 'x', 'blog', 'reel'] as Platform[]).map((p) => {
                    const hasItems = workspace.contents.some((c) => c.platform === p);
                    return (
                      <Button
                        key={p}
                        size='sm'
                        variant={selectedPlatform === p ? 'default' : 'ghost'}
                        className='h-7 text-xs capitalize px-2.5'
                        onClick={() => setSelectedPlatform(p)}
                        disabled={!hasItems}
                      >
                        {p}
                      </Button>
                    );
                  })}
                </div>

                {/* Version Selector for active platform */}
                {platformVersions.length > 1 && (
                  <div className='flex items-center gap-1.5 bg-muted/40 p-1 rounded-lg border text-xs'>
                    <span className='text-[10px] text-muted-foreground font-semibold px-1'>
                      Version:
                    </span>
                    {platformVersions.map((item) => {
                      const v = item.version || 1;
                      const isSelected = selectedVersion === v;
                      return (
                        <button
                          key={v}
                          type='button'
                          onClick={() => setSelectedVersion(v)}
                          className={`px-2 py-0.5 rounded text-[11px] font-mono transition-colors ${
                            isSelected
                              ? 'bg-primary text-primary-foreground font-bold'
                              : 'text-muted-foreground hover:text-foreground'
                          }`}
                        >
                          v{v} {item.is_current ? '(Current)' : ''}
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>

              {/* Content Item Card */}
              {activeContentItem ? (
                <Card className='shadow-xs'>
                  <CardHeader className='pb-3'>
                    <div className='flex items-center justify-between'>
                      <div className='flex items-center gap-2'>
                        <Badge variant='outline' className='text-xs font-mono capitalize'>
                          {activeContentItem.platform} v{activeContentItem.version || 1}
                        </Badge>
                        {activeContentItem.is_current && (
                          <Badge className='bg-emerald-600 text-[10px] font-mono'>
                            Current Version
                          </Badge>
                        )}
                      </div>
                      <span className='text-[11px] text-muted-foreground font-mono'>
                        ID: {activeContentItem.id.slice(0, 8)}
                      </span>
                    </div>

                    {activeContentItem.title && (
                      <CardTitle className='text-base font-bold mt-2'>
                        {activeContentItem.title}
                      </CardTitle>
                    )}
                  </CardHeader>

                  <CardContent className='space-y-4 pt-0 text-xs'>
                    {/* Post Copy */}
                    <div className='p-3.5 rounded-lg bg-muted/30 border text-foreground whitespace-pre-line leading-relaxed text-xs'>
                      {activeContentItem.content}
                    </div>

                    {/* Hashtags */}
                    {activeContentItem.hashtags && activeContentItem.hashtags.length > 0 && (
                      <div className='flex items-center gap-1.5 flex-wrap'>
                        <span className='text-[10px] font-semibold text-muted-foreground'>
                          Hashtags:
                        </span>
                        {activeContentItem.hashtags.map((ht) => (
                          <span
                            key={ht}
                            className='text-xs font-mono text-sky-600 dark:text-sky-400'
                          >
                            {ht.startsWith('#') ? ht : `#${ht}`}
                          </span>
                        ))}
                      </div>
                    )}

                    {/* Reel Script / Visual Concept */}
                    {(activeContentItem.script || activeContentItem.visual_concept) && (
                      <div className='p-3 rounded-lg bg-muted/40 border space-y-2'>
                        {activeContentItem.script && (
                          <div>
                            <span className='text-[10px] font-bold uppercase text-muted-foreground'>
                              Script / Voiceover:
                            </span>
                            <p className='text-xs mt-0.5'>{activeContentItem.script}</p>
                          </div>
                        )}
                        {activeContentItem.visual_concept && (
                          <div>
                            <span className='text-[10px] font-bold uppercase text-muted-foreground'>
                              Visual Concept:
                            </span>
                            <p className='text-xs mt-0.5 text-muted-foreground'>
                              {activeContentItem.visual_concept}
                            </p>
                          </div>
                        )}
                      </div>
                    )}
                  </CardContent>
                </Card>
              ) : (
                <div className='p-8 text-center text-muted-foreground text-xs'>
                  No content generated for {selectedPlatform}.
                </div>
              )}
            </TabsContent>

            {/* TAB 2: VISUAL & VIDEO PROMPTS */}
            <TabsContent value='prompts' className='space-y-4 pt-3'>
              <Card className='shadow-xs'>
                <CardHeader className='pb-2'>
                  <CardTitle className='text-sm font-bold flex items-center gap-2'>
                    <Icons.media className='size-4 text-primary' />
                    <span>Visual Graphic Poster Prompt (1:1 Square)</span>
                  </CardTitle>
                </CardHeader>
                <CardContent className='pt-0 text-xs'>
                  <p className='p-3 rounded-lg bg-muted/40 border leading-relaxed font-mono text-[11px] text-foreground'>
                    {camp.image_prompt ||
                      workspace.contents.find((c) => c.generation_prompt)?.generation_prompt ||
                      'No image prompt recorded'}
                  </p>
                </CardContent>
              </Card>

              <Card className='shadow-xs'>
                <CardHeader className='pb-2'>
                  <CardTitle className='text-sm font-bold flex items-center gap-2'>
                    <Icons.video className='size-4 text-primary' />
                    <span>Vertical Video Reel Motion Prompt (9:16)</span>
                  </CardTitle>
                </CardHeader>
                <CardContent className='pt-0 text-xs'>
                  <p className='p-3 rounded-lg bg-muted/40 border leading-relaxed font-mono text-[11px] text-foreground'>
                    {camp.video_prompt ||
                      workspace.contents.find((c) => c.platform === 'reel')?.generation_prompt ||
                      'No video prompt recorded'}
                  </p>
                </CardContent>
              </Card>
            </TabsContent>

            {/* TAB 3: MEDIA ASSETS & WATERMARK COMPARISON */}
            <TabsContent value='media' className='space-y-5 pt-3'>
              {/* Image Comparison: Original vs Final */}
              <div className='space-y-2'>
                <div className='flex items-center justify-between'>
                  <Label className='text-xs font-bold uppercase text-muted-foreground'>
                    Poster Asset Comparison
                  </Label>
                  <Badge variant='outline' className='text-[10px] font-mono'>
                    1:1 Square
                  </Badge>
                </div>

                <div className='grid grid-cols-1 sm:grid-cols-2 gap-4'>
                  {/* Original AI Output */}
                  <Card className='overflow-hidden border-border/80'>
                    <CardHeader className='py-2.5 px-3 bg-muted/40 border-b flex flex-row items-center justify-between'>
                      <span className='text-xs font-semibold'>1. Original AI Generation</span>
                      <Badge variant='secondary' className='text-[10px]'>
                        Unwatermarked
                      </Badge>
                    </CardHeader>
                    <CardContent className='p-3 flex flex-col items-center justify-center min-h-[220px]'>
                      {originalImage?.local_path ? (
                        <div className='relative aspect-square w-full max-w-[200px] rounded-lg overflow-hidden border'>
                          <Image
                            src={originalImage.local_path}
                            alt='Original AI Output'
                            fill
                            className='object-cover'
                            unoptimized
                          />
                        </div>
                      ) : (
                        <div className='text-center text-xs text-muted-foreground p-4'>
                          No original image record found.
                        </div>
                      )}
                    </CardContent>
                  </Card>

                  {/* Final Watermarked Asset */}
                  <Card className='overflow-hidden border-emerald-500/30'>
                    <CardHeader className='py-2.5 px-3 bg-emerald-500/10 border-b flex flex-row items-center justify-between'>
                      <span className='text-xs font-semibold text-emerald-600 dark:text-emerald-400'>
                        2. Final Watermarked Asset
                      </span>
                      <Badge className='bg-emerald-600 text-[10px]'>Official Verified</Badge>
                    </CardHeader>
                    <CardContent className='p-3 flex flex-col items-center justify-center min-h-[220px]'>
                      {finalImage?.local_path ? (
                        <div className='relative aspect-square w-full max-w-[200px] rounded-lg overflow-hidden border'>
                          <Image
                            src={finalImage.local_path}
                            alt='Final Watermarked Output'
                            fill
                            className='object-cover'
                            unoptimized
                          />
                        </div>
                      ) : (
                        <div className='text-center p-4 text-xs text-amber-500 flex flex-col items-center gap-1.5'>
                          <Icons.warning className='size-6' />
                          <span className='font-semibold'>Final media not ready</span>
                          <span className='text-[10px] text-muted-foreground'>
                            Watermark not applied yet
                          </span>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                </div>

                {/* Watermark Configuration Metadata */}
                {finalImage?.watermark_config && (
                  <Card className='shadow-xs'>
                    <CardHeader className='py-2 px-3 border-b bg-muted/20'>
                      <CardTitle className='text-xs font-bold'>
                        Saved Watermark Configuration
                      </CardTitle>
                    </CardHeader>
                    <CardContent className='p-3 text-[11px] font-mono bg-muted/10'>
                      <pre className='overflow-x-auto whitespace-pre-wrap leading-relaxed'>
                        {JSON.stringify(finalImage.watermark_config, null, 2)}
                      </pre>
                    </CardContent>
                  </Card>
                )}
              </div>

              {/* Video Assets */}
              <div className='space-y-2 pt-2 border-t'>
                <Label className='text-xs font-bold uppercase text-muted-foreground'>
                  Video Reel Asset
                </Label>
                <div className='grid grid-cols-1 sm:grid-cols-2 gap-4'>
                  <Card className='overflow-hidden'>
                    <CardHeader className='py-2 px-3 bg-muted/40 border-b flex flex-row items-center justify-between'>
                      <span className='text-xs font-semibold'>Original AI Video</span>
                      <Badge variant='secondary' className='text-[10px]'>
                        Original
                      </Badge>
                    </CardHeader>
                    <CardContent className='p-3 flex items-center justify-center min-h-[180px]'>
                      {originalVideo?.local_path ? (
                        <video
                          src={originalVideo.local_path}
                          controls
                          className='max-h-[160px] rounded-md border'
                        />
                      ) : (
                        <span className='text-xs text-muted-foreground'>
                          No original video generated
                        </span>
                      )}
                    </CardContent>
                  </Card>

                  <Card className='overflow-hidden border-emerald-500/30'>
                    <CardHeader className='py-2 px-3 bg-emerald-500/10 border-b flex flex-row items-center justify-between'>
                      <span className='text-xs font-semibold text-emerald-600 dark:text-emerald-400'>
                        Final Watermarked Video
                      </span>
                      <Badge className='bg-emerald-600 text-[10px]'>Final</Badge>
                    </CardHeader>
                    <CardContent className='p-3 flex items-center justify-center min-h-[180px]'>
                      {finalVideo?.local_path ? (
                        <video
                          src={finalVideo.local_path}
                          controls
                          className='max-h-[160px] rounded-md border'
                        />
                      ) : (
                        <span className='text-xs text-muted-foreground'>
                          No final video watermarked
                        </span>
                      )}
                    </CardContent>
                  </Card>
                </div>
              </div>
            </TabsContent>

            {/* TAB 4: REVIEW CYCLES & DECISIONS */}
            <TabsContent value='reviews' className='space-y-3 pt-3'>
              {workspace.review_cycles.length === 0 ? (
                <div className='p-8 text-center text-xs text-muted-foreground border rounded-lg'>
                  No review submissions recorded for this campaign yet.
                </div>
              ) : (
                workspace.review_cycles.map((rq, idx) => (
                  <Card key={rq.id || idx} className='shadow-xs border-border/80'>
                    <CardHeader className='pb-2 pt-3 px-4 flex flex-row items-center justify-between'>
                      <div className='flex items-center gap-2'>
                        <Badge variant='outline' className='text-xs font-mono font-bold'>
                          Cycle {rq.review_cycle || idx + 1}
                        </Badge>
                        <Badge
                          className={
                            rq.status === 'approved'
                              ? 'bg-emerald-600 text-white'
                              : rq.status === 'rejected'
                                ? 'bg-destructive text-white'
                                : 'bg-blue-600 text-white'
                          }
                        >
                          {rq.status?.toUpperCase()}
                        </Badge>
                      </div>
                      <span className='text-[10px] text-muted-foreground font-mono'>
                        {new Date(rq.created_at).toLocaleString()}
                      </span>
                    </CardHeader>

                    <CardContent className='pt-0 pb-3 px-4 text-xs space-y-1.5'>
                      {rq.reviewer_note && (
                        <div>
                          <span className='text-[10px] font-bold text-muted-foreground'>
                            Reviewer Note:
                          </span>
                          <p className='text-xs text-foreground bg-muted/30 p-2 rounded border mt-0.5'>
                            {rq.reviewer_note}
                          </p>
                        </div>
                      )}
                      {rq.feedback_tag && (
                        <div className='flex items-center gap-1.5 text-[11px]'>
                          <span className='text-muted-foreground'>Reason Tag:</span>
                          <Badge variant='secondary' className='text-[10px] font-mono'>
                            {rq.feedback_tag}
                          </Badge>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                ))
              )}
            </TabsContent>

            {/* TAB 5: PUBLICATION AUDIT */}
            <TabsContent value='pubs' className='space-y-3 pt-3'>
              {workspace.publications.length === 0 ? (
                <div className='p-8 text-center text-xs text-muted-foreground border rounded-lg'>
                  No platform publications recorded yet. Campaigns must be approved before
                  publishing.
                </div>
              ) : (
                workspace.publications.map((pub) => (
                  <Card key={pub.id} className='shadow-xs'>
                    <CardHeader className='py-2.5 px-4 flex flex-row items-center justify-between border-b bg-muted/20'>
                      <div className='flex items-center gap-2'>
                        <Badge variant='outline' className='text-xs font-bold uppercase'>
                          {pub.platform}
                        </Badge>
                        <Badge
                          className={
                            pub.status === 'published'
                              ? 'bg-emerald-600 text-white'
                              : pub.status === 'failed'
                                ? 'bg-destructive text-white'
                                : 'bg-amber-600 text-white'
                          }
                        >
                          {pub.status?.toUpperCase()}
                        </Badge>
                      </div>
                      <span className='text-[10px] font-mono text-muted-foreground'>
                        {pub.published_at ? new Date(pub.published_at).toLocaleString() : 'Queued'}
                      </span>
                    </CardHeader>

                    <CardContent className='p-4 text-xs space-y-2'>
                      {pub.external_post_url && (
                        <div className='flex items-center justify-between'>
                          <span className='text-muted-foreground text-[11px] font-mono truncate max-w-xs'>
                            ID: {pub.external_post_id}
                          </span>
                          <a
                            href={pub.external_post_url}
                            target='_blank'
                            rel='noopener noreferrer'
                            className='text-primary hover:underline text-xs font-semibold flex items-center gap-1'
                          >
                            <span>View External Post</span>
                            <Icons.externalLink className='size-3' />
                          </a>
                        </div>
                      )}

                      {pub.error_message && (
                        <div className='p-2 rounded bg-destructive/10 text-destructive text-[11px] border border-destructive/20'>
                          Error: {pub.error_message}
                        </div>
                      )}
                    </CardContent>
                  </Card>
                ))
              )}
            </TabsContent>

            {/* TAB 6: AUDIT TRAIL & EVENT LOG */}
            <TabsContent value='events' className='space-y-2 pt-3'>
              <div className='space-y-2 max-h-[500px] overflow-y-auto pr-1'>
                {workspace.events.map((e) => (
                  <div
                    key={e.id}
                    className='p-2.5 rounded-lg border bg-card text-xs flex items-start justify-between gap-3'
                  >
                    <div>
                      <div className='flex items-center gap-2'>
                        <span className='font-mono font-bold text-foreground text-[11px]'>
                          {e.event_type}
                        </span>
                        <Badge variant='secondary' className='text-[9px] py-0 px-1 font-mono'>
                          {e.actor}
                        </Badge>
                      </div>
                      {e.description && (
                        <p className='text-muted-foreground text-xs mt-0.5'>{e.description}</p>
                      )}
                    </div>
                    <span className='text-[10px] font-mono text-muted-foreground shrink-0'>
                      {new Date(e.created_at).toLocaleTimeString([], {
                        hour: '2-digit',
                        minute: '2-digit',
                        second: '2-digit'
                      })}
                    </span>
                  </div>
                ))}
              </div>
            </TabsContent>
          </Tabs>
        </div>

        {/* Right Column: Contextual AURA Assistant Chat Panel (4 cols) */}
        <div className='lg:col-span-4 flex flex-col gap-4'>
          <Card className='shadow-md border-primary/30 flex flex-col h-[650px]'>
            <CardHeader className='py-3 px-4 border-b bg-primary/[0.03]'>
              <div className='flex items-center gap-2'>
                <div className='size-7 rounded-full bg-primary/10 flex items-center justify-center text-primary'>
                  <Icons.sparkles className='size-4' />
                </div>
                <div>
                  <CardTitle className='text-sm font-bold'>AURA Assistant</CardTitle>
                  <CardDescription className='text-[10px] leading-tight'>
                    Contextual AI revision for this campaign.
                  </CardDescription>
                </div>
              </div>
            </CardHeader>

            {/* Chat Feed */}
            <CardContent className='flex-1 p-3 overflow-y-auto space-y-3 text-xs'>
              <div className='p-2.5 rounded-lg bg-muted/40 border text-[11px] text-muted-foreground leading-relaxed'>
                👋 <strong>I&apos;m your AURA Campaign Assistant.</strong> Ask me to revise content
                tone, emphasize specific event details, add disclaimers, or regenerate media
                prompts.
                <div className='text-[10px] text-primary/80 mt-1 font-medium'>
                  Guarantee: Revisions create new draft versions (v2, v3); I will never
                  auto-publish.
                </div>
              </div>

              {chatMessages.map((msg, i) => (
                <div
                  key={i}
                  className={`flex flex-col gap-1 max-w-[90%] ${
                    msg.sender === 'user' ? 'ml-auto text-right' : 'mr-auto text-left'
                  }`}
                >
                  <div
                    className={`p-2.5 rounded-xl text-xs leading-relaxed ${
                      msg.sender === 'user'
                        ? 'bg-primary text-primary-foreground font-medium rounded-br-none'
                        : 'bg-muted/80 text-foreground border rounded-bl-none'
                    }`}
                  >
                    {msg.text}

                    {msg.compliance && (
                      <div className='mt-2 pt-2 border-t border-border/40 text-[10px] font-mono text-left'>
                        <div className='font-bold text-muted-foreground'>
                          Compliance Verification:
                        </div>
                        {Object.entries(msg.compliance).map(([plat, comp]: [string, any]) => (
                          <div key={plat} className='flex items-center gap-1.5 mt-0.5'>
                            <span className='capitalize'>{plat}:</span>
                            <span
                              className={
                                comp.result === 'PASS'
                                  ? 'text-emerald-500 font-bold'
                                  : 'text-amber-500 font-bold'
                              }
                            >
                              {comp.result}
                            </span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                  <span className='text-[9px] font-mono text-muted-foreground px-1'>
                    {msg.timestamp}
                  </span>
                </div>
              ))}

              {isChatSubmitting && (
                <div className='flex items-center gap-2 p-2 text-xs text-muted-foreground'>
                  <Icons.spinner className='size-3.5 animate-spin text-primary' />
                  <span>AURA Assistant is revising campaign...</span>
                </div>
              )}
            </CardContent>

            {/* Chat Input Controls */}
            <div className='p-3 border-t bg-card space-y-2.5'>
              <div className='flex items-center justify-between text-[11px] gap-2'>
                {/* Target Platform Selector */}
                <select
                  aria-label='Target Platform'
                  value={chatTargetPlatform}
                  onChange={(e) => setChatTargetPlatform(e.target.value)}
                  className='h-7 rounded border bg-background text-[11px] px-2 text-foreground'
                >
                  <option value='all'>All Platforms</option>
                  <option value='linkedin'>LinkedIn</option>
                  <option value='instagram'>Instagram</option>
                  <option value='x'>X (Twitter)</option>
                  <option value='blog'>Blog Post</option>
                  <option value='reel'>Video Reel</option>
                </select>

                {/* Regenerate Media Checkbox */}
                <div className='flex items-center gap-1.5'>
                  <Checkbox
                    id='regen-media'
                    checked={chatRegenMedia}
                    onCheckedChange={(c) => setChatRegenMedia(Boolean(c))}
                  />
                  <Label
                    htmlFor='regen-media'
                    className='text-[10px] cursor-pointer text-muted-foreground'
                  >
                    Regen Media
                  </Label>
                </div>
              </div>

              {chatRegenMedia && (
                <div className='flex items-center gap-2 text-[10px]'>
                  <span className='text-muted-foreground font-medium'>Media Type:</span>
                  <button
                    type='button'
                    onClick={() => setChatMediaType('image')}
                    className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                      chatMediaType === 'image'
                        ? 'bg-primary text-primary-foreground'
                        : 'bg-muted text-muted-foreground'
                    }`}
                  >
                    1:1 Square
                  </button>
                  <button
                    type='button'
                    onClick={() => setChatMediaType('video')}
                    className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                      chatMediaType === 'video'
                        ? 'bg-primary text-primary-foreground'
                        : 'bg-muted text-muted-foreground'
                    }`}
                  >
                    9:16 Reel
                  </button>
                </div>
              )}

              <div className='flex items-end gap-1.5'>
                <Textarea
                  value={chatInstruction}
                  onChange={(e) => setChatInstruction(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault();
                      handleAssistantSend();
                    }
                  }}
                  placeholder='e.g., Make LinkedIn copy more concise and add compliance disclaimer...'
                  className='min-h-[50px] max-h-[100px] text-xs resize-none'
                />
                <Button
                  size='sm'
                  onClick={handleAssistantSend}
                  disabled={isChatSubmitting || !chatInstruction.trim()}
                  className='h-12 px-3 shrink-0 font-bold'
                >
                  <Icons.send className='size-3.5' />
                </Button>
              </div>
            </div>
          </Card>
        </div>
      </div>

      {/* Resubmit Review Modal */}
      <Dialog open={isResubmitOpen} onOpenChange={setIsResubmitOpen}>
        <DialogContent className='max-w-md'>
          <DialogHeader>
            <DialogTitle className='text-base font-bold'>Resubmit Campaign for Review</DialogTitle>
            <DialogDescription className='text-xs'>
              This will transition this campaign into{' '}
              <strong className='text-foreground'>Review Cycle {currentCycle + 1}</strong>, set its
              status to &apos;pending_review&apos;, and re-queue it for human reviewer approval.
            </DialogDescription>
          </DialogHeader>

          <div className='space-y-3 py-2'>
            <div className='p-2.5 rounded bg-muted/40 border text-xs space-y-1'>
              <div className='font-bold text-foreground'>{camp.title || camp.thesis}</div>
              <div className='text-muted-foreground font-mono text-[11px]'>
                Brand: {camp.brand_id?.toUpperCase()}
              </div>
            </div>

            <div className='space-y-1.5'>
              <Label className='text-xs font-semibold'>Revision Summary / Reviewer Note</Label>
              <Textarea
                value={resubmitNote}
                onChange={(e) => setResubmitNote(e.target.value)}
                placeholder='e.g., Re-generated copy via AURA Assistant; verified final watermarked graphic attached.'
                className='text-xs min-h-[80px]'
              />
            </div>
          </div>

          <DialogFooter className='gap-2'>
            <Button
              type='button'
              variant='outline'
              size='sm'
              onClick={() => setIsResubmitOpen(false)}
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
                  <span>Confirm Cycle {currentCycle + 1}</span>
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
