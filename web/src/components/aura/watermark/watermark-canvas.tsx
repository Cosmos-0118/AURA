'use client';

import React, { useRef, useState } from 'react';
import type { LogoConfig, TextConfig, WatermarkLogo } from './types';
import { Icons } from '@/components/icons';
import { Badge } from '@/components/ui/badge';

interface WatermarkCanvasProps {
  mediaType: 'image' | 'video';
  mediaSrc: string;
  logoSrc?: string | null;
  logoConfig?: LogoConfig;
  onLogoConfigChange?: (updater: (prev: LogoConfig) => LogoConfig) => void;
  logos?: WatermarkLogo[];
  activeLogoId?: string;
  onSelectLogo?: (id: string) => void;
  onLogoChange?: (id: string, updates: Partial<WatermarkLogo>) => void;
  textConfig: TextConfig;
  onTextConfigChange: (updater: (prev: TextConfig) => TextConfig) => void;
  textEnabled: boolean;
}

export function WatermarkCanvas({
  mediaType,
  mediaSrc,
  logoSrc,
  logoConfig,
  onLogoConfigChange,
  logos,
  activeLogoId,
  onSelectLogo,
  onLogoChange,
  textConfig,
  onTextConfigChange,
  textEnabled
}: WatermarkCanvasProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);

  const [isPlaying, setIsPlaying] = useState(true);
  const [activeTarget, setActiveTarget] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);

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

  const handlePointerDown = (targetId: string, e: React.PointerEvent) => {
    e.stopPropagation();
    setActiveTarget(targetId);
    if (targetId !== 'text' && onSelectLogo) {
      onSelectLogo(targetId);
    }
    setIsDragging(true);
    (e.target as HTMLElement).setPointerCapture(e.pointerId);
  };

  const handlePointerMove = (e: React.PointerEvent) => {
    if (!isDragging || !activeTarget || !containerRef.current) return;

    const rect = containerRef.current.getBoundingClientRect();
    const rawX = ((e.clientX - rect.left) / rect.width) * 100;
    const rawY = ((e.clientY - rect.top) / rect.height) * 100;

    const clampedX = Math.max(5, Math.min(95, Math.round(rawX)));
    const clampedY = Math.max(5, Math.min(95, Math.round(rawY)));

    if (activeTarget === 'text') {
      onTextConfigChange((prev) => ({
        ...prev,
        x: clampedX,
        y: clampedY
      }));
    } else if (logos && onLogoChange) {
      onLogoChange(activeTarget, {
        x: clampedX,
        y: clampedY,
        anchor: 'custom'
      });
    } else if (onLogoConfigChange) {
      onLogoConfigChange((prev) => ({
        ...prev,
        x: clampedX,
        y: clampedY,
        anchor: 'custom'
      }));
    }
  };

  const handlePointerUp = (e: React.PointerEvent) => {
    if (isDragging) {
      setIsDragging(false);
      try {
        (e.target as HTMLElement).releasePointerCapture(e.pointerId);
      } catch {
        // Ignored
      }
    }
  };

  const containerAspect =
    mediaType === 'image'
      ? 'w-full max-w-[380px] aspect-square'
      : 'w-full max-w-[270px] aspect-[9/16]';

  // Determine list of logos to render
  const renderedLogos: WatermarkLogo[] =
    logos && logos.length > 0
      ? logos
      : logoSrc && logoConfig
      ? [
          {
            id: 'default',
            logoPath: logoSrc,
            anchor: logoConfig.anchor,
            scale: logoConfig.scale,
            opacity: logoConfig.opacity,
            x: logoConfig.x,
            y: logoConfig.y
          }
        ]
      : [];

  return (
    <div className='flex flex-col items-center w-full space-y-3'>
      {/* Media Container with Interactive Canvas / Overlay */}
      <div
        ref={containerRef}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        className={`relative mx-auto overflow-hidden rounded-xl bg-black shadow-2xl ring-1 ring-border/40 select-none ${containerAspect}`}
      >
        {mediaType === 'image' ? (
          /* eslint-disable-next-line @next/next/no-img-element */
          <img
            src={mediaSrc}
            alt='Marketing Poster'
            className='h-full w-full object-contain pointer-events-none'
          />
        ) : (
          <video
            ref={videoRef}
            src={mediaSrc}
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
        )}

        {/* Multi-Logo Overlays */}
        {renderedLogos.map((logo) => {
          const isSelected = activeLogoId === logo.id || activeTarget === logo.id;
          return (
            <div
              key={logo.id}
              onPointerDown={(e) => handlePointerDown(logo.id, e)}
              style={{
                left: `${logo.x ?? 85}%`,
                top: `${logo.y ?? 85}%`,
                opacity: (logo.opacity ?? 90) / 100,
                transform: `translate(-50%, -50%) scale(${(logo.scale ?? 80) / 100})`
              }}
              className={`absolute cursor-grab active:cursor-grabbing transition-transform duration-75 touch-none group ${
                isSelected
                  ? 'ring-2 ring-primary ring-offset-2 ring-offset-black/50 rounded-sm'
                  : 'hover:ring-1 hover:ring-primary/60'
              }`}
            >
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={logo.logoPath}
                alt={logo.name || 'Brand Logo'}
                draggable={false}
                className='max-w-[90px] max-h-[90px] object-contain drop-shadow-[0_4px_8px_rgba(0,0,0,0.6)] pointer-events-none'
              />
              <div className='absolute -top-5 left-1/2 -translate-x-1/2 opacity-0 group-hover:opacity-100 transition-opacity bg-black/80 backdrop-blur-xs text-white text-[9px] px-1.5 py-0.5 rounded-sm whitespace-nowrap pointer-events-none border border-white/20'>
                {logo.name || 'Drag logo'}
              </div>
            </div>
          );
        })}

        {/* Custom Text Overlay */}
        {textEnabled && textConfig.text.trim() && (
          <div
            onPointerDown={(e) => handlePointerDown('text', e)}
            style={{
              left: `${textConfig.x}%`,
              top: `${textConfig.y}%`,
              color: textConfig.color,
              fontSize: `${Math.max(12, Math.round(textConfig.fontSize * 0.75))}px`,
              fontWeight: textConfig.bold ? 'bold' : 'normal',
              fontStyle: textConfig.italic ? 'italic' : 'normal',
              transform: 'translate(-50%, -50%)'
            }}
            className={`absolute cursor-grab active:cursor-grabbing text-center max-w-[90%] break-words px-2 py-1 select-none transition-transform duration-75 touch-none group drop-shadow-[0_2px_4px_rgba(0,0,0,0.8)] ${
              activeTarget === 'text'
                ? 'ring-2 ring-primary ring-offset-2 ring-offset-black/50 rounded-sm'
                : 'hover:ring-1 hover:ring-primary/60'
            }`}
          >
            {textConfig.text}
            <div className='absolute -top-5 left-1/2 -translate-x-1/2 opacity-0 group-hover:opacity-100 transition-opacity bg-black/80 backdrop-blur-xs text-white text-[9px] px-1.5 py-0.5 rounded-sm whitespace-nowrap pointer-events-none border border-white/20 font-sans font-normal'>
              Drag text
            </div>
          </div>
        )}

        {/* Video Play/Pause Overlay Control */}
        {mediaType === 'video' && (
          <button
            onClick={togglePlay}
            aria-label={isPlaying ? 'Pause video preview' : 'Play video preview'}
            className='absolute bottom-2 left-2 z-10 flex h-7 w-7 items-center justify-center rounded-full bg-black/60 text-white backdrop-blur-xs hover:bg-black/80 transition-colors'
          >
            {isPlaying ? (
              <Icons.close className='size-3.5 rotate-45' />
            ) : (
              <Icons.video className='size-3.5 translate-x-0.5' />
            )}
          </button>
        )}

        {/* Format Indicator Badge */}
        <div className='absolute top-2 right-2 pointer-events-none'>
          <Badge
            variant='outline'
            className='bg-black/60 text-white text-[10px] backdrop-blur-xs border-white/20 font-mono px-1.5 py-0'
          >
            {mediaType === 'image' ? '1:1 Square' : '9:16 Reel'}
          </Badge>
        </div>
      </div>

      <p className='text-[11px] text-muted-foreground flex items-center gap-1.5'>
        <Icons.info className='size-3.5 text-primary' />
        Drag logos or text directly on the canvas to reposition freely.
      </p>
    </div>
  );
}
