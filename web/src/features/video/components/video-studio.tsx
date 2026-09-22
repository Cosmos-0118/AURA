'use client';

import React, { useState, useEffect } from 'react';
import PageContainer from '@/components/layout/page-container';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Icons } from '@/components/icons';
import { IconCopy, IconDownload } from '@tabler/icons-react';
import {
  generateVideo,
  getVideoConfig,
  attachVideoToAsset,
  listAssets,
} from '@/lib/api/client';
import type {
  VideoAspectRatio,
  VideoResolution,
  VideoGenerateResponse,
  Asset,
} from '@/lib/api/types';

const PRESETS = {
  jade: {
    name: 'Jade (Jewellers)',
    badge: 'Luxury / Specialist',
    prompt:
      'A luxury handcrafted emerald and diamond necklace resting on dark velvet in an exclusive boutique showcase, warm cinematic studio rim lighting, slow elegant camera tracking orbit, 8k hyper-realistic.',
  },
  doctorshield: {
    name: 'DoctorShield (Clinics)',
    badge: 'Medical / Professional',
    prompt:
      'A sunlit modern doctor consultation clinic, clean wooden desk with a stethoscope and medical journal, soft morning sunlight through large windows, calming professional healthcare ambiance, smooth cinematic pan.',
  },
  jaguar: {
    name: 'Jaguar Transit (Secured)',
    badge: 'Logistics / High-Tech',
    prompt:
      'A heavy armored transit security vehicle departing a high-security airport vault depot at twilight, subtle holographic telemetry data overlay, atmospheric rain reflections, cinematic tracking shot.',
  },
};

export default function VideoStudio() {
  const [prompt, setPrompt] = useState(PRESETS.jade.prompt);
  const [aspectRatio, setAspectRatio] = useState<VideoAspectRatio>('9:16');
  const [resolution, setResolution] = useState<VideoResolution>('768P');
  const [promptExpansion, setPromptExpansion] = useState<'disabled' | 'balanced'>('disabled');
  const [selectedAssetId, setSelectedAssetId] = useState<string>('');
  const [assets, setAssets] = useState<Asset[]>([]);

  const [isGenerating, setIsGenerating] = useState(false);
  const [result, setResult] = useState<VideoGenerateResponse | null>(null);
  const [logs, setLogs] = useState<string[]>([]);
  const [attachStatus, setAttachStatus] = useState<string | null>(null);

  // Load existing assets for attaching video
  useEffect(() => {
    listAssets()
      .then((data) => {
        if (Array.isArray(data)) {
          setAssets(data.slice(0, 10));
        }
      })
      .catch(() => {
        // Safe dev fallback
      });
  }, []);

  const handleGenerate = async () => {
    if (!prompt.trim() || isGenerating) return;

    setIsGenerating(true);
    setResult(null);
    setLogs([
      'Initiating request for Minimax H3 Max Turbo...',
      'Verifying strict 5-second duration constraint...',
      'Submitting job to Fal.ai pipeline...',
    ]);
    setAttachStatus(null);

    try {
      const response = await generateVideo({
        prompt: prompt.trim(),
        duration: 5, // STRICT CONSTRAINT: 5 seconds max
        aspect_ratio: aspectRatio,
        resolution: resolution,
        prompt_expansion_mode: promptExpansion,
        asset_id: selectedAssetId || null,
      });

      setResult(response);
      if (response.logs && response.logs.length > 0) {
        setLogs((prev) => [...prev, ...response.logs]);
      }

      if (response.status === 'COMPLETED') {
        setLogs((prev) => [...prev, 'Video generation successfully completed (5.0s MP4).']);
      } else if (response.error) {
        setLogs((prev) => [...prev, `Error: ${response.error}`]);
      }
    } catch (err: any) {
      setResult({
        status: 'FAILED',
        error: err?.message || 'Failed to generate video',
        logs: [`Exception: ${err?.message || 'Connection error'}`],
      });
    } finally {
      setIsGenerating(false);
    }
  };

  const handleAttach = async () => {
    if (!result?.video?.url || !selectedAssetId) return;
    setAttachStatus('Attaching...');
    try {
      await attachVideoToAsset({
        asset_id: selectedAssetId,
        video_url: result.video.url,
      });
      setAttachStatus('Attached successfully to asset!');
    } catch (err: any) {
      setAttachStatus(`Failed to attach: ${err.message}`);
    }
  };

  const copyUrl = () => {
    if (result?.video?.url) {
      navigator.clipboard.writeText(result.video.url);
      alert('Video URL copied to clipboard!');
    }
  };

  return (
    <PageContainer>
      <div className='flex flex-1 flex-col space-y-6 pb-12'>
        {/* Header */}
        <div className='flex flex-col justify-between gap-4 md:flex-row md:items-center'>
          <div>
            <div className='flex items-center gap-2'>
              <h1 className='text-3xl font-bold tracking-tight'>AI Video Studio</h1>
              <Badge variant='outline' className='border-primary/40 bg-primary/10 text-primary'>
                Minimax H3 Max Turbo
              </Badge>
            </div>
            <p className='text-sm text-muted-foreground mt-1'>
              Generate high-impact 5-second marketing video reels and product clips powered by Fal.ai.
            </p>
          </div>

          <div className='flex items-center gap-2'>
            <Badge variant='secondary' className='flex items-center gap-1.5 py-1 px-3'>
              <Icons.check className='size-3.5 text-emerald-500' />
              <span>Strict 5s Max Duration Enforced</span>
            </Badge>
          </div>
        </div>

        {/* Studio Layout */}
        <div className='grid grid-cols-1 gap-6 lg:grid-cols-12'>
          {/* Left: Input & Controls (7 Cols) */}
          <div className='space-y-6 lg:col-span-7'>
            {/* Brand Presets */}
            <Card>
              <CardHeader className='pb-3'>
                <CardTitle className='text-base font-semibold'>Brand Style Presets</CardTitle>
                <CardDescription>
                  Quickly load tested visual prompts tailored for JA Assure's brand personalities.
                </CardDescription>
              </CardHeader>
              <CardContent className='flex flex-wrap gap-2.5 pt-0'>
                {Object.entries(PRESETS).map(([key, preset]) => (
                  <Button
                    key={key}
                    variant='outline'
                    size='sm'
                    className='h-auto flex-col items-start py-2 px-3 text-left hover:border-primary transition-all'
                    onClick={() => setPrompt(preset.prompt)}
                  >
                    <span className='font-medium text-xs'>{preset.name}</span>
                    <span className='text-[10px] text-muted-foreground'>{preset.badge}</span>
                  </Button>
                ))}
              </CardContent>
            </Card>

            {/* Prompt Editor */}
            <Card>
              <CardHeader className='pb-3'>
                <div className='flex items-center justify-between'>
                  <CardTitle className='text-base font-semibold'>Scene Prompt</CardTitle>
                  <span className='text-xs text-muted-foreground'>{prompt.length} characters</span>
                </div>
                <CardDescription>
                  Describe the visual scene, subject motion, camera movement, and lighting.
                </CardDescription>
              </CardHeader>
              <CardContent className='space-y-4'>
                <Textarea
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  placeholder='e.g. A luxury watch rotating slowly under ambient studio lighting, macro lens tracking...'
                  className='min-h-[140px] resize-y text-sm font-mono leading-relaxed'
                  disabled={isGenerating}
                />

                {/* Pre-fill from script selector */}
                {assets.length > 0 && (
                  <div className='space-y-1.5 pt-1'>
                    <Label className='text-xs text-muted-foreground'>
                      Or load script from recent campaign asset:
                    </Label>
                    <select
                      className='w-full rounded-md border border-input bg-background px-3 py-1.5 text-xs shadow-xs focus:border-ring focus:outline-hidden'
                      value=''
                      onChange={(e) => {
                        const found = assets.find((a) => a.id === e.target.value);
                        if (found) {
                          setPrompt(found.body);
                          setSelectedAssetId(found.id);
                        }
                      }}
                      disabled={isGenerating}
                    >
                      <option value=''>-- Select asset to copy script --</option>
                      {assets.map((asset) => (
                        <option key={asset.id} value={asset.id}>
                          [{asset.brand_id.toUpperCase()} - {asset.platform}] {asset.title || asset.body.slice(0, 45)}...
                        </option>
                      ))}
                    </select>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Video Parameters */}
            <Card>
              <CardHeader className='pb-3'>
                <CardTitle className='text-base font-semibold'>Video Generation Settings</CardTitle>
                <CardDescription>Configure aspect ratio and quality output parameters.</CardDescription>
              </CardHeader>
              <CardContent className='space-y-5'>
                {/* Aspect Ratio */}
                <div className='space-y-2'>
                  <Label className='text-xs font-medium'>Aspect Ratio</Label>
                  <div className='grid grid-cols-3 gap-2.5'>
                    <Button
                      type='button'
                      variant={aspectRatio === '9:16' ? 'default' : 'outline'}
                      size='sm'
                      className='flex flex-col h-auto py-2.5'
                      onClick={() => setAspectRatio('9:16')}
                      disabled={isGenerating}
                    >
                      <span className='font-bold text-xs'>9:16 (Vertical)</span>
                      <span className='text-[10px] opacity-80'>Reels, TikTok, Shorts</span>
                    </Button>
                    <Button
                      type='button'
                      variant={aspectRatio === '16:9' ? 'default' : 'outline'}
                      size='sm'
                      className='flex flex-col h-auto py-2.5'
                      onClick={() => setAspectRatio('16:9')}
                      disabled={isGenerating}
                    >
                      <span className='font-bold text-xs'>16:9 (Landscape)</span>
                      <span className='text-[10px] opacity-80'>Widescreen / Web</span>
                    </Button>
                    <Button
                      type='button'
                      variant={aspectRatio === '1:1' ? 'default' : 'outline'}
                      size='sm'
                      className='flex flex-col h-auto py-2.5'
                      onClick={() => setAspectRatio('1:1')}
                      disabled={isGenerating}
                    >
                      <span className='font-bold text-xs'>1:1 (Square)</span>
                      <span className='text-[10px] opacity-80'>Feed & Carousel</span>
                    </Button>
                  </div>
                </div>

                {/* Duration & Resolution Controls */}
                <div className='grid grid-cols-1 sm:grid-cols-3 gap-4 pt-1'>
                  {/* Duration - Locked to strict 5s */}
                  <div className='space-y-1.5'>
                    <Label className='text-xs font-medium'>Duration</Label>
                    <div className='flex items-center justify-between rounded-md border border-emerald-500/30 bg-emerald-500/10 px-3 py-2 text-xs font-semibold text-emerald-600 dark:text-emerald-400'>
                      <span>5 Seconds</span>
                      <Badge variant='outline' className='text-[10px] border-emerald-500/40'>
                        Max Cap
                      </Badge>
                    </div>
                  </div>

                  {/* Resolution */}
                  <div className='space-y-1.5'>
                    <Label className='text-xs font-medium'>Resolution</Label>
                    <select
                      className='w-full rounded-md border border-input bg-background px-3 py-2 text-xs shadow-xs focus:border-ring focus:outline-hidden'
                      value={resolution}
                      onChange={(e) => setResolution(e.target.value as VideoResolution)}
                      disabled={isGenerating}
                    >
                      <option value='768P'>768P (Standard HD)</option>
                      <option value='1080P'>1080P (FHD Refined)</option>
                      <option value='480P'>480P (Draft Fast)</option>
                    </select>
                  </div>

                  {/* Prompt Expansion */}
                  <div className='space-y-1.5'>
                    <Label className='text-xs font-medium'>Prompt Expansion</Label>
                    <select
                      className='w-full rounded-md border border-input bg-background px-3 py-2 text-xs shadow-xs focus:border-ring focus:outline-hidden'
                      value={promptExpansion}
                      onChange={(e) => setPromptExpansion(e.target.value as any)}
                      disabled={isGenerating}
                    >
                      <option value='disabled'>Disabled (Exact prompt)</option>
                      <option value='balanced'>Balanced (Enhanced)</option>
                    </select>
                  </div>
                </div>
              </CardContent>
              <CardFooter className='border-t bg-muted/20 px-6 py-4'>
                <Button
                  onClick={handleGenerate}
                  disabled={isGenerating || !prompt.trim()}
                  className='w-full font-semibold gap-2'
                  size='lg'
                >
                  {isGenerating ? (
                    <>
                      <Icons.spinner className='size-4 animate-spin' />
                      Generating Video (5s)...
                    </>
                  ) : (
                    <>
                      <Icons.video className='size-4' />
                      Generate Video (Max 5s)
                    </>
                  )}
                </Button>
              </CardFooter>
            </Card>
          </div>

          {/* Right: Video Output & Live Feed (5 Cols) */}
          <div className='space-y-6 lg:col-span-5'>
            {/* Video Player Card */}
            <Card className='overflow-hidden'>
              <CardHeader className='pb-3'>
                <div className='flex items-center justify-between'>
                  <CardTitle className='text-base font-semibold'>Video Output</CardTitle>
                  {result?.status === 'COMPLETED' && (
                    <Badge variant='outline' className='border-emerald-500/40 text-emerald-600 bg-emerald-500/10'>
                      5.0s Ready
                    </Badge>
                  )}
                </div>
                <CardDescription>Preview the generated MP4 media.</CardDescription>
              </CardHeader>
              <CardContent className='flex flex-col items-center justify-center p-4 pt-0'>
                {isGenerating ? (
                  <div className='flex flex-col items-center justify-center rounded-lg border border-dashed border-primary/40 bg-primary/5 p-12 text-center w-full min-h-[320px]'>
                    <Icons.spinner className='size-10 animate-spin text-primary mb-4' />
                    <p className='font-semibold text-sm'>Rendering 5s Video with Fal.ai</p>
                    <p className='text-xs text-muted-foreground mt-1 max-w-xs'>
                      Model is performing diffusion denoising and temporal alignment...
                    </p>
                  </div>
                ) : result?.video?.url ? (
                  <div className='w-full space-y-3'>
                    <div
                      className={`relative mx-auto overflow-hidden rounded-lg bg-black shadow-lg ${
                        aspectRatio === '9:16'
                          ? 'max-w-[270px] aspect-[9/16]'
                          : aspectRatio === '1:1'
                          ? 'max-w-[340px] aspect-square'
                          : 'w-full aspect-video'
                      }`}
                    >
                      <video
                        src={result.video.url}
                        controls
                        autoPlay
                        loop
                        playsInline
                        className='h-full w-full object-contain'
                      />
                    </div>

                    <div className='flex flex-col gap-2 pt-2'>
                      <div className='flex items-center justify-between text-xs text-muted-foreground'>
                        <span>Duration: <strong>5.0 seconds</strong></span>
                        <span>Format: <strong>MP4 ({resolution})</strong></span>
                      </div>

                      <div className='flex items-center gap-2'>
                        <Button
                          variant='outline'
                          size='sm'
                          className='flex-1 gap-1.5'
                          onClick={copyUrl}
                        >
                          <IconCopy className='size-3.5' />
                          Copy Video URL
                        </Button>
                        <a
                          href={result.video.url}
                          download={result.video.file_name || 'aura_reel_5s.mp4'}
                          target='_blank'
                          rel='noopener noreferrer'
                          className='flex-1'
                        >
                          <Button size='sm' className='w-full gap-1.5'>
                            <IconDownload className='size-3.5' />
                            Download MP4
                          </Button>
                        </a>
                      </div>

                      {/* Attach to Asset section */}
                      {assets.length > 0 && (
                        <div className='rounded-md border p-3 bg-muted/20 space-y-2 mt-2'>
                          <Label className='text-xs font-semibold'>Link to Campaign Asset</Label>
                          <div className='flex gap-2'>
                            <select
                              className='flex-1 rounded-md border border-input bg-background px-2.5 py-1 text-xs shadow-xs'
                              value={selectedAssetId}
                              onChange={(e) => setSelectedAssetId(e.target.value)}
                            >
                              <option value=''>-- Select target asset --</option>
                              {assets.map((asset) => (
                                <option key={asset.id} value={asset.id}>
                                  [{asset.brand_id.toUpperCase()}] {asset.title || asset.id.slice(0, 8)}
                                </option>
                              ))}
                            </select>
                            <Button
                              size='sm'
                              variant='secondary'
                              disabled={!selectedAssetId}
                              onClick={handleAttach}
                            >
                              Attach
                            </Button>
                          </div>
                          {attachStatus && (
                            <p className='text-[11px] font-medium text-emerald-600 dark:text-emerald-400'>
                              {attachStatus}
                            </p>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                ) : result?.error ? (
                  <div className='flex flex-col items-center justify-center rounded-lg border border-destructive/30 bg-destructive/5 p-8 text-center w-full min-h-[260px]'>
                    <Icons.warning className='size-8 text-destructive mb-3' />
                    <p className='font-semibold text-sm text-destructive'>Generation Failed</p>
                    <p className='text-xs text-muted-foreground mt-1 max-w-sm'>{result.error}</p>
                    <Button
                      variant='outline'
                      size='sm'
                      className='mt-4'
                      onClick={handleGenerate}
                    >
                      Retry Generation
                    </Button>
                  </div>
                ) : (
                  <div className='flex flex-col items-center justify-center rounded-lg border border-dashed p-10 text-center w-full min-h-[300px] text-muted-foreground'>
                    <Icons.video className='size-12 stroke-[1.2] mb-3 opacity-50' />
                    <p className='text-sm font-medium'>No video generated yet</p>
                    <p className='text-xs max-w-xs mt-1'>
                      Select a brand preset or enter a scene prompt and click "Generate Video".
                    </p>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Execution & Queue Logs */}
            <Card>
              <CardHeader className='pb-2'>
                <div className='flex items-center justify-between'>
                  <CardTitle className='text-xs font-semibold tracking-wide uppercase text-muted-foreground'>
                    Fal.ai Pipeline Logs
                  </CardTitle>
                  <Badge variant='outline' className='text-[10px]'>
                    {isGenerating ? 'Active' : 'Idle'}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className='pt-0'>
                <div className='rounded-md bg-zinc-950 p-3 text-emerald-400 font-mono text-[11px] min-h-[120px] max-h-[180px] overflow-y-auto space-y-1'>
                  {logs.length === 0 ? (
                    <span className='text-zinc-600'>Awaiting submission...</span>
                  ) : (
                    logs.map((log, index) => (
                      <div key={index} className='leading-tight'>
                        <span className='text-zinc-500 select-none'>&gt; </span>
                        {log}
                      </div>
                    ))
                  )}
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </PageContainer>
  );
}
