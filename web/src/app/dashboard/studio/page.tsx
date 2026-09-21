'use client';

import React, { useState } from 'react';
import { toast } from 'sonner';
import { useAuraStore, auraStore } from '@/lib/demo/store';
import { DEMO_BRANDS } from '@/lib/demo/brands';
import { generateCampaignAssets } from '@/lib/demo/campaign-generator';
import type { BrandId, Platform, Language } from '@/lib/api/types';
import type { ExtendedAsset } from '@/lib/demo/assets';
import { BrandBadge, ComplianceVerdictBadge } from '@/components/aura/common';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Icons } from '@/components/icons';

const STAGED_PIPELINE_STEPS = [
  'Retrieved relevant lessons from AURA memory',
  'Analysed brand voice guidelines and do/don’t boundaries',
  'Generated multi-platform content variants',
  'Checked compliance against 12 statutory and tone rules',
  'Localised copy nuances for target market',
  'Prepared human review package'
];

export default function StudioPage() {
  const store = useAuraStore();

  // Form State
  const [brandId, setBrandId] = useState<BrandId>('jade');
  const [topic, setTopic] = useState('How jewellery businesses can reduce transit risk');
  const [goal, setGoal] = useState('Education');
  const [selectedPlatforms, setSelectedPlatforms] = useState<Platform[]>([
    'linkedin',
    'instagram',
    'x',
    'reel',
    'blog'
  ]);
  const [language, setLanguage] = useState<Language>('en');
  const [tone, setTone] = useState('Premium & Educational');

  // Generation Pipeline State
  const [isGenerating, setIsGenerating] = useState(false);
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [generatedAssets, setGeneratedAssets] = useState<ExtendedAsset[] | null>(null);
  const [activePlatformTab, setActivePlatformTab] = useState<string>('linkedin');
  const [selectedVariants, setSelectedVariants] = useState<Record<string, string>>({});

  // Auto-update tone when brand changes
  const handleBrandChange = (newBrand: BrandId) => {
    setBrandId(newBrand);
    if (newBrand === 'jade') setTone('Authoritative & Premium');
    if (newBrand === 'doctorshield') setTone('Calm, Reassuring & Educational');
    if (newBrand === 'jaguar') setTone('Precise, Confident & Operational');
  };

  const togglePlatform = (p: Platform) => {
    setSelectedPlatforms((prev) =>
      prev.includes(p) ? (prev.length > 1 ? prev.filter((item) => item !== p) : prev) : [...prev, p]
    );
  };

  const handleGenerate = async () => {
    if (!topic.trim()) {
      toast.error('Please enter a campaign topic');
      return;
    }

    setIsGenerating(true);
    setGeneratedAssets(null);
    setCurrentStepIndex(0);

    for (let i = 0; i < STAGED_PIPELINE_STEPS.length; i++) {
      setCurrentStepIndex(i);
      await new Promise((res) => setTimeout(res, 450));
    }

    const assets = generateCampaignAssets({
      brandId,
      topic,
      goal,
      platforms: selectedPlatforms,
      language,
      tone
    });

    setGeneratedAssets(assets);
    setIsGenerating(false);

    // Default variant selections
    const initialVariants: Record<string, string> = {};
    assets.forEach((a) => {
      if (!initialVariants[a.platform]) {
        initialVariants[a.platform] = a.variant;
      }
    });
    setSelectedVariants(initialVariants);

    toast.success('Campaign package generated with 5 cross-platform assets');
  };

  const handleSendToReview = () => {
    if (!generatedAssets) return;

    auraStore.addGeneratedCampaign({
      brandId,
      topic,
      goal,
      platforms: selectedPlatforms,
      language,
      assets: generatedAssets
    });

    toast.success('All generated variants enqueued to Review Queue!');
  };

  return (
    <div className='flex flex-col gap-6 p-4 md:p-8 max-w-7xl mx-auto w-full'>
      {/* Header */}
      <div className='border-b pb-5'>
        <div className='flex items-center gap-2 text-xs font-semibold text-muted-foreground uppercase tracking-widest'>
          <span>AURA Operations</span>
          <span>•</span>
          <span className='text-primary'>Creative Engine</span>
        </div>
        <h1 className='text-3xl font-bold tracking-tight text-foreground mt-1'>
          Campaign Studio
        </h1>
        <p className='text-sm text-muted-foreground mt-0.5'>
          Turn one marketing idea into a complete, compliance-checked content package.
        </p>
      </div>

      {/* Main Studio Grid */}
      <div className='grid grid-cols-1 lg:grid-cols-12 gap-8'>
        {/* Left Form: Campaign Config */}
        <div className='lg:col-span-5 flex flex-col gap-5'>
          <Card className='shadow-xs'>
            <CardHeader className='pb-3'>
              <CardTitle className='text-base font-bold text-foreground'>
                Campaign Configuration
              </CardTitle>
              <CardDescription className='text-xs'>
                Define the core thesis and target parameters for JA Assure underwriting portfolios.
              </CardDescription>
            </CardHeader>
            <CardContent className='flex flex-col gap-4 text-xs'>
              {/* Brand Selector */}
              <div className='flex flex-col gap-1.5'>
                <Label className='text-xs font-semibold'>Target Brand</Label>
                <div className='grid grid-cols-3 gap-2'>
                  {(['jade', 'doctorshield', 'jaguar'] as BrandId[]).map((bId) => {
                    const isSelected = brandId === bId;
                    return (
                      <button
                        key={bId}
                        type='button'
                        onClick={() => handleBrandChange(bId)}
                        className={`flex flex-col items-center justify-center p-2.5 rounded-lg border text-xs font-semibold transition-all ${
                          isSelected
                            ? 'border-primary bg-primary/10 text-primary ring-1 ring-primary'
                            : 'border-muted hover:bg-muted/40 text-muted-foreground'
                        }`}
                      >
                        <span className='capitalize'>{bId === 'doctorshield' ? 'DoctorShield' : bId === 'jaguar' ? 'Jaguar' : 'Jade'}</span>
                        <span className='text-[10px] font-normal text-muted-foreground mt-0.5'>
                          {bId === 'jade' ? 'Jewellery/Art' : bId === 'doctorshield' ? 'Medical' : 'Logistics'}
                        </span>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Topic Input */}
              <div className='flex flex-col gap-1.5'>
                <Label htmlFor='topic' className='text-xs font-semibold'>
                  Campaign Topic / Working Hook
                </Label>
                <Input
                  id='topic'
                  value={topic}
                  onChange={(e) => setTopic(e.target.value)}
                  placeholder='e.g. How jewellery businesses can reduce transit risk'
                  className='text-xs'
                />
              </div>

              {/* Goal Dropdown */}
              <div className='grid grid-cols-2 gap-3'>
                <div className='flex flex-col gap-1.5'>
                  <Label className='text-xs font-semibold'>Primary Goal</Label>
                  <select
                    value={goal}
                    onChange={(e) => setGoal(e.target.value)}
                    className='h-9 rounded-md border bg-background px-3 py-1 text-xs shadow-xs focus:outline-hidden focus:ring-1 focus:ring-primary'
                  >
                    <option value='Awareness'>Awareness</option>
                    <option value='Education'>Education</option>
                    <option value='Lead Generation'>Lead Generation</option>
                    <option value='Thought Leadership'>Thought Leadership</option>
                    <option value='Engagement'>Engagement</option>
                    <option value='Product Awareness'>Product Awareness</option>
                  </select>
                </div>

                {/* Language Dropdown */}
                <div className='flex flex-col gap-1.5'>
                  <Label className='text-xs font-semibold'>Language</Label>
                  <select
                    value={language}
                    onChange={(e) => setLanguage(e.target.value as Language)}
                    className='h-9 rounded-md border bg-background px-3 py-1 text-xs shadow-xs focus:outline-hidden focus:ring-1 focus:ring-primary'
                  >
                    <option value='en'>English (Global / ASEAN)</option>
                    <option value='ms'>Bahasa Melayu (Malaysia)</option>
                    <option value='id'>Bahasa Indonesia</option>
                    <option value='th'>Thai (Thailand)</option>
                    <option value='zh'>Traditional Chinese</option>
                  </select>
                </div>
              </div>

              {/* Tone (derived with override) */}
              <div className='flex flex-col gap-1.5'>
                <Label className='text-xs font-semibold'>Editorial Tone</Label>
                <Input
                  value={tone}
                  onChange={(e) => setTone(e.target.value)}
                  className='text-xs'
                />
              </div>

              {/* Platforms */}
              <div className='flex flex-col gap-1.5'>
                <Label className='text-xs font-semibold'>Target Platforms</Label>
                <div className='flex flex-wrap gap-2'>
                  {(['linkedin', 'instagram', 'x', 'reel', 'blog'] as Platform[]).map((p) => {
                    const isSelected = selectedPlatforms.includes(p);
                    return (
                      <button
                        key={p}
                        type='button'
                        onClick={() => togglePlatform(p)}
                        className={`px-3 py-1.5 rounded-md border text-xs font-medium transition-colors ${
                          isSelected
                            ? 'bg-foreground text-background border-foreground font-semibold'
                            : 'bg-muted/40 text-muted-foreground hover:bg-muted'
                        }`}
                      >
                        {p === 'linkedin' ? 'LinkedIn' : p === 'instagram' ? 'Instagram' : p === 'x' ? 'X' : p === 'reel' ? 'Reel' : 'Blog'}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Lessons Injected indicator */}
              <div className='rounded-md border bg-muted/30 p-2.5 flex items-start gap-2'>
                <Icons.sparkles className='size-4 text-purple-600 dark:text-purple-400 mt-0.5 shrink-0' />
                <div className='text-[11px] text-muted-foreground'>
                  <strong className='text-foreground font-medium'>
                    {store.lessons.filter((l) => l.brand_id === brandId).length} learned lessons
                  </strong>{' '}
                  active for {DEMO_BRANDS[brandId].name}. Negative guidance automatically appended to generator.
                </div>
              </div>

              {/* Generate Button */}
              <Button
                onClick={handleGenerate}
                disabled={isGenerating}
                className='w-full mt-2 font-semibold'
                size='default'
              >
                {isGenerating ? (
                  <>
                    <Icons.spinner className='size-4 animate-spin mr-2' />
                    AURA is Working...
                  </>
                ) : (
                  <>
                    <Icons.sparkles className='size-4 mr-2' />
                    Generate Campaign
                  </>
                )}
              </Button>
            </CardContent>
          </Card>
        </div>

        {/* Right Output: Staged Generation or Results View */}
        <div className='lg:col-span-7 flex flex-col gap-4'>
          {/* Staged Generation State */}
          {isGenerating && (
            <Card className='shadow-xs border-primary/20 bg-primary/[0.02] p-8 text-center flex flex-col items-center justify-center min-h-[420px]'>
              <div className='h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center text-primary mb-4 animate-pulse'>
                <Icons.sparkles className='size-6' />
              </div>
              <h2 className='text-lg font-bold text-foreground'>AURA is working</h2>
              <p className='text-xs text-muted-foreground max-w-sm mt-1 mb-6'>
                Synthesizing brand voice guidelines, historical reviewer feedback, and regulatory compliance rules.
              </p>

              <div className='flex flex-col gap-2.5 text-left w-full max-w-md'>
                {STAGED_PIPELINE_STEPS.map((step, idx) => {
                  const isDone = idx < currentStepIndex;
                  const isCurrent = idx === currentStepIndex;
                  return (
                    <div
                      key={step}
                      className={`flex items-center gap-3 text-xs p-2 rounded-md transition-all ${
                        isCurrent
                          ? 'bg-primary/10 font-semibold text-primary'
                          : isDone
                          ? 'text-foreground'
                          : 'text-muted-foreground/40'
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

          {/* Empty Prompt Before Generating */}
          {!isGenerating && !generatedAssets && (
            <Card className='border-dashed flex flex-col items-center justify-center p-12 text-center min-h-[420px]'>
              <div className='h-12 w-12 rounded-full bg-muted flex items-center justify-center text-muted-foreground mb-3'>
                <Icons.post className='size-6' />
              </div>
              <h3 className='text-base font-bold text-foreground'>Ready to generate</h3>
              <p className='text-xs text-muted-foreground max-w-sm mt-1'>
                Select your parameters on the left and click <strong>Generate Campaign</strong> to produce a complete cross-channel suite.
              </p>
            </Card>
          )}

          {/* Generated Results View */}
          {!isGenerating && generatedAssets && (
            <div className='flex flex-col gap-4'>
              {/* Campaign Header Badge */}
              <div className='rounded-xl border bg-card p-4 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-3'>
                <div>
                  <div className='flex items-center gap-2'>
                    <BrandBadge brandId={brandId} />
                    <Badge variant='outline' className='text-xs font-semibold'>
                      Campaign Ready
                    </Badge>
                  </div>
                  <h3 className='text-base font-bold text-foreground mt-1.5'>{topic}</h3>
                  <div className='flex items-center gap-3 text-xs text-muted-foreground mt-1'>
                    <span>
                      <strong className='text-foreground'>{generatedAssets.length}</strong> assets generated
                    </span>
                    <span>•</span>
                    <span>2 variants</span>
                    <span>•</span>
                    <span>{selectedPlatforms.length} platforms</span>
                    <span>•</span>
                    <span>{language.toUpperCase()}</span>
                  </div>
                </div>

                <div className='flex items-center gap-2'>
                  <Button onClick={handleSendToReview} size='sm'>
                    <Icons.checks className='size-4 mr-1.5' />
                    Send All to Review Queue
                  </Button>
                </div>
              </div>

              {/* Platform Tabs */}
              <Tabs value={activePlatformTab} onValueChange={setActivePlatformTab} className='w-full'>
                <TabsList className='w-full grid grid-cols-5 h-10'>
                  {selectedPlatforms.map((p) => (
                    <TabsTrigger key={p} value={p} className='text-xs capitalize'>
                      {p}
                    </TabsTrigger>
                  ))}
                </TabsList>

                {/* Tab Contents */}
                {selectedPlatforms.map((platform) => {
                  const platformAssets = generatedAssets.filter((a) => a.platform === platform);
                  return (
                    <TabsContent key={platform} value={platform} className='mt-4 flex flex-col gap-4'>
                      {/* Variant Comparison (especially for LinkedIn) */}
                      {platformAssets.length > 1 ? (
                        <div className='grid grid-cols-1 md:grid-cols-2 gap-4'>
                          {platformAssets.map((asset) => {
                            const isSelected = selectedVariants[platform] === asset.variant;
                            return (
                              <Card
                                key={asset.id}
                                className={`shadow-xs transition-all border ${
                                  isSelected ? 'border-primary ring-1 ring-primary' : ''
                                }`}
                              >
                                <CardHeader className='pb-2 flex flex-row items-center justify-between'>
                                  <div>
                                    <span className='text-xs font-bold uppercase tracking-wider text-muted-foreground'>
                                      VARIANT {asset.variant}
                                    </span>
                                    <CardTitle className='text-xs font-semibold text-foreground mt-0.5 line-clamp-1'>
                                      {asset.title}
                                    </CardTitle>
                                  </div>
                                  <ComplianceVerdictBadge
                                    verdict={asset.compliance?.result}
                                    risk={asset.compliance?.risk}
                                  />
                                </CardHeader>
                                <CardContent className='flex flex-col gap-3'>
                                  <div className='rounded-md bg-muted/40 p-3 text-xs font-mono whitespace-pre-wrap max-h-56 overflow-y-auto leading-relaxed'>
                                    {asset.body}
                                  </div>
                                  <div className='flex flex-wrap gap-1'>
                                    {asset.hashtags.map((h) => (
                                      <span key={h} className='text-[10px] text-primary font-medium'>
                                        {h}
                                      </span>
                                    ))}
                                  </div>
                                  <div className='flex items-center justify-between pt-2 border-t'>
                                    <Button
                                      size='xs'
                                      variant={isSelected ? 'default' : 'outline'}
                                      onClick={() =>
                                        setSelectedVariants((prev) => ({
                                          ...prev,
                                          [platform]: asset.variant
                                        }))
                                      }
                                    >
                                      {isSelected ? '✓ Selected' : `Use Variant ${asset.variant}`}
                                    </Button>
                                    <Button
                                      size='xs'
                                      variant='secondary'
                                      onClick={() => {
                                        auraStore.addGeneratedCampaign({
                                          brandId,
                                          topic,
                                          goal,
                                          platforms: [platform],
                                          language,
                                          assets: [asset]
                                        });
                                        toast.success(`Variant ${asset.variant} sent to Review Queue`);
                                      }}
                                    >
                                      Enqueue
                                    </Button>
                                  </div>
                                </CardContent>
                              </Card>
                            );
                          })}
                        </div>
                      ) : (
                        /* Single Asset View for Reel, Blog, etc. */
                        platformAssets.map((asset) => (
                          <Card key={asset.id} className='shadow-xs'>
                            <CardHeader className='pb-2 flex flex-row items-center justify-between'>
                              <div>
                                <span className='text-xs font-bold uppercase tracking-wider text-muted-foreground'>
                                  {platform.toUpperCase()} FORMAT
                                </span>
                                <CardTitle className='text-sm font-bold text-foreground mt-0.5'>
                                  {asset.title}
                                </CardTitle>
                              </div>
                              <ComplianceVerdictBadge
                                verdict={asset.compliance?.result}
                                risk={asset.compliance?.risk}
                              />
                            </CardHeader>
                            <CardContent className='flex flex-col gap-3'>
                              <div className='rounded-md bg-muted/40 p-3 text-xs font-mono whitespace-pre-wrap max-h-80 overflow-y-auto leading-relaxed'>
                                {asset.body}
                              </div>
                              <div className='flex items-center justify-end gap-2 pt-2 border-t'>
                                <Button
                                  size='xs'
                                  onClick={() => {
                                    auraStore.addGeneratedCampaign({
                                      brandId,
                                      topic,
                                      goal,
                                      platforms: [platform],
                                      language,
                                      assets: [asset]
                                    });
                                    toast.success(`Asset added to Review Queue`);
                                  }}
                                >
                                  Enqueue for Review
                                </Button>
                              </div>
                            </CardContent>
                          </Card>
                        ))
                      )}

                      {/* Realistic Social Preview */}
                      <Card className='border bg-muted/10'>
                        <CardHeader className='py-2.5 px-4 border-b bg-muted/20'>
                          <CardTitle className='text-xs font-semibold text-muted-foreground flex items-center gap-1.5'>
                            <Icons.post className='size-3.5' /> Realistic {platform.toUpperCase()} Social Preview
                          </CardTitle>
                        </CardHeader>
                        <CardContent className='p-4'>
                          <div className='max-w-md mx-auto rounded-lg border bg-card p-4 shadow-sm text-xs'>
                            <div className='flex items-center gap-2.5 mb-3'>
                              <div className='h-8 w-8 rounded-full bg-foreground text-background flex items-center justify-center font-bold text-xs'>
                                JA
                              </div>
                              <div>
                                <div className='font-bold text-foreground flex items-center gap-1'>
                                  JA Assure · {DEMO_BRANDS[brandId].name}
                                </div>
                                <div className='text-[10px] text-muted-foreground'>
                                  Specialist Underwriting • Promoted
                                </div>
                              </div>
                            </div>
                            <div className='font-sans whitespace-pre-line text-foreground/90 leading-relaxed text-xs'>
                              {platformAssets[0]?.body.slice(0, 240)}...
                            </div>
                            <div className='mt-2 text-primary font-medium text-[11px]'>
                              {platformAssets[0]?.hashtags.join(' ')}
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    </TabsContent>
                  );
                })}
              </Tabs>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
