'use client';

import React, { useRef, useState } from 'react';
import type { VideoAspectRatio } from '@/lib/api/types';
import type { LogoConfig, TextConfig } from '../types/brand-types';
import { Icons } from '@/components/icons';
import { Badge } from '@/components/ui/badge';

interface BrandCanvasProps {
  videoSrc: string;
  logoSrc: string | null;
  logoConfig: LogoConfig;
  onLogoConfigChange: (updater: (prev: LogoConfig) => LogoConfig) => void;
  textConfig: TextConfig;
  onTextConfigChange: (updater: (prev: TextConfig) => TextConfig) => void;
  textEnabled: boolean;
  aspectRatio: VideoAspectRatio;
}

export function BrandCanvas({
  videoSrc,
  logoSrc,
  logoConfig,
  onLogoConfigChange,
  textConfig,
  onTextConfigChange,
  textEnabled,
  aspectRatio
}: BrandCanvasProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);

  const [isPlaying, setIsPlaying] = useState(true);
  const [activeTarget, setActiveTarget] = useState<'logo' | 'text' | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  // Aspect ratio styling
  const getAspectRatioClasses = () => {
    switch (aspectRatio) {
      case '9:16':
        return 'max-w-[270px] aspect-[9/16]';
      case '1:1':
        return 'max-w-[340px] aspect-square';
      case '4:3':
        return 'max-w-[380px] aspect-[4/3]';
      case '3:4':
        return 'max-w-[280px] aspect-[3/4]';
      case '21:9':
        return 'max-w-[460px] aspect-[21/9]';
      case '16:9':
      default:
        return 'w-full aspect-video';
    }
  };

  const togglePlay = () => {
    if (!videoRef.current) return;
    if (videoRef.current.paused) {
      videoRef.current.play();
      setIsPlaying(true);
    } else {
      videoRef.current.pause();
      setIsPlaying(false);
    }
  };

  const handlePointerDown = (target: 'logo' | 'text', e: React.PointerEvent) => {
    e.stopPropagation();
    setActiveTarget(target);
    setIsDragging(true);
    (e.target as HTMLElement).setPointerCapture(e.pointerId);
  };

  const handlePointerMove = (e: React.PointerEvent) => {
    if (!isDragging || !activeTarget || !containerRef.current) return;

    const rect = containerRef.current.getBoundingClientRect();
    const rawX = ((e.clientX - rect.left) / rect.width) * 100;
    const rawY = ((e.clientY - rect.top) / rect.height) * 100;

    // Clamp between 5% and 95%
    const clampedX = Math.max(5, Math.min(95, Math.round(rawX)));
    const clampedY = Math.max(5, Math.min(95, Math.round(rawY)));

    if (activeTarget === 'logo') {
      onLogoConfigChange((prev) => ({
        ...prev,
        x: clampedX,
        y: clampedY,
        anchor: 'custom'
      }));
    } else if (activeTarget === 'text') {
      onTextConfigChange((prev) => ({
        ...prev,
        x: clampedX,
        y: clampedY
      }));
    }
  };

  const handlePointerUp = (e: React.PointerEvent) => {
    if (isDragging) {
      setIsDragging(false);
      try {
        (e.target as HTMLElement).releasePointerCapture(e.pointerId);
      } catch {
        // Ignored if already released
      }
    }
  };

  return (
    <div className='flex flex-col items-center w-full space-y-3'>
      {/* Video Container with Interactive Canvas / Overlay */}
      <div
        ref={containerRef}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        className={`relative mx-auto overflow-hidden rounded-xl bg-black shadow-xl ring-1 ring-border/30 select-none ${getAspectRatioClasses()}`}
      >
        <video
          ref={videoRef}
          src={videoSrc}
          autoPlay
          loop
          muted
          playsInline
          onPlay={() => setIsPlaying(true)}
          onPause={() => setIsPlaying(false)}
          className='h-full w-full object-contain pointer-events-none'
        >
          <track kind='captions' />
        </video>

        {/* Logo Marker Overlay */}
        {logoSrc && (
          <div
            onPointerDown={(e) => handlePointerDown('logo', e)}
            style={{
              left: `${logoConfig.x}%`,
              top: `${logoConfig.y}%`,
              opacity: logoConfig.opacity / 100,
              transform: `translate(-50%, -50%) scale(${logoConfig.scale / 100})`
            }}
            className={`absolute cursor-grab active:cursor-grabbing transition-transform duration-75 touch-none group ${
              activeTarget === 'logo'
                ? 'ring-2 ring-primary ring-offset-2 ring-offset-black/50 rounded-sm'
                : 'hover:ring-1 hover:ring-primary/60'
            }`}
          >
            {/* Logo Image */}
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={logoSrc}
              alt='Brand Logo'
              draggable={false}
              className='max-w-[90px] max-h-[90px] object-contain drop-shadow-[0_4px_8px_rgba(0,0,0,0.6)] pointer-events-none'
            />

            {/* Drag Handle Indicator badge */}
            <div className='absolute -top-5 left-1/2 -translate-x-1/2 opacity-0 group-hover:opacity-100 transition-opacity bg-black/80 backdrop-blur-xs text-white text-[9px] px-1.5 py-0.5 rounded-sm whitespace-nowrap pointer-events-none border border-white/20'>
              Drag to position
            </div>
          </div>
        )}

        {/* Custom Text Overlay */}
        {textEnabled && textConfig.text.trim() && (
          <div
            onPointerDown={(e) => handlePointerDown('text', e)}
            style={{
              left: `${textConfig.x}%`,
              top: `${textConfig.y}%`,
              fontSize: `${textConfig.fontSize}px`,
              color: textConfig.color,
              fontStyle: textConfig.italic ? 'italic' : 'normal',
              fontWeight: textConfig.bold ? 'bold' : 'normal',
              transform: 'translate(-50%, -50%)'
            }}
            className={`absolute cursor-grab active:cursor-grabbing font-sans text-center drop-shadow-[0_2px_6px_rgba(0,0,0,0.85)] px-2 py-0.5 whitespace-nowrap transition-transform duration-75 touch-none group ${
              activeTarget === 'text'
                ? 'ring-2 ring-emerald-500 ring-offset-2 ring-offset-black/50 rounded-sm'
                : 'hover:ring-1 hover:ring-emerald-500/60'
            }`}
          >
            {textConfig.text}

            <div className='absolute -bottom-5 left-1/2 -translate-x-1/2 opacity-0 group-hover:opacity-100 transition-opacity bg-black/80 backdrop-blur-xs text-white text-[9px] px-1.5 py-0.5 rounded-sm whitespace-nowrap pointer-events-none border border-white/20'>
              Drag text
            </div>
          </div>
        )}

        {/* Floating Quick Play / Pause overlay */}
        <div className='absolute bottom-2 left-2 flex items-center gap-1.5 bg-black/60 backdrop-blur-md px-2 py-1 rounded-full border border-white/10'>
          <button
            type='button'
            onClick={togglePlay}
            className='text-white/80 hover:text-white transition-colors'
            title={isPlaying ? 'Pause video' : 'Play video'}
          >
            {isPlaying ? (
              <Icons.minus className='size-3.5' />
            ) : (
              <Icons.arrowRight className='size-3.5' />
            )}
          </button>
          <span className='text-[10px] font-mono text-zinc-300'>
            {isPlaying ? 'Playing' : 'Paused'}
          </span>
        </div>

        {/* Watermark mode badge */}
        <div className='absolute top-2 right-2'>
          <Badge
            variant='secondary'
            className='bg-black/70 backdrop-blur-md text-zinc-200 border-white/15 text-[10px] py-0 px-2'
          >
            Live Overlay
          </Badge>
        </div>
      </div>

      {/* Guide text */}
      <p className='text-[11px] text-muted-foreground text-center flex items-center gap-1.5'>
        <Icons.info className='size-3.5 text-primary' />
        Click and drag the logo or text directly on the preview to adjust position.
      </p>
    </div>
  );
}
