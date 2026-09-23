'use client';

import React, { Suspense, useEffect, useState } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { toast } from 'sonner';
import { useAuraStore } from '@/lib/demo/store';
import { DEMO_BRANDS } from '@/lib/demo/brands';
import {
  generateStudioCampaign,
  getStudioCampaign,
  generateCampaignImage,
  generateCampaignVideo,
  editCampaignContent,
  submitCampaign
} from '@/lib/api/client';
import type {
  BrandId,
  Platform,
  Language,
  StudioCampaignDetail,
  CampaignMediaItem
} from '@/lib/api/types';
import { BrandBadge } from '@/components/aura/common';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Icons } from '@/components/icons';
import { WatermarkStudio } from '@/components/aura/watermark/watermark-studio';
import { cn } from '@/lib/utils';

const STAGED_PIPELINE_STEPS = [
  'Ingesting Brand Voice & Underwriting Rules',
  'Analyzing Factual Event & Subject Constraints',
  'Groq LLM Multi-Platform Content Generation',
  'Synthesizing 1:1 Poster & 9:16 Video Prompts',
  'Persisting Static Campaign Snapshot to Database'
];

const PLATFORM_INFO: Record<Platform, { label: string; desc: string; icon: string }> = {
  linkedin: { label: 'LinkedIn', desc: 'Longform authoritative industry post', icon: 'post' },
  x: { label: 'X (Twitter)', desc: 'Concise punchy hook & thread (<280 chars)', icon: 'post' },
  instagram: { label: 'Instagram', desc: 'Editorial caption & targeted hashtags', icon: 'post' },
  blog: { label: 'Blog / Article', desc: 'Comprehensive SEO thought-leadership article', icon: 'post' },
  reel: { label: 'Reel (Video)', desc: '9:16 vertical scene-by-scene storyboard', icon: 'video' }
};

const OBJECTIVES = [
  'Awareness',
  'Education',
  'Lead Generation',
  'Thought Leadership',
  'Engagement',
  'Product Awareness'
];

const LANGUAGES: { code: Language; label: string }[] = [
  { code: 'en', label: 'English' },
  { code: 'ms', label: 'Bahasa Melayu' },
  { code: 'id', label: 'Bahasa Indonesia' },
  { code: 'th', label: 'Thai' },
  { code: 'zh', label: 'Traditional Chinese' }
];

function handleCopy(text: string, label: string) {
  navigator.clipboard.writeText(text);
  toast.success(`Copied ${label} to clipboard!`);
}

function StudioContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const campaignIdFromQuery = searchParams.get('id');

  const store = useAuraStore();

  // Workflow Stepper State: 1 = Setup, 2 = Generation, 3 = Media & Review
  const [currentWorkflowStep, setCurrentWorkflowStep] = useState<1 | 2 | 3>(1);

  // Step 1: Configuration Form State
  const [brandId, setBrandId] = useState<BrandId>('jade');
  const [objective, setObjective] = useState('Awareness');
  const [language, setLanguage] = useState<Language>('en');
  const [thesis, setThesis] = useState(
    'How jewellery businesses can eliminate transit custody risk during regional exhibitions'
  );
  const [targetAudience, setTargetAudience] = useState(
    'Jewellers, fine-art businesses, luxury asset businesses, and high-value asset owners.'
  );
  const [selectedPlatforms, setSelectedPlatforms] = useState<Platform[]>([
    'linkedin',
    'x',
    'instagram',
    'blog',
    'reel'
  ]);

  // Step 2 & 3: Generation & Snapshot State
  const [isGenerating, setIsGenerating] = useState(false);
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [campaignSnapshot, setCampaignSnapshot] = useState<StudioCampaignDetail | null>(null);
  const [activePlatformTab, setActivePlatformTab] = useState<Platform>('linkedin');

  // Inline editing state for platform content
  const [editingContentMap, setEditingContentMap] = useState<Record<string, string>>({});
  const [editingTitleMap, setEditingTitleMap] = useState<Record<string, string>>({});
  const [isSavingContent, setIsSavingContent] = useState(false);

  // Media Generation Loaders
  const [isGeneratingImage, setIsGeneratingImage] = useState(false);
  const [isGeneratingVideo, setIsGeneratingVideo] = useState(false);
  const [editableImagePrompt, setEditableImagePrompt] = useState('');
  const [editableVideoPrompt, setEditableVideoPrompt] = useState('');
  const [mediaTimestamp, setMediaTimestamp] = useState<number>(Date.now());
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Load existing campaign snapshot from URL id
  useEffect(() => {
    if (campaignIdFromQuery) {
      getStudioCampaign(campaignIdFromQuery)
        .then((detail) => {
          setCampaignSnapshot(detail);
          setBrandId(detail.brand_id);
          setObjective(detail.objective);
          setLanguage(detail.language);
          setThesis(detail.thesis);
          if (detail.image_prompt) setEditableImagePrompt(detail.image_prompt);
          if (detail.video_prompt) setEditableVideoPrompt(detail.video_prompt);

          // Populate editable content maps
          const contentMap: Record<string, string> = {};
          const titleMap: Record<string, string> = {};
          detail.contents.forEach((c) => {
            contentMap[c.platform] = c.content;
            if (c.title) titleMap[c.platform] = c.title;
          });
          setEditingContentMap(contentMap);
          setEditingTitleMap(titleMap);

          // If final media is already generated, start on Step 3, otherwise Step 2
          const hasFinal = detail.media?.some((m) => m.watermarked || m.media_stage === 'final');
          if (hasFinal) {
            setCurrentWorkflowStep(3);
          } else {
            setCurrentWorkflowStep(2);
          }
        })
        .catch((err) => {
          console.warn('Could not load campaign from URL query:', err);
        });
    }
  }, [campaignIdFromQuery]);

  // Brand selection helper
  const handleBrandSelect = (id: BrandId) => {
    setBrandId(id);
    if (id === 'jade') {
      setTargetAudience('Jewellers, fine-art ateliers, luxury asset businesses, and high-value asset owners.');
      setThesis('How jewellery ateliers can eliminate transit custody risk during regional exhibitions');
    } else if (id === 'doctorshield') {
      setTargetAudience('Private medical practitioners, clinical directors, healthcare specialists.');
      setThesis('Understanding medical council inquiry protocols and documentation integrity');
    } else if (id === 'jaguar') {
      setTargetAudience('Logistics directors, bonded corridor freight carriers, high-value couriers.');
      setThesis('Telemetry tracking and chain-of-custody handovers across ASEAN land borders');
    }
  };

  const togglePlatform = (p: Platform) => {
    setSelectedPlatforms((prev) =>
      prev.includes(p) ? (prev.length > 1 ? prev.filter((item) => item !== p) : prev) : [...prev, p]
    );
  };

  // Run Content Generation Flow
  const handleGenerate = async () => {
    if (!thesis.trim()) {
      toast.error('Please enter a campaign thesis / working angle');
      return;
    }

    setIsGenerating(true);
    setCurrentStepIndex(0);

    const interval = setInterval(() => {
      setCurrentStepIndex((prev) => (prev < STAGED_PIPELINE_STEPS.length - 1 ? prev + 1 : prev));
    }, 450);

    try {
      const result = await generateStudioCampaign({
        brand_id: brandId,
        objective,
        language,
        thesis,
        target_audience: targetAudience,
        platforms: selectedPlatforms
      });

      clearInterval(interval);
      setCampaignSnapshot(result);
      if (result.image_prompt) setEditableImagePrompt(result.image_prompt);
      if (result.video_prompt) setEditableVideoPrompt(result.video_prompt);

      const contentMap: Record<string, string> = {};
      const titleMap: Record<string, string> = {};
      result.contents.forEach((c) => {
        contentMap[c.platform] = c.content;
        if (c.title) titleMap[c.platform] = c.title;
      });
      setEditingContentMap(contentMap);
      setEditingTitleMap(titleMap);

      router.push(`/dashboard/studio?id=${result.id}`);
      setCurrentWorkflowStep(2);
      toast.success('Campaign package generated and saved to MySQL snapshot!');
    } catch (err: unknown) {
      clearInterval(interval);
      const msg = err instanceof Error ? err.message : String(err);
      toast.error(`Generation failed: ${msg}`);
    } finally {
      setIsGenerating(false);
    }
  };

  // Save edits to platform content
  const handleSavePlatformContent = async (platform: Platform) => {
    if (!campaignSnapshot) return;
    const newContent = editingContentMap[platform];
    const newTitle = editingTitleMap[platform];
    setIsSavingContent(true);
    try {
      await editCampaignContent(campaignSnapshot.id, {
        platform,
        new_content: newContent,
        new_title: newTitle,
        tag: 'OTHER',
        note: 'Direct editorial refinement in Campaign Studio'
      });
      // Refresh snapshot
      const updated = await getStudioCampaign(campaignSnapshot.id);
      setCampaignSnapshot(updated);
      toast.success(`Saved changes for ${PLATFORM_INFO[platform].label}`);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      toast.error(`Failed to save content: ${msg}`);
    } finally {
      setIsSavingContent(false);
    }
  };

  // Generate / Regenerate Image Poster (1:1 Original)
  const handleGenerateImage = async () => {
    if (!campaignSnapshot) return;
    setIsGeneratingImage(true);
    try {
      const newMedia = await generateCampaignImage(
        campaignSnapshot.id,
        editableImagePrompt || campaignSnapshot.image_prompt || undefined
      );
      setMediaTimestamp(Date.now());
      // Refresh snapshot
      const updated = await getStudioCampaign(campaignSnapshot.id);
      setCampaignSnapshot(updated);
      toast.success(`Square 1:1 poster generated (${newMedia.local_path})`);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      toast.error(`Image generation failed: ${msg}`);
    } finally {
      setIsGeneratingImage(false);
    }
  };

  // Generate / Regenerate Video Reel (9:16 Original)
  const handleGenerateVideo = async () => {
    if (!campaignSnapshot) return;
    setIsGeneratingVideo(true);
    try {
      const newMedia = await generateCampaignVideo(
        campaignSnapshot.id,
        editableVideoPrompt || campaignSnapshot.video_prompt || undefined
      );
      setMediaTimestamp(Date.now());
      // Refresh snapshot
      const updated = await getStudioCampaign(campaignSnapshot.id);
      setCampaignSnapshot(updated);
      toast.success(`Vertical 9:16 reel generated (${newMedia.local_path})`);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      toast.error(`Video generation failed: ${msg}`);
    } finally {
      setIsGeneratingVideo(false);
    }
  };

  // Callback when watermark is applied and saved in Step 3
  const handleWatermarkSaved = async (savedItem: CampaignMediaItem) => {
    setMediaTimestamp(Date.now());
    if (campaignSnapshot) {
      const updated = await getStudioCampaign(campaignSnapshot.id);
      setCampaignSnapshot(updated);
    }
  };

  // Submit to Review Queue
  const handleSubmitReview = async () => {
    if (!campaignSnapshot) return;
    setIsSubmitting(true);
    try {
      const result = await submitCampaign(campaignSnapshot.id);
      toast.success(result.message || 'Campaign successfully enqueued for review!');
      router.push('/dashboard/review');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      toast.error(`Submission failed: ${msg}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleStartNew = () => {
    setCampaignSnapshot(null);
    setCurrentWorkflowStep(1);
    router.push('/dashboard/studio');
  };

  // Helper to construct absolute media URLs
  const resolveMediaUrl = (path?: string | null) => {
    if (!path) return '';
    if (path.startsWith('http://') || path.startsWith('https://') || path.startsWith('data:')) {
      return path;
    }
    const apiBase = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    const cleanPath = path.startsWith('/') ? path : `/${path}`;
    const separator = cleanPath.includes('?') ? '&' : '?';
    return `${apiBase}${cleanPath}${separator}t=${mediaTimestamp}`;
  };

  // Separate Original and Final media items
  const allImageMedia = campaignSnapshot?.media?.filter((m) => m.media_type === 'image') || [];
  const allVideoMedia = campaignSnapshot?.media?.filter((m) => m.media_type === 'video') || [];

  const originalImage = allImageMedia.find((m) => m.media_stage === 'original') || allImageMedia[0];
  const finalImage = allImageMedia.find((m) => m.media_stage === 'final' || m.watermarked);

  const originalVideo = allVideoMedia.find((m) => m.media_stage === 'original') || allVideoMedia[0];
  const finalVideo = allVideoMedia.find((m) => m.media_stage === 'final' || m.watermarked);

  const hasMediaGenerated = Boolean(originalImage || originalVideo);
  const hasWatermarkedMedia = Boolean(finalImage || finalVideo);

  return (
    <div className='flex min-w-0 w-full flex-col gap-6 px-4 pb-16 pt-6 sm:px-6 lg:px-8 xl:px-12'>
      {/* Top Banner / Header */}
      <div className='flex flex-col md:flex-row md:items-center justify-between gap-4 border-b pb-5'>
        <div>
          <div className='flex items-center gap-2 text-xs font-semibold text-muted-foreground uppercase tracking-widest'>
            <span>AURA Operations</span>
            <span>•</span>
            <span className='text-primary'>Campaign Studio</span>
          </div>
          <h1 className='text-3xl font-bold tracking-tight text-foreground mt-1'>
            Campaign Studio
          </h1>
          <p className='text-sm text-muted-foreground mt-0.5'>
            3-Step Workflow: Configure &rarr; Multi-Channel Generation &rarr; Branded Watermarking &amp; Review.
          </p>
        </div>

        <div className='flex items-center gap-3'>
          {campaignSnapshot && (
            <Button size='sm' variant='outline' onClick={handleStartNew} className='text-xs'>
              <Icons.add className='size-3.5 mr-1.5' />
              New Campaign
            </Button>
          )}
        </div>

      </div>

      {/* 3-STEP WORKFLOW STEPPER */}
      <div className='grid grid-cols-1 md:grid-cols-3 gap-3 p-1.5 bg-muted/40 rounded-xl border'>
        {[
          {
            step: 1 as const,
            title: 'STEP 1: Campaign Setup',
            desc: 'Portfolio, objective, language, channels & thesis',
            enabled: true,
            done: Boolean(campaignSnapshot)
          },
          {
            step: 2 as const,
            title: 'STEP 2: Content Generation',
            desc: 'Multi-platform copy & 1:1 / 9:16 AI media prompts',
            enabled: Boolean(campaignSnapshot),
            done: hasMediaGenerated
          },
          {
            step: 3 as const,
            title: 'STEP 3: Media & Review',
            desc: 'Brand watermark overlay & review queue signoff',
            enabled: Boolean(campaignSnapshot),
            done: hasWatermarkedMedia
          }
        ].map((item) => {
          const isCurrent = currentWorkflowStep === item.step;
          return (
            <button
              key={item.step}
              type='button'
              disabled={!item.enabled && !campaignSnapshot}
              onClick={() => {
                if (item.enabled || campaignSnapshot) {
                  setCurrentWorkflowStep(item.step);
                }
              }}
              className={cn(
                'flex items-center gap-3 p-3 rounded-lg text-left transition-all',
                isCurrent
                  ? 'bg-card border shadow-xs font-bold text-primary ring-1 ring-primary/30'
                  : item.done
                  ? 'bg-emerald-500/5 hover:bg-card border-transparent text-foreground cursor-pointer'
                  : item.enabled
                  ? 'hover:bg-card border-transparent text-muted-foreground cursor-pointer'
                  : 'opacity-40 cursor-not-allowed text-muted-foreground'
              )}
            >
              <div
                className={cn(
                  'size-7 rounded-full flex items-center justify-center text-xs font-bold shrink-0 transition-colors',
                  isCurrent
                    ? 'bg-primary text-primary-foreground'
                    : item.done
                    ? 'bg-emerald-600 text-white'
                    : 'bg-muted text-muted-foreground'
                )}
              >
                {item.done && !isCurrent ? <Icons.check className='size-4' /> : item.step}
              </div>
              <div className='flex flex-col min-w-0'>
                <span className='text-xs font-bold truncate leading-tight'>{item.title}</span>
                <span className='text-[10px] text-muted-foreground truncate'>{item.desc}</span>
              </div>
            </button>
          );
        })}
      </div>

      {/* GENERATION IN PROGRESS TICKER */}
      {isGenerating && (
        <Card className='shadow-lg border-primary/30 bg-primary/[0.02] p-8 text-center flex flex-col items-center justify-center min-h-[420px]'>
          <div className='h-14 w-14 rounded-full bg-primary/10 flex items-center justify-center text-primary mb-4 animate-pulse'>
            <Icons.sparkles className='size-7' />
          </div>
          <h2 className='text-xl font-bold text-foreground'>
            AURA Groq Live AI is Generating
          </h2>

          <p className='text-xs text-muted-foreground max-w-md mt-1 mb-6'>
            Executing underwriting parameters, negative guidance constraints, and multi-platform media prompts.
          </p>

          <div className='flex flex-col gap-3 text-left w-full max-w-lg'>
            {STAGED_PIPELINE_STEPS.map((step, idx) => {
              const isDone = idx < currentStepIndex;
              const isCurrent = idx === currentStepIndex;
              return (
                <div
                  key={step}
                  className={`flex items-center gap-3 text-xs p-3 rounded-lg border transition-all ${
                    isCurrent
                      ? 'border-primary bg-primary/10 font-bold text-primary shadow-xs'
                      : isDone
                      ? 'border-emerald-500/20 bg-emerald-500/5 text-foreground'
                      : 'border-muted bg-muted/20 text-muted-foreground/40'
                  }`}
                >
                  {isDone ? (
                    <Icons.circleCheck className='size-4 text-emerald-600 dark:text-emerald-400 shrink-0' />
                  ) : isCurrent ? (
                    <Icons.spinner className='size-4 animate-spin text-primary shrink-0' />
                  ) : (
                    <span className='size-4 rounded-full border border-muted-foreground/30 flex items-center justify-center text-[10px] text-muted-foreground shrink-0'>
                      {idx + 1}
                    </span>
                  )}
                  <span>{step}</span>
                </div>
              );
            })}
          </div>
        </Card>
      )}

      {/* STEP 1: CAMPAIGN SETUP FORM */}
      {!isGenerating && currentWorkflowStep === 1 && (
        <div className='flex flex-col gap-6'>
          {/* 1. Brand Selection Card (Full Width Row) */}
          <Card className='shadow-xs'>
            <CardHeader className='pb-3'>
              <div className='flex items-center justify-between'>
                <CardTitle className='text-base font-bold text-foreground'>
                  1. Select Brand Portfolio
                </CardTitle>
                <Badge variant='outline' className='text-xs'>
                  Step 1 of 3
                </Badge>
              </div>
              <CardDescription className='text-xs'>
                Choose your JA Assure underwriting portfolio to load calibrated voice and boundaries.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className='grid grid-cols-1 md:grid-cols-3 gap-3.5'>
                {(['jade', 'doctorshield', 'jaguar'] as BrandId[]).map((bId) => {
                  const isSelected = brandId === bId;
                  const b = DEMO_BRANDS[bId];
                  const count = store.lessons.filter((l) => l.brand_id === bId).length;
                  return (
                    <button
                      key={bId}
                      type='button'
                      onClick={() => handleBrandSelect(bId)}
                      className={`flex flex-col text-left p-4 rounded-xl border transition-all cursor-pointer ${
                        isSelected
                          ? 'border-primary bg-primary/5 ring-2 ring-primary/40 shadow-xs'
                          : 'border-muted hover:border-foreground/30 bg-card'
                      }`}
                    >
                      <div className='flex items-center justify-between gap-2'>
                        <h4 className='font-bold text-sm text-foreground'>{b.name}</h4>
                        <Badge variant='secondary' className='text-[10px] font-mono shrink-0'>
                          {count} Rules
                        </Badge>
                      </div>
                      <p className='text-[11px] text-muted-foreground line-clamp-2 mt-1 leading-snug'>
                        {b.tagline}
                      </p>
                      <div className='mt-3 pt-2.5 border-t text-[10px] text-muted-foreground flex flex-col gap-1'>
                        <span><strong>Tone:</strong> {b.tone.slice(0, 2).join(', ')}</span>
                        <span className='line-clamp-1'><strong>Target:</strong> {b.audience}</span>
                      </div>
                    </button>
                  );
                })}
              </div>
            </CardContent>
          </Card>

          {/* 2. Campaign Working Angle & Audience Card (Full Width Row) */}
          <Card className='shadow-xs'>
            <CardHeader className='pb-3'>
              <CardTitle className='text-base font-bold'>2. Campaign Working Angle &amp; Audience</CardTitle>
              <CardDescription className='text-xs'>
                Provide your core educational subject, event facts, and target audience specification.
              </CardDescription>
            </CardHeader>
            <CardContent className='space-y-4 text-xs'>
              <div className='space-y-1.5'>
                <Label htmlFor='thesis' className='font-bold text-foreground'>
                  Campaign Thesis / Core Working Angle <span className='text-destructive'>*</span>
                </Label>
                <Textarea
                  id='thesis'
                  value={thesis}
                  onChange={(e) => setThesis(e.target.value)}
                  placeholder='e.g. How jewellery ateliers can eliminate transit custody risk during regional exhibitions'
                  rows={3}
                  className='text-xs font-sans leading-relaxed'
                />
              </div>

              <div className='space-y-1.5'>
                <Label htmlFor='audience' className='font-bold text-foreground'>
                  Target Audience (Optional)
                </Label>
                <Input
                  id='audience'
                  value={targetAudience}
                  onChange={(e) => setTargetAudience(e.target.value)}
                  placeholder='e.g. Jewellers, fine-art businesses, and luxury asset owners'
                  className='text-xs'
                />
              </div>
            </CardContent>
          </Card>

          {/* 3. Campaign Objective (Full Width Row) */}
          <Card className='shadow-xs'>
            <CardHeader className='pb-3'>
              <CardTitle className='text-base font-bold'>3. Campaign Objective</CardTitle>
              <CardDescription className='text-xs'>
                Sets marketing intent and call-to-action framing across all generated assets.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className='grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-2'>
                {OBJECTIVES.map((obj) => (
                  <Button
                    key={obj}
                    type='button'
                    variant={objective === obj ? 'default' : 'outline'}
                    size='sm'
                    onClick={() => setObjective(obj)}
                    className='justify-center text-xs h-9 font-semibold'
                  >
                    {obj}
                  </Button>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* 4. Target Market Language (Full Width Row) */}
          <Card className='shadow-xs'>
            <CardHeader className='pb-3'>
              <CardTitle className='text-base font-bold'>4. Target Market Language</CardTitle>
              <CardDescription className='text-xs'>
                Calibrates localized idioms, regional cultural context, and jurisdiction-specific disclaimers.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className='grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-2'>
                {LANGUAGES.map((lang) => (
                  <Button
                    key={lang.code}
                    type='button'
                    variant={language === lang.code ? 'default' : 'outline'}
                    size='sm'
                    onClick={() => setLanguage(lang.code)}
                    className='justify-center text-xs h-9 font-semibold'
                  >
                    {lang.label}
                  </Button>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* 5. Target Delivery Channels (Full Width Row) */}
          <Card className='shadow-xs'>
            <CardHeader className='pb-3'>
              <CardTitle className='text-base font-bold'>5. Target Delivery Channels</CardTitle>
              <CardDescription className='text-xs'>
                Select which platforms to generate dedicated content copy variants and media prompts for.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className='grid grid-cols-2 sm:grid-cols-5 gap-3'>
                {(['linkedin', 'instagram', 'x', 'reel', 'blog'] as Platform[]).map((p) => {
                  const isSelected = selectedPlatforms.includes(p);
                  const info = PLATFORM_INFO[p];
                  return (
                    <button
                      key={p}
                      type='button'
                      onClick={() => togglePlatform(p)}
                      className={`flex flex-col p-3.5 rounded-xl border text-left transition-all cursor-pointer ${
                        isSelected
                          ? 'border-primary bg-primary/5 ring-1 ring-primary/30 text-foreground'
                          : 'border-muted hover:border-foreground/20 text-muted-foreground bg-card'
                      }`}
                    >
                      <div className='flex items-center justify-between'>
                        <span className='font-bold text-xs capitalize'>{info.label}</span>
                        {isSelected ? (
                          <Icons.circleCheck className='size-4 text-primary shrink-0' />
                        ) : (
                          <span className='size-4 rounded-full border border-muted-foreground/30' />
                        )}
                      </div>
                      <span className='text-[10px] text-muted-foreground mt-1.5 line-clamp-2 leading-tight'>
                        {info.desc}
                      </span>
                    </button>
                  );
                })}
              </div>
            </CardContent>
          </Card>

          {/* 6. Ready to Generate? (Full Width Row Directly Below Delivery Channels) */}
          <Card className='shadow-xs border-primary/30 bg-primary/[0.03]'>
            <CardHeader className='pb-3'>
              <div className='flex items-center justify-between flex-wrap gap-2'>
                <div className='flex items-center gap-2'>
                  <Icons.sparkles className='size-4 text-primary' />
                  <CardTitle className='text-base font-bold text-foreground'>
                    Ready to generate?
                  </CardTitle>
                </div>
                <Badge variant='outline' className='text-xs font-mono border-primary/30 text-primary'>
                  {selectedPlatforms.length} Channel Pipeline
                </Badge>
              </div>
              <CardDescription className='text-xs'>
                Produces {selectedPlatforms.length} cross-channel copy variants, image concept prompt, and 9:16 vertical video prompt.
              </CardDescription>
            </CardHeader>
            <CardContent className='space-y-4 pt-1'>
              <div className='grid grid-cols-2 sm:grid-cols-4 gap-3 p-3.5 rounded-xl bg-muted/40 border text-xs'>
                <div className='flex flex-col'>
                  <span className='text-[10px] text-muted-foreground uppercase font-semibold'>Brand</span>
                  <span className='font-bold text-foreground capitalize mt-0.5'>{brandId}</span>
                </div>
                <div className='flex flex-col'>
                  <span className='text-[10px] text-muted-foreground uppercase font-semibold'>Channels</span>
                  <span className='font-bold text-foreground mt-0.5'>{selectedPlatforms.length} selected</span>
                </div>
                <div className='flex flex-col'>
                  <span className='text-[10px] text-muted-foreground uppercase font-semibold'>Language</span>
                  <span className='font-bold text-foreground mt-0.5'>
                    {LANGUAGES.find((l) => l.code === language)?.label || language.toUpperCase()}
                  </span>
                </div>
                <div className='flex flex-col'>
                  <span className='text-[10px] text-muted-foreground uppercase font-semibold'>Objective</span>
                  <span className='font-bold text-foreground mt-0.5'>{objective}</span>
                </div>
              </div>

              <div className='flex items-center justify-between pt-2 border-t flex-wrap gap-3'>
                <p className='text-[11px] text-muted-foreground'>
                  Calibrated for <strong>{DEMO_BRANDS[brandId].name}</strong> compliance and ASEAN regulatory guidelines.
                </p>
                <Button
                  size='lg'
                  onClick={handleGenerate}
                  className='font-bold gap-2 px-8 shadow-xs'
                >
                  <Icons.sparkles className='size-4' />
                  <span>Continue to Content Generation</span>
                  <Icons.arrowRight className='size-4' />
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* STEP 2: CONTENT GENERATION WORKSPACE */}
      {!isGenerating && currentWorkflowStep === 2 && (
        <div className='flex flex-col gap-6'>
          {/* Top Action Bar */}
          <div className='rounded-xl border bg-card p-4 shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-4'>
            <div>
              <div className='flex items-center gap-2'>
                <BrandBadge brandId={campaignSnapshot?.brand_id || brandId} />
                <Badge variant='outline' className='text-xs'>
                  {campaignSnapshot?.objective || objective} · {campaignSnapshot?.language.toUpperCase() || language.toUpperCase()}
                </Badge>
                <Badge variant='secondary' className='text-xs font-mono'>
                  {campaignSnapshot ? campaignSnapshot.id : 'Draft'}
                </Badge>
              </div>
              <h2 className='text-base font-bold text-foreground mt-1'>
                {campaignSnapshot?.thesis || thesis}
              </h2>
            </div>

            <div className='flex items-center gap-2 shrink-0'>
              <Button
                variant='outline'
                size='sm'
                onClick={handleGenerate}
                disabled={isGenerating}
                className='text-xs gap-1.5'
              >
                <Icons.sparkles className='size-3.5' />
                <span>{campaignSnapshot ? 'Regenerate Content' : 'Generate Campaign'}</span>
              </Button>

              {hasMediaGenerated && (
                <Button
                  size='sm'
                  onClick={() => setCurrentWorkflowStep(3)}
                  className='text-xs font-bold gap-1.5'
                >
                  <span>Proceed to Step 3: Media &amp; Watermark</span>
                  <Icons.arrowRight className='size-3.5' />
                </Button>
              )}
            </div>
          </div>

          {!campaignSnapshot ? (
            <Card className='border-dashed p-10 text-center'>
              <div className='flex flex-col items-center justify-center space-y-3 py-6'>
                <Icons.sparkles className='size-10 text-primary animate-pulse' />
                <h3 className='text-base font-bold'>Ready to Generate Campaign Content</h3>
                <p className='text-xs text-muted-foreground max-w-sm'>
                  Click &quot;Generate Campaign&quot; to synthesize cross-platform copy, 1:1 poster prompts, and 9:16 Reel prompts using calibrated underwriting guidelines.
                </p>
                <Button onClick={handleGenerate} className='font-bold mt-2 gap-2'>
                  <Icons.sparkles className='size-4' />
                  <span>Generate Campaign Now</span>
                </Button>
              </div>
            </Card>
          ) : (
            <>
              {/* SECTION 1: FULL-WIDTH CROSS-PLATFORM CONTENT ASSETS */}
              <Card className='shadow-xs'>
                <CardHeader className='pb-3 border-b'>
                  <div className='flex items-center justify-between'>
                    <div>
                      <CardTitle className='text-base font-bold flex items-center gap-2'>
                        <Icons.post className='size-4 text-primary' />
                        <span>Cross-Platform Content Assets</span>
                      </CardTitle>
                      <CardDescription className='text-xs mt-0.5'>
                        Verified copy tailored to platform constraints with editorial editing enabled.
                      </CardDescription>
                    </div>

                    <Badge variant='outline' className='text-xs font-mono'>
                      {campaignSnapshot.contents.length} Channels Generated
                    </Badge>
                  </div>
                </CardHeader>

                <CardContent className='p-6'>
                  <Tabs
                    value={activePlatformTab}
                    onValueChange={(val) => setActivePlatformTab(val as Platform)}
                    className='w-full'
                  >
                    <TabsList className='grid grid-cols-5 h-9 w-full mb-5'>
                      {campaignSnapshot.contents.map((item) => (
                        <TabsTrigger key={item.platform} value={item.platform} className='text-xs font-semibold capitalize'>
                          {PLATFORM_INFO[item.platform]?.label || item.platform}
                        </TabsTrigger>
                      ))}
                    </TabsList>

                    {campaignSnapshot.contents.map((item) => {
                      const platformInfo = PLATFORM_INFO[item.platform];
                      const currentText = editingContentMap[item.platform] ?? item.content;
                      const currentTitle = editingTitleMap[item.platform] ?? (item.title || '');

                      return (
                        <TabsContent key={item.platform} value={item.platform} className='space-y-4 mt-0'>
                          {/* Title / Headline (if applicable) */}
                          <div className='space-y-1.5'>
                            <Label className='text-xs font-bold text-foreground flex items-center justify-between'>
                              <span>Headline / Post Title</span>
                              <span className='text-[10px] text-muted-foreground font-normal'>Editable</span>
                            </Label>
                            <Input
                              value={currentTitle}
                              onChange={(e) =>
                                setEditingTitleMap((prev) => ({ ...prev, [item.platform]: e.target.value }))
                              }
                              placeholder='Enter post title...'
                              className='text-xs font-semibold'
                            />
                          </div>

                          {/* Body Content */}
                          <div className='space-y-1.5'>
                            <div className='flex items-center justify-between text-xs'>
                              <Label className='font-bold text-foreground'>
                                {platformInfo?.label} Body Content
                              </Label>
                              <div className='flex items-center gap-3 text-muted-foreground'>
                                <span>{currentText.length} characters</span>
                                <button
                                  type='button'
                                  onClick={() => handleCopy(currentText, platformInfo?.label || item.platform)}
                                  className='hover:text-foreground flex items-center gap-1 cursor-pointer'
                                >
                                  <Icons.share className='size-3' />
                                  <span>Copy</span>
                                </button>
                              </div>
                            </div>
                            <Textarea
                              value={currentText}
                              onChange={(e) =>
                                setEditingContentMap((prev) => ({ ...prev, [item.platform]: e.target.value }))
                              }
                              rows={7}
                              className='text-xs leading-relaxed font-sans'
                            />
                          </div>

                          {/* Hashtags */}
                          {item.hashtags && item.hashtags.length > 0 && (
                            <div className='space-y-1.5'>
                              <Label className='text-xs font-medium text-muted-foreground'>Hashtags</Label>
                              <div className='flex flex-wrap gap-1.5'>
                                {item.hashtags.map((ht) => (
                                  <Badge key={ht} variant='secondary' className='text-[11px] font-mono'>
                                    {ht}
                                  </Badge>
                                ))}
                              </div>
                            </div>
                          )}

                          {/* Script / Voiceover outline for Reel */}
                          {item.script && (
                            <div className='p-3.5 rounded-lg border bg-muted/20 text-xs space-y-1'>
                              <span className='font-bold text-foreground'>🎙️ Voiceover / Narration Script</span>
                              <p className='text-muted-foreground italic font-serif leading-relaxed'>{item.script}</p>
                            </div>
                          )}

                          {/* Save Changes Button */}
                          <div className='pt-2 flex justify-end'>
                            <Button
                              size='sm'
                              onClick={() => handleSavePlatformContent(item.platform)}
                              disabled={isSavingContent}
                              className='text-xs font-bold gap-1.5'
                            >
                              {isSavingContent ? (
                                <>
                                  <Icons.spinner className='size-3.5 animate-spin' />
                                  <span>Saving...</span>
                                </>
                              ) : (
                                <>
                                  <Icons.check className='size-3.5' />
                                  <span>Save Content Edits</span>
                                </>
                              )}
                            </Button>
                          </div>
                        </TabsContent>
                      );
                    })}
                  </Tabs>
                </CardContent>
              </Card>

              {/* SECTION 2: FULL-WIDTH AI MEDIA GENERATION PROMPTS (1 x 2 DESKTOP LAYOUT) */}
              <div className='grid grid-cols-1 md:grid-cols-2 gap-6'>
                {/* LEFT: SQUARE 1:1 POSTER CARD */}
                <Card className='shadow-xs overflow-hidden flex flex-col justify-between'>
                  <div>
                    <CardHeader className='pb-3 border-b'>
                      <div className='flex items-center justify-between'>
                        <div className='flex items-center gap-2'>
                          <Icons.media className='size-4 text-primary' />
                          <CardTitle className='text-sm font-bold'>
                            Square 1:1 Social Poster
                          </CardTitle>
                        </div>
                        <Badge variant='outline' className='text-[10px] font-mono border-primary/30 text-primary'>
                          1080×1080 · 1:1 Square
                        </Badge>
                      </div>
                      <CardDescription className='text-xs'>
                        Explicitly commands square composition, readable bold headline text, and factual event details.
                      </CardDescription>
                    </CardHeader>

                    <CardContent className='p-4 space-y-4 text-xs'>
                      <div className='space-y-1.5'>
                        <Label className='font-bold text-foreground flex items-center justify-between'>
                          <span>Poster Generation Prompt</span>
                          <span className='text-[10px] text-muted-foreground font-normal'>Editable</span>
                        </Label>
                        <Textarea
                          value={editableImagePrompt}
                          onChange={(e) => setEditableImagePrompt(e.target.value)}
                          rows={4}
                          placeholder='Square 1:1 commercial advertising poster with bold headline typography text overlay...'
                          className='text-xs font-mono leading-relaxed'
                        />
                      </div>

                      {/* Original Preview if generated */}
                      {originalImage?.local_path ? (
                        <div className='space-y-2 border rounded-lg p-3 bg-muted/20'>
                          <div className='flex items-center justify-between text-xs'>
                            <span className='font-semibold text-foreground flex items-center gap-1.5'>
                              <Icons.circleCheck className='size-3.5 text-emerald-600' />
                              <span>Original Poster Generated</span>
                            </span>
                            <Badge variant='secondary' className='text-[10px] font-mono'>
                              Original v1
                            </Badge>
                          </div>
                          <div className='relative rounded-lg overflow-hidden border bg-black w-full max-w-[240px] aspect-square mx-auto'>
                            {/* eslint-disable-next-line @next/next/no-img-element */}
                            <img
                              src={resolveMediaUrl(originalImage.local_path)}
                              alt='Generated Square Poster'
                              className='w-full h-full object-contain'
                            />
                          </div>
                        </div>
                      ) : (
                        <div className='border-2 border-dashed rounded-lg p-5 text-center bg-muted/10'>
                          <Icons.media className='size-8 text-muted-foreground mx-auto mb-1.5' />
                          <span className='font-bold text-xs text-foreground block'>Poster Not Yet Generated</span>
                          <span className='text-[11px] text-muted-foreground block mt-0.5'>
                            Click below to generate high-resolution 1:1 original poster.
                          </span>
                        </div>
                      )}
                    </CardContent>
                  </div>

                  <div className='p-4 border-t bg-muted/10 flex items-center justify-between'>
                    <Button
                      size='sm'
                      onClick={handleGenerateImage}
                      disabled={isGeneratingImage}
                      className='w-full font-bold text-xs gap-1.5'
                    >
                      {isGeneratingImage ? (
                        <>
                          <Icons.spinner className='size-3.5 animate-spin' />
                          <span>Generating 1:1 Poster...</span>
                        </>
                      ) : (
                        <>
                          <Icons.sparkles className='size-3.5' />
                          <span>{originalImage ? 'Regenerate Square Poster' : 'Generate 1:1 Square Poster'}</span>
                        </>
                      )}
                    </Button>
                  </div>
                </Card>

                {/* RIGHT: VERTICAL 9:16 REEL CARD */}
                <Card className='shadow-xs overflow-hidden flex flex-col justify-between'>
                  <div>
                    <CardHeader className='pb-3 border-b'>
                      <div className='flex items-center justify-between'>
                        <div className='flex items-center gap-2'>
                          <Icons.video className='size-4 text-primary' />
                          <CardTitle className='text-sm font-bold'>
                            Vertical 9:16 Social Reel
                          </CardTitle>
                        </div>
                        <Badge variant='outline' className='text-[10px] font-mono border-purple-500/30 text-purple-600 dark:text-purple-400'>
                          768×1365 · 9:16 Vertical
                        </Badge>
                      </div>
                      <CardDescription className='text-xs'>
                        Explicitly commands 9:16 vertical video composition, visually coherent with poster theme.
                      </CardDescription>
                    </CardHeader>

                    <CardContent className='p-4 space-y-4 text-xs'>
                      <div className='space-y-1.5'>
                        <Label className='font-bold text-foreground flex items-center justify-between'>
                          <span>Reel Video Prompt</span>
                          <span className='text-[10px] text-muted-foreground font-normal'>Editable</span>
                        </Label>
                        <Textarea
                          value={editableVideoPrompt}
                          onChange={(e) => setEditableVideoPrompt(e.target.value)}
                          rows={4}
                          placeholder='Vertical 9:16 cinematic video reel with smooth motion...'
                          className='text-xs font-mono leading-relaxed'
                        />
                      </div>

                      {/* Original Preview if generated */}
                      {originalVideo?.local_path ? (
                        <div className='space-y-2 border rounded-lg p-3 bg-muted/20'>
                          <div className='flex items-center justify-between text-xs'>
                            <span className='font-semibold text-foreground flex items-center gap-1.5'>
                              <Icons.circleCheck className='size-3.5 text-emerald-600' />
                              <span>Original Reel Generated</span>
                            </span>
                            <Badge variant='secondary' className='text-[10px] font-mono'>
                              Original v1
                            </Badge>
                          </div>
                          <div className='relative rounded-lg overflow-hidden border bg-black w-full max-w-[150px] aspect-[9/16] mx-auto'>
                            <video
                              src={resolveMediaUrl(originalVideo.local_path)}
                              controls
                              playsInline
                              className='w-full h-full object-contain'
                            />
                          </div>
                        </div>
                      ) : (
                        <div className='border-2 border-dashed rounded-lg p-5 text-center bg-muted/10'>
                          <Icons.video className='size-8 text-muted-foreground mx-auto mb-1.5' />
                          <span className='font-bold text-xs text-foreground block'>Reel Not Yet Generated</span>
                          <span className='text-[11px] text-muted-foreground block mt-0.5'>
                            Click below to generate vertical 9:16 Reel video.
                          </span>
                        </div>
                      )}
                    </CardContent>
                  </div>

                  <div className='p-4 border-t bg-muted/10 flex items-center justify-between'>
                    <Button
                      size='sm'
                      onClick={handleGenerateVideo}
                      disabled={isGeneratingVideo}
                      className='w-full font-bold text-xs gap-1.5'
                    >
                      {isGeneratingVideo ? (
                        <>
                          <Icons.spinner className='size-3.5 animate-spin' />
                          <span>Generating 9:16 Reel...</span>
                        </>
                      ) : (
                        <>
                          <Icons.sparkles className='size-3.5' />
                          <span>{originalVideo ? 'Regenerate Vertical Reel' : 'Generate 9:16 Vertical Reel'}</span>
                        </>
                      )}
                    </Button>
                  </div>
                </Card>
              </div>

              {/* Bottom Navigation CTA */}
              <div className='flex items-center justify-between p-4 rounded-xl border bg-card'>
                <div className='text-xs text-muted-foreground'>
                  {hasMediaGenerated ? (
                    <span className='text-emerald-600 font-semibold flex items-center gap-1'>
                      <Icons.circleCheck className='size-4' />
                      <span>Original media is ready! Proceed to Step 3 to customize and apply your brand watermark.</span>
                    </span>
                  ) : (
                    <span>Generate at least one media asset (Poster or Reel) before proceeding to watermarking.</span>
                  )}
                </div>

                <Button
                  size='default'
                  onClick={() => setCurrentWorkflowStep(3)}
                  disabled={!hasMediaGenerated}
                  className='font-bold gap-2'
                >
                  <span>Proceed to Step 3: Media &amp; Watermark</span>
                  <Icons.arrowRight className='size-4' />
                </Button>
              </div>
            </>
          )}
        </div>
      )}

      {/* STEP 3: MEDIA & REVIEW WORKSPACE */}
      {!isGenerating && currentWorkflowStep === 3 && campaignSnapshot && (
        <div className='flex flex-col gap-6'>
          {/* Watermark Studio Component */}
          <WatermarkStudio
            campaignId={campaignSnapshot.id}
            brandId={campaignSnapshot.brand_id}
            imageItem={finalImage || originalImage}
            videoItem={finalVideo || originalVideo}
            onWatermarkSaved={handleWatermarkSaved}
          />

          {/* Verification & Submission Box */}
          <Card className='shadow-xs border-primary/20 bg-card'>
            <CardHeader className='pb-3 border-b'>
              <div className='flex items-center justify-between'>
                <div className='flex items-center gap-2'>
                  <Icons.checks className='size-4 text-emerald-600' />
                  <CardTitle className='text-base font-bold'>
                    Submit for Verification &amp; Review Queue
                  </CardTitle>
                </div>
                <Badge
                  variant='outline'
                  className={cn(
                    'text-xs font-semibold',
                    campaignSnapshot.status === 'pending_review'
                      ? 'border-amber-500/30 bg-amber-500/10 text-amber-600'
                      : 'border-emerald-500/30 bg-emerald-500/10 text-emerald-600'
                  )}
                >
                  {campaignSnapshot.status === 'pending_review' ? 'In Review Queue' : 'Ready for Submission'}
                </Badge>
              </div>
              <CardDescription className='text-xs'>
                Once submitted, the campaign enters the human-in-the-loop review gateway for statutory compliance verification before publishing.
              </CardDescription>
            </CardHeader>

            <CardContent className='p-5 flex flex-col sm:flex-row items-center justify-between gap-4'>
              <div className='flex flex-col gap-1 text-xs text-muted-foreground'>
                <span className='flex items-center gap-1.5 text-foreground font-semibold'>
                  <Icons.circleCheck className='size-4 text-emerald-600' />
                  <span>{campaignSnapshot.contents.length} Cross-Platform Copy Variants Ready</span>
                </span>
                <span className='flex items-center gap-1.5 text-foreground font-semibold'>
                  <Icons.circleCheck className='size-4 text-emerald-600' />
                  <span>
                    {hasWatermarkedMedia
                      ? 'Final Watermarked Assets Created (poster_final_v1.png / reel_final_v1.mp4)'
                      : 'Original Media Ready (Watermark optional or applied above)'}
                  </span>
                </span>
                <span className='flex items-center gap-1.5'>
                  <Icons.circleCheck className='size-4 text-emerald-600' />
                  <span>100% Underwriting Guidelines Pre-Audited</span>
                </span>
              </div>

              <Button
                size='lg'
                onClick={handleSubmitReview}
                disabled={campaignSnapshot.status === 'pending_review' || isSubmitting}
                className='w-full sm:w-auto font-bold gap-2 min-w-[220px]'
              >
                {isSubmitting ? (
                  <>
                    <Icons.spinner className='size-4 animate-spin' />
                    <span>Submitting...</span>
                  </>
                ) : campaignSnapshot.status === 'pending_review' ? (
                  <>
                    <Icons.circleCheck className='size-4' />
                    <span>Enqueued in Review</span>
                  </>
                ) : (
                  <>
                    <Icons.checks className='size-4' />
                    <span>Submit for Verification</span>
                  </>
                )}
              </Button>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}

export default function StudioPage() {
  return (
    <Suspense fallback={<div className='p-8 text-center text-xs text-muted-foreground'>Loading Campaign Studio...</div>}>
      <StudioContent />
    </Suspense>
  );
}
