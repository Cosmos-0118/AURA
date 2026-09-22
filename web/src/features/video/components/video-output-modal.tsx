'use client';

import React, { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Label } from '@/components/ui/label';
import { Icons } from '@/components/icons';
import {
  IconCopy,
  IconDownload,
  IconSparkles,
  IconX,
  IconMovie,
  IconBrandLinkedin
} from '@tabler/icons-react';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { BrandMarkerStudio } from './brand-marker-studio';
import type {
  VideoAspectRatio,
  VideoResolution,
  VideoGenerateResponse,
  Asset
} from '@/lib/api/types';

const BRAND_CONFIG: Record<string, { label: string; badgeColor: string }> = {
  jade: {
    label: 'Jade',
    badgeColor: 'border-emerald-500/40 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400'
  },
  doctorshield: {
    label: 'Doctor Shield',
    badgeColor: 'border-sky-500/40 bg-sky-500/10 text-sky-600 dark:text-sky-400'
  },
  jaguar: {
    label: 'Jaguar Transit',
    badgeColor: 'border-amber-500/40 bg-amber-500/10 text-amber-600 dark:text-amber-400'
  }
};

export interface VideoOutputModalProps {
  open: boolean;
  onClose: () => void;
  defaultTab?: 'preview' | 'brand';
  result: VideoGenerateResponse | null;
  isGenerating?: boolean;
  aspectRatio: VideoAspectRatio;
  resolution: VideoResolution;
  selectedBrand: 'jade' | 'doctorshield' | 'jaguar';
  brandMarkerVideoOverride: string | null;
  activeRecordId: string | null;
  assets: Asset[];
  selectedAssetId: string;
  attachStatus: string | null;
  onSetSelectedAssetId: (id: string) => void;
  onAttach: () => void;
  onCopyUrl: () => void;
  onExportSaved: (recordId: string, brandedUrl: string, fileName: string) => void;
  onRetry?: () => void;
}

export function VideoOutputModal({
  open,
  onClose,
  defaultTab = 'preview',
  result,
  isGenerating = false,
  aspectRatio,
  resolution,
  selectedBrand,
  brandMarkerVideoOverride,
  activeRecordId,
  assets,
  selectedAssetId,
  attachStatus,
  onSetSelectedAssetId,
  onAttach,
  onCopyUrl,
  onExportSaved,
  onRetry
}: VideoOutputModalProps) {
  const [mounted, setMounted] = useState(false);
  const [activeTab, setActiveTab] = useState<'preview' | 'brand'>(defaultTab);

  useEffect(() => {
    setMounted(true);
  }, []);

  // Update tab when defaultTab changes
  useEffect(() => {
    if (defaultTab) {
      setActiveTab(defaultTab);
    }
  }, [defaultTab]);

  // Handle ESC key and prevent body scroll when open
  useEffect(() => {
    if (!open) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    const originalOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    window.addEventListener('keydown', handleKeyDown);

    return () => {
      document.body.style.overflow = originalOverflow;
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [open, onClose]);

  if (!mounted || !open) return null;

  const currentVideoUrl = brandMarkerVideoOverride || result?.video?.url;
  const brandInfo = BRAND_CONFIG[selectedBrand] || {
    label: selectedBrand,
    badgeColor: 'border-primary/30 bg-primary/10 text-primary'
  };

  return createPortal(
    <div
      className='fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 animate-in fade-in duration-200'
      role='dialog'
      aria-modal='true'
    >
      {/* Backdrop overlay (click to dismiss) */}
      <div
        className='fixed inset-0 bg-black/75 backdrop-blur-xs transition-opacity'
        onClick={onClose}
      />

      {/* Modal Card Panel */}
      <div
        className='relative z-10 flex flex-col w-full max-w-5xl max-h-[92vh] rounded-2xl border border-border/80 bg-background shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200'
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div className='flex items-center justify-between border-b border-border/60 px-5 py-3.5 bg-muted/25'>
          <div className='flex items-center gap-2.5 flex-wrap'>
            <div className='flex items-center justify-center size-8 rounded-lg bg-primary/10 text-primary border border-primary/20'>
              <IconMovie className='size-4' />
            </div>
            <div>
              <div className='flex items-center gap-2'>
                <h2 className='text-sm font-semibold tracking-tight'>AI Video Studio Output</h2>
                <Badge
                  variant='outline'
                  className={`text-[11px] font-medium ${brandInfo.badgeColor}`}
                >
                  {brandInfo.label}
                </Badge>
                {result?.status === 'COMPLETED' && (
                  <Badge
                    variant='outline'
                    className='border-emerald-500/40 text-emerald-600 dark:text-emerald-400 bg-emerald-500/10 text-[10px]'
                  >
                    5.0s Ready
                  </Badge>
                )}
              </div>
              <p className='text-[11px] text-muted-foreground'>
                Review AI reel output and customize company overlays before publishing
              </p>
            </div>
          </div>

          <div className='flex items-center gap-2'>
            <Button
              variant='ghost'
              size='icon'
              className='size-8 rounded-full text-muted-foreground hover:text-foreground hover:bg-muted'
              onClick={onClose}
              aria-label='Close popup'
            >
              <IconX className='size-4' />
            </Button>
          </div>
        </div>

        {/* Modal Tabs & Body */}
        <Tabs
          value={activeTab}
          onValueChange={(val) => setActiveTab(val as 'preview' | 'brand')}
          className='flex flex-col flex-1 overflow-hidden'
        >
          {/* Navigation Bar inside modal */}
          <div className='border-b border-border/50 px-5 py-2 bg-muted/10 flex items-center justify-between'>
            <TabsList className='grid w-full max-w-xs grid-cols-2 h-8'>
              <TabsTrigger value='preview' className='gap-1.5 text-xs font-medium'>
                <Icons.video className='size-3.5' />
                <span>Video Preview</span>
              </TabsTrigger>
              <TabsTrigger value='brand' className='gap-1.5 text-xs font-medium relative'>
                <IconSparkles className='size-3.5' />
                <span>Brand Marker</span>
                {currentVideoUrl && (
                  <span className='size-1.5 rounded-full bg-emerald-500 animate-pulse ml-0.5' />
                )}
              </TabsTrigger>
            </TabsList>

            <div className='hidden sm:flex items-center gap-2 text-[11px] text-muted-foreground'>
              <Badge variant='outline' className='text-[10px] font-mono'>
                Aspect: {aspectRatio}
              </Badge>
              <Badge variant='outline' className='text-[10px] font-mono'>
                Res: {resolution}
              </Badge>
            </div>
          </div>

          {/* Tab 1: Video Preview */}
          <TabsContent
            value='preview'
            className='flex-1 overflow-y-auto p-5 sm:p-6 mt-0 space-y-5 focus-visible:outline-none'
          >
            {isGenerating ? (
              <div className='flex flex-col items-center justify-center rounded-xl border border-dashed border-primary/40 bg-primary/5 p-12 text-center w-full min-h-[360px]'>
                <Icons.spinner className='size-10 animate-spin text-primary mb-4' />
                <p className='font-semibold text-sm'>Rendering 5s Video with Fal.ai</p>
                <p className='text-xs text-muted-foreground mt-1 max-w-xs'>
                  Model is performing diffusion denoising and temporal alignment...
                </p>
              </div>
            ) : currentVideoUrl ? (
              <div className='grid grid-cols-1 lg:grid-cols-12 gap-6 items-start'>
                {/* Video Player (responsive max constraint) */}
                <div className='lg:col-span-7 flex flex-col items-center justify-center'>
                  <div
                    className={`relative w-full overflow-hidden rounded-xl bg-black shadow-xl ring-1 ring-border/50 flex items-center justify-center ${
                      aspectRatio === '9:16'
                        ? 'max-w-[280px] aspect-[9/16]'
                        : aspectRatio === '1:1'
                          ? 'max-w-[360px] aspect-square'
                          : 'w-full aspect-video'
                    }`}
                  >
                    <video
                      src={currentVideoUrl}
                      controls
                      autoPlay
                      loop
                      playsInline
                      className='h-full w-full object-contain'
                    >
                      <track kind='captions' />
                    </video>
                  </div>
                </div>

                {/* Video Details & Action Panel */}
                <div className='lg:col-span-5 space-y-4 flex flex-col'>
                  <div className='rounded-xl border border-border/80 bg-muted/20 p-4 space-y-3'>
                    <div className='flex items-center justify-between text-xs'>
                      <span className='text-muted-foreground'>Duration:</span>
                      <strong className='font-semibold'>5.0 seconds (Locked)</strong>
                    </div>
                    <div className='flex items-center justify-between text-xs'>
                      <span className='text-muted-foreground'>Format:</span>
                      <strong className='font-semibold'>MP4 ({resolution})</strong>
                    </div>
                    <div className='flex items-center justify-between text-xs'>
                      <span className='text-muted-foreground'>Aspect Ratio:</span>
                      <strong className='font-semibold'>{aspectRatio}</strong>
                    </div>
                    <div className='flex items-center justify-between text-xs'>
                      <span className='text-muted-foreground'>Generation Engine:</span>
                      <strong className='font-semibold text-primary'>Minimax H3 Max Turbo</strong>
                    </div>
                  </div>

                  {/* Primary Action Buttons */}
                  <div className='grid grid-cols-2 gap-2 pt-1'>
                    <Button
                      variant='outline'
                      size='sm'
                      className='gap-1.5 text-xs'
                      onClick={onCopyUrl}
                    >
                      <IconCopy className='size-3.5' />
                      Copy Video URL
                    </Button>
                    <a
                      href={currentVideoUrl}
                      download={result?.video?.file_name || 'aura_video_reel.mp4'}
                      target='_blank'
                      rel='noopener noreferrer'
                    >
                      <Button size='sm' className='w-full gap-1.5 text-xs font-semibold'>
                        <IconDownload className='size-3.5' />
                        Download MP4
                      </Button>
                    </a>
                  </div>

                  {/* Move directly to branding */}
                  <Button
                    variant='secondary'
                    size='sm'
                    className='w-full gap-2 text-xs border border-primary/30 text-primary hover:bg-primary/10'
                    onClick={() => setActiveTab('brand')}
                  >
                    <IconSparkles className='size-3.5' />
                    Add Company Logo &amp; Brand Overlay &rarr;
                  </Button>

                  {/* Link to Campaign Asset Section */}
                  {assets.length > 0 && (
                    <div className='rounded-xl border border-border/70 p-3.5 bg-muted/15 space-y-2 mt-2'>
                      <Label className='text-xs font-semibold flex items-center justify-between'>
                        <span>Link to Campaign Asset</span>
                        <IconBrandLinkedin className='size-3.5 text-sky-500' />
                      </Label>
                      <div className='flex gap-2'>
                        <select
                          className='flex-1 rounded-md border border-input bg-background px-2.5 py-1 text-xs shadow-xs focus:border-ring focus:outline-hidden'
                          value={selectedAssetId}
                          onChange={(e) => onSetSelectedAssetId(e.target.value)}
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
                          onClick={onAttach}
                          className='text-xs shrink-0'
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
              <div className='flex flex-col items-center justify-center rounded-xl border border-destructive/30 bg-destructive/5 p-8 text-center w-full min-h-[280px]'>
                <Icons.warning className='size-8 text-destructive mb-3' />
                <p className='font-semibold text-sm text-destructive'>Generation Failed</p>
                <p className='text-xs text-muted-foreground mt-1 max-w-sm'>{result.error}</p>
                {onRetry && (
                  <Button variant='outline' size='sm' className='mt-4 text-xs' onClick={onRetry}>
                    Retry Generation
                  </Button>
                )}
              </div>
            ) : (
              <div className='flex flex-col items-center justify-center rounded-xl border border-dashed p-10 text-center w-full min-h-[300px] text-muted-foreground'>
                <Icons.video className='size-12 stroke-[1.2] mb-3 opacity-50' />
                <p className='text-sm font-medium'>No video available</p>
                <p className='text-xs max-w-xs mt-1'>
                  Generate a video in the studio or select a record from Video History to preview it
                  here.
                </p>
              </div>
            )}
          </TabsContent>

          {/* Tab 2: Brand Marker Studio */}
          <TabsContent
            value='brand'
            className='flex-1 overflow-y-auto p-5 sm:p-6 mt-0 space-y-4 focus-visible:outline-none'
          >
            <BrandMarkerStudio
              videoResult={result}
              aspectRatio={aspectRatio}
              videoUrlOverride={brandMarkerVideoOverride}
              activeRecordId={activeRecordId}
              onExportSaved={onExportSaved}
            />
          </TabsContent>
        </Tabs>
      </div>
    </div>,
    document.body
  );
}
