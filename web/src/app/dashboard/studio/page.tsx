'use client';

import React, { Suspense, useEffect, useState } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { toast } from 'sonner';
import { useAuraStore, auraStore } from '@/lib/demo/store';
import { DEMO_BRANDS } from '@/lib/demo/brands';
import {
  generateStudioCampaign,
  getStudioCampaign,
  generateCampaignImage,
  generateCampaignVideo,
  submitCampaignForReview
} from '@/lib/api/client';
import type {
  BrandId,
  Platform,
  Language,
  StudioCampaignDetail
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
import { useApiMode } from '@/context/api-mode-context';
import { ApiModeToggle } from '@/components/layout/api-mode-toggle';
import { cn } from '@/lib/utils';

const STAGED_PIPELINE_STEPS = [
  'Ingesting Brand Voice & Learned Lessons Memory',
  'Analyzing Topic & Platform Constraints',
  'Groq LLM Multi-Platform Content Generation',
  'Synthesizing AI Media Prompts & Snapshot Packages',
  'Persisting Static Snapshot to MySQL / Local Storage'
];

const PLATFORM_INFO: Record<Platform, { label: string; desc: string }> = {
  linkedin: { label: 'LinkedIn', desc: 'Longform authority post & carousels' },
  x: { label: 'X (Twitter)', desc: 'Concise hook & thread (<280 chars)' },
  instagram: { label: 'Instagram', desc: 'Visual concept, caption & hashtags' },
  blog: { label: 'Blog / Article', desc: 'Structured SEO thought-leadership draft' },
  reel: { label: 'Reel (Video)', desc: '9:16 vertical storyboard & voiceover' }
};

function handleCopy(text: string, label: string) {
  navigator.clipboard.writeText(text);
  toast.success(`Copied ${label} to clipboard!`);
}

function StudioContent() {

  const router = useRouter();
  const searchParams = useSearchParams();
  const campaignIdFromQuery = searchParams.get('id');

  const store = useAuraStore();

  // Mode Info from Global API Mode Context
  const { isRealApi, modeInfo, backendStatus } = useApiMode();

  // Form State
  const [brandId, setBrandId] = useState<BrandId>('jade');
  const [objective, setObjective] = useState('Awareness');
  const [language, setLanguage] = useState<Language>('en');
  const [thesis, setThesis] = useState('How jewellery businesses can eliminate transit custody risk during regional exhibitions');
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

  // Generation & Active Snapshot State
  const [isGenerating, setIsGenerating] = useState(false);
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [campaignSnapshot, setCampaignSnapshot] = useState<StudioCampaignDetail | null>(null);
  const [activePlatformTab, setActivePlatformTab] = useState<Platform>('linkedin');

  // Media Generation Loaders
  const [isGeneratingImage, setIsGeneratingImage] = useState(false);
  const [isGeneratingVideo, setIsGeneratingVideo] = useState(false);
  const [editableImagePrompt, setEditableImagePrompt] = useState('');
  const [editableVideoPrompt, setEditableVideoPrompt] = useState('');
  const [showPromptsAccordion, setShowPromptsAccordion] = useState(false);

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
        })
        .catch(() => {
          // If not found in API, check if existing in current state or reset
        });
    }
  }, [campaignIdFromQuery]);

  // Update audience when brand changes
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

    // Staged step visual ticker
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
      router.push(`/dashboard/studio?id=${result.id}`);
      toast.success('Campaign package generated and saved to snapshot database!');
    } catch (err: unknown) {
      clearInterval(interval);
      const msg = err instanceof Error ? err.message : String(err);
      toast.error(`Generation failed: ${msg}`);
    } finally {
      setIsGenerating(false);
    }
  };

  // Generate / Regenerate Image
  const handleGenerateImage = async () => {
    if (!campaignSnapshot) return;
    setIsGeneratingImage(true);
    try {
      const updatedMedia = await generateCampaignImage(
        campaignSnapshot.id,
        editableImagePrompt || campaignSnapshot.image_prompt || undefined
      );

      setCampaignSnapshot((prev) => {
        if (!prev) return null;
        const otherMedia = prev.media.filter((m) => m.media_type !== 'image');
        return {
          ...prev,
          media: [...otherMedia, updatedMedia]
        };
      });
      toast.success('Image asset generated and stored locally in storage/campaigns!');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      toast.error(`Image generation failed: ${msg}`);
    } finally {
      setIsGeneratingImage(false);
    }
  };

  // Generate / Regenerate Video
  const handleGenerateVideo = async () => {
    if (!campaignSnapshot) return;
    setIsGeneratingVideo(true);
    try {
      const updatedMedia = await generateCampaignVideo(
        campaignSnapshot.id,
        editableVideoPrompt || campaignSnapshot.video_prompt || undefined
      );

      setCampaignSnapshot((prev) => {
        if (!prev) return null;
        const otherMedia = prev.media.filter((m) => m.media_type !== 'video');
        return {
          ...prev,
          media: [...otherMedia, updatedMedia]
        };
      });
      toast.success('Reel video asset generated and stored locally in storage/campaigns!');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      toast.error(`Video generation failed: ${msg}`);
    } finally {
      setIsGeneratingVideo(false);
    }
  };

  // Submit for Verification
  const handleSubmitReview = async () => {
    if (!campaignSnapshot) return;
    try {
      const updated = await submitCampaignForReview(campaignSnapshot.id);
      setCampaignSnapshot(updated);
      auraStore.addStudioCampaignPackage(updated);
      toast.success('Campaign submitted for human verification!');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      toast.error(`Submission failed: ${msg}`);
    }
  };

  // Reset to create new campaign
  const handleStartNew = () => {
    setCampaignSnapshot(null);
    router.push('/dashboard/studio');
  };


  // Active brand lessons
  const brandLessons = store.lessons.filter((l) => l.brand_id === brandId);

  // Media items from current snapshot
  const imageMedia = campaignSnapshot?.media.find((m) => m.media_type === 'image');
  const videoMedia = campaignSnapshot?.media.find((m) => m.media_type === 'video');

  return (
    <div className='flex flex-col gap-6 p-4 md:p-8 max-w-7xl mx-auto w-full'>
      {/* Top Banner / Header */}
      <div className='flex flex-col md:flex-row md:items-center justify-between gap-4 border-b pb-5'>
        <div>
          <div className='flex items-center gap-2 text-xs font-semibold text-muted-foreground uppercase tracking-widest'>
            <span>AURA Operations</span>
            <span>•</span>
            <span className='text-primary'>Creative Engine</span>
          </div>
          <h1 className='text-3xl font-bold tracking-tight text-foreground mt-1'>
            Campaign Studio
          </h1>
          <p className='text-sm text-muted-foreground mt-0.5'>
            Turn one marketing thesis into a complete, compliance-checked content & media package.
          </p>
        </div>

        <div className='flex items-center gap-3'>
          <ApiModeToggle variant='studio' />

          {campaignSnapshot && (
            <Button size='sm' variant='outline' onClick={handleStartNew}>
              <Icons.add className='size-4 mr-1.5' />
              New Campaign
            </Button>
          )}
        </div>
      </div>

      {/* GENERATION IN PROGRESS OVERLAY / CARD */}
      {isGenerating && (
        <Card className='shadow-lg border-primary/30 bg-primary/[0.02] p-8 text-center flex flex-col items-center justify-center min-h-[440px]'>
          <div className='h-14 w-14 rounded-full bg-primary/10 flex items-center justify-center text-primary mb-4 animate-pulse'>
            <Icons.sparkles className='size-7' />
          </div>
          <h2 className='text-xl font-bold text-foreground'>
            {isRealApi ? 'AURA Live AI Engine is Generating' : 'AURA Mock Simulator is Generating'}
          </h2>
          <p className='text-xs text-muted-foreground max-w-md mt-1 mb-6'>
            {isRealApi
              ? `Executing live prompts on Groq (${modeInfo?.groq_model || 'openai/gpt-oss-20b'}) and synthesizing multi-platform compliance-checked marketing package.`
              : 'Synthesizing brand underwriting guidelines, historical reviewer feedback, and regulatory compliance rules using simulated mock templates.'}
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

      {/* MAIN VIEW: CONFIGURATION OR WORKSPACE */}
      {!isGenerating && !campaignSnapshot && (
        /* Configuration Form */
        <div className='grid grid-cols-1 lg:grid-cols-12 gap-8'>
          <div className='lg:col-span-8 flex flex-col gap-6'>
            {/* Step 1: Brand Selection */}
            <Card className='shadow-xs'>
              <CardHeader className='pb-3'>
                <div className='flex items-center justify-between'>
                  <CardTitle className='text-base font-bold text-foreground'>
                    1. Select Underwriting Portfolio
                  </CardTitle>
                  <span className='text-xs text-muted-foreground'>Step 1 of 3</span>
                </div>
                <CardDescription className='text-xs'>
                  Choose the JA Assure specialized insurance brand for tailored voice and statutory boundaries.
                </CardDescription>
              </CardHeader>
              <CardContent className='flex flex-col gap-3'>
                <div className='grid grid-cols-1 md:grid-cols-3 gap-3'>
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
                            ? 'border-primary bg-primary/5 ring-2 ring-primary/40'
                            : 'border-muted hover:border-foreground/30 bg-card'
                        }`}
                      >
                        <div className='flex items-center justify-between'>
                          <BrandBadge brandId={bId} />
                          <Badge variant='secondary' className='text-[10px] font-mono'>
                            {count} Rules Active
                          </Badge>
                        </div>
                        <h4 className='font-bold text-sm text-foreground mt-2.5'>{b.name}</h4>
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

            {/* Step 2: Campaign Parameters */}
            <Card className='shadow-xs'>
              <CardHeader className='pb-3'>
                <div className='flex items-center justify-between'>
                  <CardTitle className='text-base font-bold text-foreground'>
                    2. Campaign Thesis & Target Audience
                  </CardTitle>
                  <span className='text-xs text-muted-foreground'>Step 2 of 3</span>
                </div>
                <CardDescription className='text-xs'>
                  The core subject or risk mitigation perspective you want to educate your market on.
                </CardDescription>
              </CardHeader>
              <CardContent className='flex flex-col gap-4 text-xs'>
                <div className='flex flex-col gap-1.5'>
                  <Label htmlFor='thesis' className='font-bold text-foreground'>
                    Campaign Thesis / Core Working Angle <span className='text-destructive'>*</span>
                  </Label>
                  <Textarea
                    id='thesis'
                    value={thesis}
                    onChange={(e) => setThesis(e.target.value)}
                    placeholder='e.g. How jewellery ateliers can eliminate transit custody risk during regional exhibitions'
                    rows={3}
                    className='text-xs leading-relaxed font-sans'
                  />
                </div>

                <div className='flex flex-col gap-1.5'>
                  <Label htmlFor='audience' className='font-bold text-foreground'>
                    Refined Target Audience
                  </Label>
                  <Input
                    id='audience'
                    value={targetAudience}
                    onChange={(e) => setTargetAudience(e.target.value)}
                    placeholder='Describe the exact profile or industry role'
                    className='text-xs'
                  />
                </div>

                <div className='grid grid-cols-1 md:grid-cols-2 gap-4'>
                  <div className='flex flex-col gap-1.5'>
                    <Label className='font-bold text-foreground'>Primary Objective</Label>
                    <select
                      value={objective}
                      onChange={(e) => setObjective(e.target.value)}
                      className='h-9 rounded-md border bg-background px-3 py-1 text-xs shadow-xs focus:ring-1 focus:ring-primary'
                    >
                      <option value='Awareness'>Brand & Portfolio Awareness</option>
                      <option value='Education'>Risk Education & Exposure Audit</option>
                      <option value='Lead Generation'>Qualified B2B Lead Acquisition</option>
                      <option value='Authority & Trust'>Institutional Authority & Trust</option>
                      <option value='Retention'>Client Policy Renewal & Retention</option>
                    </select>
                  </div>

                  <div className='flex flex-col gap-1.5'>
                    <Label className='font-bold text-foreground'>Target Market Language</Label>
                    <select
                      value={language}
                      onChange={(e) => setLanguage(e.target.value as Language)}
                      className='h-9 rounded-md border bg-background px-3 py-1 text-xs shadow-xs focus:ring-1 focus:ring-primary'
                    >
                      <option value='en'>English (Singapore & Regional ASEAN)</option>
                      <option value='ms'>Bahasa Melayu (Malaysia)</option>
                      <option value='id'>Bahasa Indonesia (Indonesia)</option>
                      <option value='th'>Thai (Thailand)</option>
                      <option value='zh'>Traditional Chinese (Hong Kong & Taiwan)</option>
                    </select>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Step 3: Platform Selection */}
            <Card className='shadow-xs'>
              <CardHeader className='pb-3'>
                <div className='flex items-center justify-between'>
                  <CardTitle className='text-base font-bold text-foreground'>
                    3. Target Delivery Channels
                  </CardTitle>
                  <span className='text-xs text-muted-foreground'>Step 3 of 3</span>
                </div>
                <CardDescription className='text-xs'>
                  Select which platforms to generate dedicated content and creative prompts for.
                </CardDescription>
              </CardHeader>
              <CardContent className='flex flex-col gap-3'>
                <div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2.5'>
                  {(['linkedin', 'x', 'instagram', 'blog', 'reel'] as Platform[]).map((p) => {
                    const isSelected = selectedPlatforms.includes(p);
                    const info = PLATFORM_INFO[p];
                    return (
                      <button
                        key={p}
                        type='button'
                        onClick={() => togglePlatform(p)}
                        className={`flex flex-col text-left p-3 rounded-lg border text-xs transition-all cursor-pointer ${
                          isSelected
                            ? 'border-primary bg-primary/10 text-foreground font-semibold'
                            : 'border-muted bg-card text-muted-foreground hover:bg-muted/30'
                        }`}
                      >
                        <div className='flex items-center justify-between'>
                          <span className='capitalize font-bold'>{info.label}</span>
                          {isSelected ? (
                            <Icons.circleCheck className='size-4 text-primary shrink-0' />
                          ) : (
                            <span className='size-4 rounded-full border border-muted-foreground/30' />
                          )}
                        </div>
                        <span className='text-[11px] text-muted-foreground font-normal mt-1 leading-tight'>
                          {info.desc}
                        </span>
                      </button>
                    );
                  })}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Right Sidebar: Active Lessons & Generation CTA */}
          <div className='lg:col-span-4 flex flex-col gap-5'>
            {/* Active Learned Lessons Callout Banner */}
            <Card className='border-purple-500/20 bg-purple-500/5 shadow-xs'>
              <CardHeader className='pb-2'>
                <div className='flex items-center gap-2'>
                  <Icons.sparkles className='size-4 text-purple-600 dark:text-purple-400' />
                  <CardTitle className='text-sm font-bold text-foreground'>
                    AURA Memory Context
                  </CardTitle>
                </div>
                <CardDescription className='text-xs text-muted-foreground'>
                  Active learned rules for <strong>{DEMO_BRANDS[brandId].name}</strong> injected into Groq generator as negative guidance.
                </CardDescription>
              </CardHeader>
              <CardContent className='flex flex-col gap-2.5 pt-1 text-xs'>
                {brandLessons.length === 0 ? (
                  <p className='text-muted-foreground italic text-xs'>
                    No specific correction rules recorded yet. Reviewer feedback will automatically train this brand.
                  </p>
                ) : (
                  brandLessons.map((l) => (
                    <div
                      key={l.id}
                      className='rounded-md border border-purple-500/20 bg-background/80 p-2.5 text-[11px] flex flex-col gap-1'
                    >
                      <div className='flex items-center justify-between'>
                        <Badge variant='outline' className='text-[9px] font-bold text-purple-700 dark:text-purple-300'>
                          {l.reason_tag}
                        </Badge>
                        <span className='text-[10px] text-muted-foreground capitalize'>
                          {l.platform || 'all platforms'}
                        </span>
                      </div>
                      <p className='text-foreground/90 font-medium leading-snug'>
                        {l.note}
                      </p>
                    </div>
                  ))
                )}
                <div className='text-[10px] text-muted-foreground mt-1'>
                  🛡️ Prompts strictly forbid claims of "foolproof protection" or "guaranteed outcome" per JA Assure compliance.
                </div>
              </CardContent>
            </Card>

            {/* Launch Card */}
            <Card className='shadow-sm border-primary/20 bg-card'>
              <CardContent className='p-6 flex flex-col gap-4'>
                <div>
                  <h4 className='text-base font-bold text-foreground'>Ready to generate?</h4>
                  <p className='text-xs text-muted-foreground mt-1'>
                    Produces {selectedPlatforms.length} cross-channel copy variants, image concept prompt, and 9:16 vertical video prompt.
                  </p>
                </div>

                <div className='flex flex-col gap-2 text-xs text-muted-foreground'>
                  <div className='flex items-center justify-between'>
                    <span>Brand:</span>
                    <strong className='text-foreground capitalize'>{brandId}</strong>
                  </div>
                  <div className='flex items-center justify-between'>
                    <span>Channels:</span>
                    <strong className='text-foreground'>{selectedPlatforms.length} selected</strong>
                  </div>
                  <div className='flex items-center justify-between'>
                    <span>Language:</span>
                    <strong className='text-foreground'>{language.toUpperCase()}</strong>
                  </div>
                </div>

                <div
                  className={cn(
                    'text-xs p-2.5 rounded-lg border flex items-center justify-between',
                    isRealApi
                      ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-700 dark:text-emerald-300'
                      : 'bg-amber-500/10 border-amber-500/30 text-amber-700 dark:text-amber-300'
                  )}
                >
                  <div className='flex items-center gap-2'>
                    <span
                      className={cn(
                        'size-2 rounded-full',
                        isRealApi ? 'bg-emerald-500' : 'bg-amber-500'
                      )}
                    />
                    <span className='font-semibold'>
                      {isRealApi
                        ? `Live AI: ${modeInfo?.groq_model || 'openai/gpt-oss-20b'}`
                        : 'Mock Simulator Mode'}
                    </span>
                  </div>
                  <span className='font-mono text-[10px] uppercase font-bold opacity-80'>
                    {backendStatus === 'connected' ? 'Server Online' : 'Server Offline'}
                  </span>
                </div>

                <Button
                  onClick={handleGenerate}
                  size='lg'
                  className={cn(
                    'w-full font-bold shadow-md mt-2 transition-all',
                    isRealApi
                      ? 'bg-emerald-600 hover:bg-emerald-700 text-white'
                      : ''
                  )}
                >
                  <Icons.sparkles className='size-4 mr-2' />
                  {isRealApi
                    ? 'Generate with Real Groq AI'
                    : 'Generate with Mock Simulator'}
                </Button>
              </CardContent>
            </Card>
          </div>
        </div>
      )}

      {/* GENERATED CAMPAIGN WORKSPACE (Static Snapshot) */}
      {!isGenerating && campaignSnapshot && (
        <div className='flex flex-col gap-6'>
          {/* Campaign Metadata Header Bar */}
          <div className='rounded-xl border bg-card p-5 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4'>
            <div>
              <div className='flex items-center gap-2'>
                <BrandBadge brandId={campaignSnapshot.brand_id} />
                <Badge
                  variant='outline'
                  className={
                    campaignSnapshot.status === 'pending_review'
                      ? 'bg-amber-500/10 text-amber-700 dark:text-amber-400 border-amber-500/30'
                      : campaignSnapshot.status === 'approved'
                      ? 'bg-blue-500/10 text-blue-700 dark:text-blue-400 border-blue-500/30'
                      : 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/30'
                  }
                >
                  {campaignSnapshot.status === 'pending_review'
                    ? 'In Review Queue'
                    : campaignSnapshot.status === 'approved'
                    ? 'Approved'
                    : 'Generated Snapshot'}
                </Badge>
                <span className='text-xs font-mono text-muted-foreground'>
                  {campaignSnapshot.id}
                </span>
              </div>
              <h2 className='text-xl font-bold text-foreground mt-2'>
                {campaignSnapshot.thesis}
              </h2>
              <div className='flex flex-wrap items-center gap-3 text-xs text-muted-foreground mt-1'>
                <span>Objective: <strong>{campaignSnapshot.objective}</strong></span>
                <span>•</span>
                <span>Language: <strong>{campaignSnapshot.language.toUpperCase()}</strong></span>
                <span>•</span>
                <span>Platforms: <strong>{campaignSnapshot.platforms.join(', ')}</strong></span>
                <span>•</span>
                <span>Created: {new Date(campaignSnapshot.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
              </div>
            </div>

            <div className='flex items-center gap-3 shrink-0'>
              <Button
                variant={campaignSnapshot.status === 'pending_review' ? 'secondary' : 'default'}
                onClick={handleSubmitReview}
                disabled={campaignSnapshot.status === 'pending_review'}
                size='default'
                className='font-bold'
              >
                <Icons.checks className='size-4 mr-2' />
                {campaignSnapshot.status === 'pending_review'
                  ? 'Submitted to Review'
                  : 'Submit for Verification'}
              </Button>
            </div>
          </div>

          {/* Submission Notice Banner */}
          {campaignSnapshot.status === 'pending_review' && (
            <div className='rounded-xl border border-amber-500/30 bg-amber-500/10 p-4 flex items-center justify-between gap-4'>
              <div className='flex items-center gap-3'>
                <Icons.clock className='size-5 text-amber-600 dark:text-amber-400 shrink-0' />
                <div className='text-xs'>
                  <strong className='text-foreground font-bold'>
                    Campaign Package Enqueued for Human Review
                  </strong>
                  <p className='text-muted-foreground mt-0.5'>
                    All copy variants and media assets are locked in the Human-in-the-Loop Gateway. Nothing can publish without approval.
                  </p>
                </div>
              </div>
              <Button
                size='sm'
                variant='outline'
                onClick={() => router.push('/dashboard/review')}
              >
                Open Review Queue
                <Icons.arrowRight className='size-3.5 ml-1.5' />
              </Button>

            </div>
          )}

          {/* Main Two-Column Workspace */}
          <div className='grid grid-cols-1 lg:grid-cols-12 gap-8'>
            {/* Left Column: Platform Content Tabs & Previews */}
            <div className='lg:col-span-7 flex flex-col gap-6'>
              <Card className='shadow-xs'>
                <CardHeader className='pb-3 border-b'>
                  <div className='flex items-center justify-between'>
                    <div>
                      <CardTitle className='text-base font-bold text-foreground'>
                        Cross-Platform Content Assets
                      </CardTitle>
                      <CardDescription className='text-xs'>
                        Static campaign package snapshot. Refreshing does not re-invoke Groq.
                      </CardDescription>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className='pt-4 flex flex-col gap-4'>
                  {/* Platform Tabs */}
                  <Tabs
                    value={activePlatformTab}
                    onValueChange={(val) => setActivePlatformTab(val as Platform)}
                    className='w-full'
                  >
                    <TabsList className='w-full grid grid-cols-5 h-10'>
                      {campaignSnapshot.platforms.map((p) => (
                        <TabsTrigger key={p} value={p} className='text-xs capitalize'>
                          {p}
                        </TabsTrigger>
                      ))}
                    </TabsList>

                    {/* LinkedIn Tab */}
                    <TabsContent value='linkedin' className='mt-4 flex flex-col gap-4'>
                      {(() => {
                        const item = campaignSnapshot.contents.find((c) => c.platform === 'linkedin');
                        if (!item) return <p className='text-xs text-muted-foreground'>No LinkedIn content generated.</p>;
                        return (
                          <div className='flex flex-col gap-4'>
                            <div className='flex items-center justify-between'>
                              <span className='text-xs font-bold uppercase tracking-wider text-muted-foreground'>
                                Longform Authority Post
                              </span>
                              <Button
                                size='xs'
                                variant='outline'
                                onClick={() => handleCopy(item.content, 'LinkedIn Post')}
                              >
                                <Icons.forms className='size-3.5 mr-1' />
                                Copy Text
                              </Button>
                            </div>
                            {item.title && (
                              <h4 className='text-sm font-bold text-foreground'>{item.title}</h4>
                            )}
                            <div className='rounded-lg bg-muted/30 border p-4 text-xs font-sans whitespace-pre-wrap leading-relaxed max-h-72 overflow-y-auto'>
                              {item.content}
                            </div>
                            {item.hashtags.length > 0 && (
                              <div className='flex flex-wrap gap-1.5'>
                                {item.hashtags.map((h) => (
                                  <Badge key={h} variant='secondary' className='text-[10px]'>
                                    {h}
                                  </Badge>
                                ))}
                              </div>
                            )}

                            {/* Social Feed Preview Card */}
                            <div className='mt-2 rounded-xl border bg-card p-4 shadow-sm text-xs'>
                              <div className='flex items-center gap-2.5 mb-3'>
                                <div className='h-9 w-9 rounded-full bg-primary/20 text-primary flex items-center justify-center font-bold text-xs'>
                                  JA
                                </div>
                                <div>
                                  <div className='font-bold text-foreground flex items-center gap-1.5'>
                                    JA Assure · {DEMO_BRANDS[campaignSnapshot.brand_id].name}
                                    <Badge variant='outline' className='text-[9px] py-0'>Promoted</Badge>
                                  </div>
                                  <div className='text-[10px] text-muted-foreground'>
                                    Specialist Underwriting & Risk Advisory • 1d
                                  </div>
                                </div>
                              </div>
                              <p className='whitespace-pre-wrap leading-relaxed text-foreground/90 font-sans text-xs line-clamp-4'>
                                {item.content}
                              </p>
                              <div className='mt-2 text-primary font-medium text-[11px]'>
                                {item.hashtags.join(' ')}
                              </div>
                              <div className='mt-3 pt-2.5 border-t flex items-center justify-between text-[11px] text-muted-foreground'>
                                <span>👍 84 endorsements</span>
                                <span>16 comments</span>
                              </div>
                            </div>
                          </div>
                        );
                      })()}
                    </TabsContent>

                    {/* X Tab */}
                    <TabsContent value='x' className='mt-4 flex flex-col gap-4'>
                      {(() => {
                        const item = campaignSnapshot.contents.find((c) => c.platform === 'x');
                        if (!item) return <p className='text-xs text-muted-foreground'>No X content generated.</p>;
                        const charCount = item.content.length;
                        const isValid = charCount <= 280;
                        return (
                          <div className='flex flex-col gap-4'>
                            <div className='flex items-center justify-between'>
                              <div className='flex items-center gap-2'>
                                <span className='text-xs font-bold uppercase tracking-wider text-muted-foreground'>
                                  Hook Post
                                </span>
                                <Badge
                                  variant='outline'
                                  className={`text-[10px] font-mono ${
                                    isValid ? 'text-emerald-600 dark:text-emerald-400' : 'text-destructive'
                                  }`}
                                >
                                  {charCount} / 280 characters
                                </Badge>
                              </div>
                              <Button
                                size='xs'
                                variant='outline'
                                onClick={() => handleCopy(item.content, 'X Post')}
                              >
                                <Icons.forms className='size-3.5 mr-1' />
                                Copy
                              </Button>
                            </div>
                            <div className='rounded-lg bg-muted/30 border p-4 text-xs font-sans whitespace-pre-wrap leading-relaxed'>
                              {item.content}
                            </div>
                            {item.hashtags.length > 0 && (
                              <div className='flex flex-wrap gap-1.5'>
                                {item.hashtags.map((h) => (
                                  <Badge key={h} variant='secondary' className='text-[10px]'>
                                    {h}
                                  </Badge>
                                ))}
                              </div>
                            )}

                            {/* X Preview */}
                            <div className='mt-2 rounded-xl border bg-card p-4 shadow-sm text-xs'>
                              <div className='flex items-center gap-2 mb-2'>
                                <div className='h-7 w-7 rounded-full bg-foreground text-background flex items-center justify-center font-bold text-[10px]'>
                                  JA
                                </div>
                                <div>
                                  <span className='font-bold text-foreground'>JA Assure Group</span>{' '}
                                  <span className='text-muted-foreground text-[10px]'>@jaassure</span>
                                </div>
                              </div>
                              <p className='text-xs leading-relaxed text-foreground/90 font-sans'>
                                {item.content}
                              </p>
                              <div className='mt-2 text-primary text-[11px]'>{item.hashtags.join(' ')}</div>
                            </div>
                          </div>
                        );
                      })()}
                    </TabsContent>

                    {/* Instagram Tab */}
                    <TabsContent value='instagram' className='mt-4 flex flex-col gap-4'>
                      {(() => {
                        const item = campaignSnapshot.contents.find((c) => c.platform === 'instagram');
                        if (!item) return <p className='text-xs text-muted-foreground'>No Instagram content generated.</p>;
                        return (
                          <div className='flex flex-col gap-4'>
                            {item.visual_concept && (
                              <div className='rounded-lg border border-primary/20 bg-primary/5 p-3 flex flex-col gap-1 text-xs'>
                                <span className='font-bold text-primary flex items-center gap-1.5'>
                                  <Icons.media className='size-3.5' /> Visual Creative Concept
                                </span>
                                <p className='text-muted-foreground'>{item.visual_concept}</p>
                              </div>
                            )}

                            <div className='flex items-center justify-between'>
                              <span className='text-xs font-bold uppercase tracking-wider text-muted-foreground'>
                                Post Caption
                              </span>
                              <Button
                                size='xs'
                                variant='outline'
                                onClick={() => handleCopy(item.content, 'Instagram Caption')}
                              >
                                <Icons.forms className='size-3.5 mr-1' />
                                Copy Caption
                              </Button>
                            </div>
                            <div className='rounded-lg bg-muted/30 border p-4 text-xs font-sans whitespace-pre-wrap leading-relaxed max-h-56 overflow-y-auto'>
                              {item.content}
                            </div>
                            {item.hashtags.length > 0 && (
                              <div className='flex flex-wrap gap-1.5'>
                                {item.hashtags.map((h) => (
                                  <span key={h} className='text-[10px] text-primary font-medium'>
                                    {h}
                                  </span>
                                ))}
                              </div>
                            )}

                            {/* Direct Action */}
                            <div className='flex items-center justify-between border-t pt-3'>
                              <span className='text-xs text-muted-foreground'>
                                Need image asset for this post?
                              </span>
                              <Button size='sm' onClick={handleGenerateImage} disabled={isGeneratingImage}>
                                {isGeneratingImage ? (
                                  <>
                                    <Icons.spinner className='size-3.5 animate-spin mr-1.5' />
                                    Generating Image...
                                  </>
                                ) : (
                                  <>
                                    <Icons.media className='size-3.5 mr-1.5' />
                                    Generate Image
                                  </>
                                )}
                              </Button>
                            </div>
                          </div>
                        );
                      })()}
                    </TabsContent>

                    {/* Blog Tab */}
                    <TabsContent value='blog' className='mt-4 flex flex-col gap-4'>
                      {(() => {
                        const item = campaignSnapshot.contents.find((c) => c.platform === 'blog');
                        if (!item) return <p className='text-xs text-muted-foreground'>No Blog article generated.</p>;
                        return (
                          <div className='flex flex-col gap-4'>
                            <div className='flex items-center justify-between'>
                              <span className='text-xs font-bold uppercase tracking-wider text-muted-foreground'>
                                SEO Thought-Leadership Article
                              </span>
                              <Button
                                size='xs'
                                variant='outline'
                                onClick={() => handleCopy(item.content, 'Blog Article')}
                              >
                                <Icons.forms className='size-3.5 mr-1' />
                                Copy Full Article
                              </Button>
                            </div>
                            {item.title && (
                              <h3 className='text-base font-bold text-foreground'>{item.title}</h3>
                            )}
                            <div className='rounded-lg bg-muted/30 border p-5 text-xs font-serif whitespace-pre-wrap leading-relaxed max-h-96 overflow-y-auto'>
                              {item.content}
                            </div>
                          </div>
                        );
                      })()}
                    </TabsContent>

                    {/* Reel Tab */}
                    <TabsContent value='reel' className='mt-4 flex flex-col gap-4'>
                      {(() => {
                        const item = campaignSnapshot.contents.find((c) => c.platform === 'reel');
                        if (!item) return <p className='text-xs text-muted-foreground'>No Reel script generated.</p>;
                        return (
                          <div className='flex flex-col gap-4'>
                            <div className='flex items-center justify-between'>
                              <div className='flex items-center gap-2'>
                                <span className='text-xs font-bold uppercase tracking-wider text-muted-foreground'>
                                  Vertical Shortform Storyboard
                                </span>
                                <Badge variant='secondary' className='text-[10px]'>
                                  Duration: 45s
                                </Badge>
                              </div>
                              <Button
                                size='xs'
                                variant='outline'
                                onClick={() => handleCopy(item.script || item.content, 'Reel Script')}
                              >
                                <Icons.forms className='size-3.5 mr-1' />
                                Copy Script
                              </Button>
                            </div>

                            {item.title && (
                              <h4 className='text-sm font-bold text-foreground'>{item.title}</h4>
                            )}

                            {/* Voiceover block */}
                            <div className='rounded-lg border bg-card p-3.5 flex flex-col gap-1.5 text-xs'>
                              <span className='font-bold text-foreground flex items-center gap-1.5'>
                                🎙️ Voiceover Narration Script
                              </span>
                              <p className='text-foreground/90 font-serif leading-relaxed italic'>
                                "{item.script || item.content}"
                              </p>
                            </div>

                            {/* Direct Action */}
                            <div className='flex items-center justify-between border-t pt-3'>
                              <span className='text-xs text-muted-foreground'>
                                Render vertical video with Minimax Falcon model?
                              </span>
                              <Button size='sm' onClick={handleGenerateVideo} disabled={isGeneratingVideo}>
                                {isGeneratingVideo ? (
                                  <>
                                    <Icons.spinner className='size-3.5 animate-spin mr-1.5' />
                                    Rendering Video...
                                  </>
                                ) : (
                                  <>
                                    <Icons.video className='size-3.5 mr-1.5' />
                                    Generate Video
                                  </>
                                )}
                              </Button>
                            </div>
                          </div>
                        );
                      })()}
                    </TabsContent>
                  </Tabs>
                </CardContent>
              </Card>

              {/* Collapsible AI Media Prompts Accordion */}
              <Card className='shadow-xs'>
                <CardHeader className='py-3 px-5 border-b cursor-pointer' onClick={() => setShowPromptsAccordion(!showPromptsAccordion)}>
                  <div className='flex items-center justify-between'>
                    <div className='flex items-center gap-2'>
                      <Icons.code className='size-4 text-primary' />
                      <CardTitle className='text-xs font-bold text-foreground'>
                        AI Media Generation Prompts
                      </CardTitle>
                    </div>
                    <Button variant='ghost' size='xs'>
                      {showPromptsAccordion ? 'Hide Prompts' : 'Show Prompts'}
                      <Icons.chevronDown className={`size-3 ml-1 transition-transform ${showPromptsAccordion ? 'rotate-180' : ''}`} />
                    </Button>
                  </div>
                </CardHeader>
                {showPromptsAccordion && (
                  <CardContent className='p-4 flex flex-col gap-4 text-xs'>
                    <div className='flex flex-col gap-1.5'>
                      <Label className='font-bold text-foreground flex items-center justify-between'>
                        <span>Image Prompt (FAL Flux / Local)</span>
                        <span className='text-[10px] text-muted-foreground font-normal'>Editable</span>
                      </Label>
                      <Textarea
                        value={editableImagePrompt}
                        onChange={(e) => setEditableImagePrompt(e.target.value)}
                        rows={3}
                        className='text-xs font-mono'
                      />
                    </div>

                    <div className='flex flex-col gap-1.5'>
                      <Label className='font-bold text-foreground flex items-center justify-between'>
                        <span>Video Prompt (FAL Minimax / Local)</span>
                        <span className='text-[10px] text-muted-foreground font-normal'>Editable</span>
                      </Label>
                      <Textarea
                        value={editableVideoPrompt}
                        onChange={(e) => setEditableVideoPrompt(e.target.value)}
                        rows={3}
                        className='text-xs font-mono'
                      />
                    </div>
                  </CardContent>
                )}
              </Card>
            </div>

            {/* Right Column: Dedicated Media Generation Panel */}
            <div className='lg:col-span-5 flex flex-col gap-6'>
              {/* Image Generation Slot */}
              <Card className='shadow-xs overflow-hidden'>
                <CardHeader className='pb-3 border-b'>
                  <div className='flex items-center justify-between'>
                    <div className='flex items-center gap-2'>
                      <Icons.media className='size-4 text-primary' />
                      <CardTitle className='text-sm font-bold text-foreground'>
                        Campaign Image Asset
                      </CardTitle>
                    </div>
                    <Badge variant='outline' className='text-[10px] font-mono'>
                      {imageMedia?.model || modeInfo?.image_model || 'fal-ai/flux/schnell'}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent className='p-4 flex flex-col gap-3'>
                  {imageMedia && imageMedia.local_path ? (
                    <div className='flex flex-col gap-3'>
                      <div className='relative rounded-lg overflow-hidden border bg-muted/40 aspect-16/10 flex items-center justify-center'>
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img
                          src={imageMedia.local_path}
                          alt='Campaign creative visual render'
                          className='w-full h-full object-cover'
                        />
                      </div>
                      <div className='flex items-center justify-between text-xs'>
                        <span className='text-[11px] text-emerald-600 dark:text-emerald-400 font-semibold flex items-center gap-1'>
                          <Icons.circleCheck className='size-3.5' /> Stored locally: ✓
                        </span>
                        <span className='text-[10px] font-mono text-muted-foreground'>
                          {imageMedia.local_path}
                        </span>
                      </div>
                      <div className='flex items-center justify-between pt-2 border-t'>
                        <Button
                          size='xs'
                          variant='outline'
                          onClick={() => window.open(imageMedia.local_path || '#', '_blank')}
                        >
                          <Icons.externalLink className='size-3 mr-1' />
                          View Full Size
                        </Button>
                        <Button
                          size='xs'
                          onClick={handleGenerateImage}
                          disabled={isGeneratingImage}
                        >
                          {isGeneratingImage ? (
                            <>
                              <Icons.spinner className='size-3 animate-spin mr-1' />
                              Regenerating...
                            </>
                          ) : (
                            'Regenerate Image'
                          )}
                        </Button>
                      </div>
                    </div>
                  ) : (
                    <div className='rounded-lg border-2 border-dashed p-6 text-center flex flex-col items-center justify-center min-h-[180px] bg-muted/10'>
                      <div className='h-10 w-10 rounded-full bg-muted flex items-center justify-center text-muted-foreground mb-2'>
                        <Icons.media className='size-5' />
                      </div>
                      <h5 className='text-xs font-bold text-foreground'>No Image Generated Yet</h5>
                      <p className='text-[11px] text-muted-foreground max-w-xs mt-1 mb-3'>
                        Synthesize an editorial commercial photo matching this campaign's prompt.
                      </p>
                      <Button
                        size='sm'
                        onClick={handleGenerateImage}
                        disabled={isGeneratingImage}
                      >
                        {isGeneratingImage ? (
                          <>
                            <Icons.spinner className='size-3.5 animate-spin mr-1.5' />
                            Generating Image...
                          </>
                        ) : (
                          <>
                            <Icons.sparkles className='size-3.5 mr-1.5' />
                            Generate Image
                          </>
                        )}
                      </Button>
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Video Generation Slot */}
              <Card className='shadow-xs overflow-hidden'>
                <CardHeader className='pb-3 border-b'>
                  <div className='flex items-center justify-between'>
                    <div className='flex items-center gap-2'>
                      <Icons.video className='size-4 text-purple-600 dark:text-purple-400' />
                      <CardTitle className='text-sm font-bold text-foreground'>
                        Reel Video Asset (9:16)
                      </CardTitle>
                    </div>
                    <Badge variant='outline' className='text-[10px] font-mono'>
                      {videoMedia?.model || modeInfo?.video_model || 'minimax/h3-max-turbo/text-to-video'}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent className='p-4 flex flex-col gap-3'>
                  {videoMedia && videoMedia.local_path ? (
                    <div className='flex flex-col gap-3'>
                      <div className='relative rounded-lg overflow-hidden border bg-black/90 aspect-9/16 max-h-[380px] mx-auto flex items-center justify-center w-full'>
                        <video
                          controls
                          playsInline
                          className='w-full h-full object-contain'
                          src={videoMedia.local_path}
                        >
                          <track kind='captions' />
                          Your browser does not support HTML video playback.
                        </video>
                      </div>
                      <div className='flex items-center justify-between text-xs'>
                        <span className='text-[11px] text-emerald-600 dark:text-emerald-400 font-semibold flex items-center gap-1'>
                          <Icons.circleCheck className='size-3.5' /> Stored locally: ✓
                        </span>
                        <span className='text-[10px] font-mono text-muted-foreground'>
                          {videoMedia.local_path}
                        </span>
                      </div>
                      <div className='flex items-center justify-between pt-2 border-t'>
                        <Button
                          size='xs'
                          variant='outline'
                          onClick={() => window.open(videoMedia.local_path || '#', '_blank')}
                        >
                          <Icons.externalLink className='size-3 mr-1' />
                          Open Video
                        </Button>
                        <Button
                          size='xs'
                          onClick={handleGenerateVideo}
                          disabled={isGeneratingVideo}
                        >
                          {isGeneratingVideo ? (
                            <>
                              <Icons.spinner className='size-3 animate-spin mr-1' />
                              Regenerating...
                            </>
                          ) : (
                            'Regenerate Video'
                          )}
                        </Button>
                      </div>
                    </div>
                  ) : (
                    <div className='rounded-lg border-2 border-dashed p-6 text-center flex flex-col items-center justify-center min-h-[180px] bg-muted/10'>
                      <div className='h-10 w-10 rounded-full bg-muted flex items-center justify-center text-muted-foreground mb-2'>
                        <Icons.video className='size-5' />
                      </div>
                      <h5 className='text-xs font-bold text-foreground'>No Video Rendered Yet</h5>
                      <p className='text-[11px] text-muted-foreground max-w-xs mt-1 mb-3'>
                        Generate a 9:16 vertical shortform video using FAL MiniMax.
                      </p>
                      <Button
                        size='sm'
                        onClick={handleGenerateVideo}
                        disabled={isGeneratingVideo}
                      >
                        {isGeneratingVideo ? (
                          <>
                            <Icons.spinner className='size-3.5 animate-spin mr-1.5' />
                            Rendering Video...
                          </>
                        ) : (
                          <>
                            <Icons.sparkles className='size-3.5 mr-1.5' />
                            Generate Video
                          </>
                        )}
                      </Button>
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Local Storage System Card */}
              <div className='rounded-xl border bg-muted/30 p-4 flex items-start gap-3 text-xs'>
                <Icons.info className='size-4 text-primary mt-0.5 shrink-0' />
                <div className='flex flex-col gap-1 text-muted-foreground'>
                  <strong className='text-foreground font-semibold'>
                    Local File Storage & Database Verification
                  </strong>
                  <p className='text-[11px] leading-relaxed'>
                    Every image and vertical reel is saved directly to{' '}
                    <code className='bg-muted px-1 py-0.5 rounded font-mono text-[10px] text-foreground'>
                      storage/campaigns/{campaignSnapshot.id}/
                    </code>{' '}
                    and registered in MySQL.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function StudioPage() {
  return (
    <Suspense
      fallback={
        <div className='flex items-center justify-center min-h-[400px]'>
          <Icons.spinner className='size-8 animate-spin text-primary' />
        </div>
      }
    >
      <StudioContent />
    </Suspense>
  );
}
