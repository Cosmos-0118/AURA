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
  CardTitle
} from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Icons } from '@/components/icons';
import { IconCopy, IconDownload, IconSparkles } from '@tabler/icons-react';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { BrandMarkerStudio } from './brand-marker-studio';
import { VideoHistory } from './video-history';
import { generateVideo, attachVideoToAsset, listAssets, saveVideoExport } from '@/lib/api/client';
import type {
  VideoAspectRatio,
  VideoResolution,
  VideoGenerateResponse,
  VideoGenerationRecord,
  Asset
} from '@/lib/api/types';

const PRESETS = {
  jade: {
    id: 'jade',
    name: 'Jade',
    badge: 'Luxury Jewellery',
    prompt:
      'A luxury handcrafted emerald and diamond necklace resting on dark velvet in an exclusive boutique showcase, warm cinematic studio rim lighting, slow elegant camera tracking orbit, 8k hyper-realistic.'
  },
  doctorshield: {
    id: 'doctorshield',
    name: 'Doctor Shield',
    badge: 'Clinical Healthcare',
    prompt:
      'A sunlit modern doctor consultation clinic, clean wooden desk with a stethoscope and medical journal, soft morning sunlight through large windows, calming professional healthcare ambiance, smooth cinematic pan.'
  },
  jaguar: {
    id: 'jaguar',
    name: 'Jaguar Transit',
    badge: 'Logistics & Security',
    prompt:
      'A heavy armored transit security vehicle departing a high-security community vault depot at twilight, subtle holographic telemetry data overlay, atmospheric rain reflections, cinematic tracking shot.'
  }
};

export default function VideoStudio() {
  const [selectedBrand, setSelectedBrand] = useState<'jade' | 'doctorshield' | 'jaguar'>('jade');
  const [prompt, setPrompt] = useState(PRESETS.jade.prompt);
  const [aspectRatio, setAspectRatio] = useState<VideoAspectRatio>('9:16');
  const [resolution, setResolution] = useState<VideoResolution>('768P');
  const [promptExpansion, setPromptExpansion] = useState<'disabled' | 'balanced'>('disabled');
  const [selectedAssetId, setSelectedAssetId] = useState<string>('');
  const [assets, setAssets] = useState<Asset[]>([]);

  const [activeTab, setActiveTab] = useState<'preview' | 'brand'>('preview');
  const [brandMarkerVideoOverride, setBrandMarkerVideoOverride] = useState<string | null>(null);
  const [activeRecordId, setActiveRecordId] = useState<string | null>(null);

  const [isGenerating, setIsGenerating] = useState(false);
  const [result, setResult] = useState<VideoGenerateResponse | null>(null);
  const [logs, setLogs] = useState<string[]>([]);
  const [attachStatus, setAttachStatus] = useState<string | null>(null);

  // History: latest record for instant prepend in VideoHistory
  const [latestRecord, setLatestRecord] = useState<VideoGenerationRecord | null>(null);

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

  const handleSelectPreset = (key: 'jade' | 'doctorshield' | 'jaguar') => {
    setSelectedBrand(key);
    setPrompt(PRESETS[key].prompt);
  };

  const handleGenerate = async () => {
    if (!prompt.trim() || isGenerating) return;

    setIsGenerating(true);
    setResult(null);
    setLogs([
      'Initiating request for Minimax H3 Max Turbo...',
      'Verifying strict 5-second duration constraint...',
      'Submitting job to Fal.ai pipeline...'
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
        brand_id: selectedBrand
      });

      setResult(response);
      if (response.logs && response.logs.length > 0) {
        setLogs((prev) => [...prev, ...response.logs]);
      }

      const newRecId = response.request_id ?? `local-${Date.now()}`;
      setActiveRecordId(newRecId);
      setBrandMarkerVideoOverride(response.video?.url ?? null);

      if (response.status === 'COMPLETED') {
        setLogs((prev) => [...prev, 'Video generation successfully completed (5.0s MP4).']);
        // Build a VideoGenerationRecord from the response for instant history prepend
        setLatestRecord({
          id: newRecId,
          brand_id: selectedBrand,
          asset_id: selectedAssetId || null,
          prompt: prompt.trim(),
          aspect_ratio: aspectRatio,
          resolution: resolution,
          duration_secs: 5,
          model: 'minimax/h3-max-turbo/text-to-video',
          video_url: response.video?.url ?? null,
          file_name: response.video?.file_name ?? null,
          file_size: response.video?.file_size ?? null,
          branded_video_url: null,
          branded_file_name: null,
          status: 'COMPLETED',
          error_msg: null,
          request_id: response.request_id ?? null,
          created_at: new Date().toISOString()
        });
      } else if (response.error) {
        setLogs((prev) => [...prev, `Error: ${response.error}`]);
        // Also record failed generations in history
        setLatestRecord({
          id: newRecId,
          brand_id: selectedBrand,
          asset_id: selectedAssetId || null,
          prompt: prompt.trim(),
          aspect_ratio: aspectRatio,
          resolution: resolution,
          duration_secs: 5,
          model: 'minimax/h3-max-turbo/text-to-video',
          video_url: null,
          file_name: null,
          file_size: null,
          branded_video_url: null,
          branded_file_name: null,
          status: 'FAILED',
          error_msg: response.error ?? null,
          request_id: response.request_id ?? null,
          created_at: new Date().toISOString()
        });
      }
    } catch (err: unknown) {
      const errMsg = err instanceof Error ? err.message : 'Failed to generate video';
      setResult({
        status: 'FAILED',
        error: errMsg,
        logs: [`Exception: ${errMsg}`]
      });
    } finally {
      setIsGenerating(false);
    }
  };

  const handleExportSaved = async (recordId: string, brandedUrl: string, fileName: string) => {
    try {
      await saveVideoExport({
        id: recordId,
        branded_video_url: brandedUrl,
        branded_file_name: fileName
      });
    } catch {
      // Offline fallback
    }
    // Update active record in memory/history
    setLatestRecord((prev) => {
      if (!prev || prev.id !== recordId) return prev;
      return {
        ...prev,
        branded_video_url: brandedUrl,
        branded_file_name: fileName
      };
    });
  };

  const handleAttach = async () => {
    if (!result?.video?.url || !selectedAssetId) return;
    setAttachStatus('Attaching...');
    try {
      await attachVideoToAsset({
        asset_id: selectedAssetId,
        video_url: result.video.url
      });
      setAttachStatus('Attached successfully to asset!');
    } catch (err: unknown) {
      const errMsg = err instanceof Error ? err.message : 'Unknown error';
      setAttachStatus(`Failed to attach: ${errMsg}`);
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
              Generate high-impact 5-second marketing video reels and product clips powered by
              Fal.ai.
            </p>
          </div>

          <div className='flex items-center gap-3'>
            <Badge variant='secondary' className='px-3 py-1 font-mono text-xs'>
              Strict limit: 5.0s Max
            </Badge>
          </div>
        </div>

        {/* Studio Grid (7 cols left input, 5 cols right output) */}
        <div className='grid grid-cols-1 gap-6 lg:grid-cols-12'>
          {/* Left: Generation Controls (7 Cols) */}
          <div className='space-y-6 lg:col-span-7'>
            <Card>
              <CardHeader className='pb-3'>
                <div className='flex items-center justify-between'>
                  <CardTitle className='text-base font-semibold'>
                    Prompt &amp; Brand Settings
                  </CardTitle>
                  <Badge variant='outline' className='text-xs'>
                    Prompt Engine
                  </Badge>
                </div>
                <CardDescription>
                  Choose a brand preset or craft a custom video scene prompt.
                </CardDescription>
              </CardHeader>

              <CardContent className='space-y-4 pt-0'>
                {/* Brand Presets */}
                <div className='space-y-2'>
                  <Label className='text-xs font-semibold'>Brand Presets</Label>
                  <div className='grid grid-cols-1 sm:grid-cols-3 gap-2'>
                    {(Object.keys(PRESETS) as Array<keyof typeof PRESETS>).map((key) => {
                      const item = PRESETS[key];
                      const isSelected = selectedBrand === key && prompt === item.prompt;
                      return (
                        <Button
                          key={key}
                          type='button'
                          variant='outline'
                          size='sm'
                          className={`h-auto flex-col items-start p-2.5 text-left transition-all ${
                            isSelected
                              ? 'border-primary ring-1 ring-primary bg-primary/5'
                              : 'hover:border-primary/50'
                          }`}
                          onClick={() => handleSelectPreset(key)}
                        >
                          <span className='font-medium text-xs'>{item.name}</span>
                          <span className='text-[10px] text-muted-foreground'>{item.badge}</span>
                        </Button>
                      );
                    })}
                  </div>
                </div>

                {/* Prompt Textarea */}
                <div className='space-y-2'>
                  <div className='flex items-center justify-between'>
                    <Label htmlFor='video-prompt' className='text-xs font-semibold'>
                      Video Prompt
                    </Label>
                    <span className='text-[11px] text-muted-foreground'>{prompt.length} chars</span>
                  </div>
                  <Textarea
                    id='video-prompt'
                    placeholder='Describe the subject, camera movement, lighting, style, and cinematic mood...'
                    value={prompt}
                    onChange={(e) => setPrompt(e.target.value)}
                    rows={4}
                    className='resize-none text-xs leading-relaxed'
                    disabled={isGenerating}
                  />
                </div>

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
                          [{asset.brand_id.toUpperCase()} - {asset.platform}]{' '}
                          {asset.title || asset.body.slice(0, 45)}...
                        </option>
                      ))}
                    </select>
                  </div>
                )}

                {/* Video Parameters */}
                <div className='grid grid-cols-1 sm:grid-cols-3 gap-4 pt-1'>
                  {/* Aspect Ratio */}
                  <div className='space-y-1.5'>
                    <Label className='text-xs font-medium'>Aspect Ratio</Label>
                    <select
                      className='w-full rounded-md border border-input bg-background px-3 py-1.5 text-xs shadow-xs focus:border-ring focus:outline-hidden'
                      value={aspectRatio}
                      onChange={(e) => setAspectRatio(e.target.value as VideoAspectRatio)}
                      disabled={isGenerating}
                    >
                      <option value='9:16'>9:16 (Reel / TikTok / Shorts)</option>
                      <option value='16:9'>16:9 (Landscape YouTube / Web)</option>
                      <option value='1:1'>1:1 (Square Feed Post)</option>
                      <option value='4:3'>4:3 (Classic Video)</option>
                      <option value='3:4'>3:4 (Portrait Feed)</option>
                      <option value='21:9'>21:9 (Cinematic Ultrawide)</option>
                    </select>
                  </div>

                  {/* Resolution */}
                  <div className='space-y-1.5'>
                    <Label className='text-xs font-medium'>Resolution</Label>
                    <select
                      className='w-full rounded-md border border-input bg-background px-3 py-1.5 text-xs shadow-xs focus:border-ring focus:outline-hidden'
                      value={resolution}
                      onChange={(e) => setResolution(e.target.value as VideoResolution)}
                      disabled={isGenerating}
                    >
                      <option value='768P'>768P (Standard HD)</option>
                      <option value='1080P'>1080P (Full HD)</option>
                      <option value='480P'>480P (Fast Preview)</option>
                    </select>
                  </div>

                  {/* Prompt Expansion */}
                  <div className='space-y-1.5'>
                    <Label className='text-xs font-medium'>Prompt Enhancer</Label>
                    <select
                      className='w-full rounded-md border border-input bg-background px-3 py-1.5 text-xs shadow-xs focus:border-ring focus:outline-hidden'
                      value={promptExpansion}
                      onChange={(e) =>
                        setPromptExpansion(e.target.value as 'disabled' | 'balanced')
                      }
                      disabled={isGenerating}
                    >
                      <option value='disabled'>Disabled (Exact Prompt)</option>
                      <option value='balanced'>Balanced Expansion</option>
                    </select>
                  </div>
                </div>
              </CardContent>

              <CardFooter className='border-t bg-muted/20 px-6 py-3.5 flex items-center justify-between'>
                <div className='flex items-center gap-2 text-xs text-muted-foreground'>
                  <Icons.check className='size-3.5 text-emerald-500' />
                  <span>Duration locked to 5.0s</span>
                </div>

                <Button
                  onClick={handleGenerate}
                  disabled={isGenerating || !prompt.trim()}
                  className='font-semibold gap-2 min-w-[140px]'
                >
                  {isGenerating ? (
                    <>
                      <Icons.spinner className='size-4 animate-spin' />
                      Generating...
                    </>
                  ) : (
                    <>
                      <IconSparkles className='size-4' />
                      Generate Video
                    </>
                  )}
                </Button>
              </CardFooter>
            </Card>
          </div>

          {/* Right: Video Output & Live Feed (5 Cols) */}
          <div className='space-y-6 lg:col-span-5'>
            {/* Tabs for Video Preview and Brand Marker */}
            <Tabs
              value={activeTab}
              onValueChange={(val) => setActiveTab(val as 'preview' | 'brand')}
              className='w-full space-y-4'
            >
              <TabsList className='grid w-full grid-cols-2'>
                <TabsTrigger value='preview' className='gap-2 text-xs font-medium'>
                  <Icons.video className='size-3.5' />
                  <span>Video Preview</span>
                </TabsTrigger>
                <TabsTrigger value='brand' className='gap-2 text-xs font-medium relative'>
                  <IconSparkles className='size-3.5' />
                  <span>Brand Marker</span>
                  {(result?.status === 'COMPLETED' || brandMarkerVideoOverride) && (
                    <span className='size-2 rounded-full bg-emerald-500 animate-pulse' />
                  )}
                </TabsTrigger>
              </TabsList>

              {/* Tab 1: Direct Video Preview */}
              <TabsContent value='preview' className='mt-0 space-y-4'>
                <Card className='overflow-hidden'>
                  <CardHeader className='pb-3'>
                    <div className='flex items-center justify-between'>
                      <CardTitle className='text-base font-semibold'>Video Output</CardTitle>
                      {result?.status === 'COMPLETED' && (
                        <Badge
                          variant='outline'
                          className='border-emerald-500/40 text-emerald-600 bg-emerald-500/10'
                        >
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
                          >
                            <track kind='captions' />
                          </video>
                        </div>

                        <div className='flex flex-col gap-2 pt-2'>
                          <div className='flex items-center justify-between text-xs text-muted-foreground'>
                            <span>
                              Duration: <strong>5.0 seconds</strong>
                            </span>
                            <span>
                              Format: <strong>MP4 ({resolution})</strong>
                            </span>
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
                              <Label className='text-xs font-semibold'>
                                Link to Campaign Asset
                              </Label>
                              <div className='flex gap-2'>
                                <select
                                  className='flex-1 rounded-md border border-input bg-background px-2.5 py-1 text-xs shadow-xs'
                                  value={selectedAssetId}
                                  onChange={(e) => setSelectedAssetId(e.target.value)}
                                >
                                  <option value=''>-- Select target asset --</option>
                                  {assets.map((asset) => (
                                    <option key={asset.id} value={asset.id}>
                                      [{asset.brand_id.toUpperCase()}]{' '}
                                      {asset.title || asset.id.slice(0, 8)}
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
                        <p className='text-xs text-muted-foreground mt-1 max-w-sm'>
                          {result.error}
                        </p>
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
                          Select a brand preset or enter a scene prompt and click &quot;Generate
                          Video&quot;.
                        </p>
                      </div>
                    )}
                  </CardContent>
                </Card>
              </TabsContent>

              {/* Tab 2: Brand Marker Module */}
              <TabsContent value='brand' className='mt-0 space-y-4'>
                <BrandMarkerStudio
                  videoResult={result}
                  aspectRatio={aspectRatio}
                  videoUrlOverride={brandMarkerVideoOverride}
                  activeRecordId={activeRecordId}
                  onExportSaved={handleExportSaved}
                />
              </TabsContent>
            </Tabs>

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

        {/* Video Generation History — full-width section below the studio grid */}
        <VideoHistory
          latestRecord={latestRecord}
          onOpenInBrandMarker={(url, promptText, recordId) => {
            setBrandMarkerVideoOverride(url);
            setActiveRecordId(recordId || null);
            if (promptText) setPrompt(promptText);
            setActiveTab('brand');
            window.scrollTo({ top: 120, behavior: 'smooth' });
          }}
          onRegenerate={(p) => {
            setPrompt(p);
            window.scrollTo({ top: 0, behavior: 'smooth' });
          }}
        />
      </div>
    </PageContainer>
  );
}
