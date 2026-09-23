'use client';

import { useState, useCallback } from 'react';
import { toast } from 'sonner';
import type { LogoConfig, TextConfig, LogoAnchor, WatermarkLogo } from './types';

export const DEFAULT_LOGO_CONFIG: LogoConfig = {
  x: 85,
  y: 85,
  scale: 80,
  opacity: 90,
  padding: 24,
  anchor: 'bottom-right'
};

export const DEFAULT_TEXT_CONFIG: TextConfig = {
  text: '',
  x: 50,
  y: 92,
  fontSize: 22,
  color: '#ffffff',
  bold: true,
  italic: false
};

export function getCoordinatesForAnchor(anchor: LogoAnchor): { x: number; y: number } {
  switch (anchor) {
    case 'top-left':
      return { x: 15, y: 15 };
    case 'top-right':
      return { x: 85, y: 15 };
    case 'bottom-left':
      return { x: 15, y: 85 };
    case 'bottom-right':
      return { x: 85, y: 85 };
    case 'center':
      return { x: 50, y: 50 };
    case 'custom':
    default:
      return { x: 85, y: 85 };
  }
}

export function useWatermarkComposer() {
  const [logoFile, setLogoFileState] = useState<File | null>(null);
  const [logos, setLogos] = useState<WatermarkLogo[]>([
    {
      id: 'logo-primary',
      logoPath: '/logo/Jade.png',
      name: 'Jade',
      anchor: 'bottom-right',
      scale: 80,
      opacity: 90,
      padding: 24,
      x: 85,
      y: 85
    }
  ]);
  const [activeLogoId, setActiveLogoId] = useState<string>('logo-primary');

  const [textConfig, setTextConfig] = useState<TextConfig>(DEFAULT_TEXT_CONFIG);
  const [textEnabled, setTextEnabled] = useState<boolean>(false);

  const [isExporting, setIsExporting] = useState<boolean>(false);
  const [exportProgress, setExportProgress] = useState<number>(0);

  const activeLogo = logos.find((l) => l.id === activeLogoId) || logos[0];

  const setLogoFile = useCallback((file: File | null) => {
    setLogoFileState(file);
    if (file) {
      const url = URL.createObjectURL(file);
      setLogos((prev) =>
        prev.map((l, idx) =>
          idx === 0
            ? { ...l, logoPath: url, name: file.name }
            : l
        )
      );
    }
  }, []);

  const addLogo = useCallback((logoPartial: Partial<WatermarkLogo>) => {
    const newId = `logo-${Date.now()}`;
    const anchor = logoPartial.anchor || 'top-left';
    const coords = getCoordinatesForAnchor(anchor);
    const newLogo: WatermarkLogo = {
      id: newId,
      logoPath: logoPartial.logoPath || '/logo/ja.png',
      name: logoPartial.name || 'Brand Logo',
      anchor,
      scale: logoPartial.scale ?? 60,
      opacity: logoPartial.opacity ?? 90,
      padding: 24,
      x: logoPartial.x ?? coords.x,
      y: logoPartial.y ?? coords.y
    };
    setLogos((prev) => [...prev, newLogo]);
    setActiveLogoId(newId);
    return newId;
  }, []);

  const removeLogo = useCallback((id: string) => {
    setLogos((prev) => {
      if (prev.length <= 1) {
        toast.error('At least one watermark logo must remain');
        return prev;
      }
      const next = prev.filter((l) => l.id !== id);
      setActiveLogoId(next[0]?.id || '');
      return next;
    });
  }, []);

  const updateLogo = useCallback((id: string, updates: Partial<WatermarkLogo>) => {
    setLogos((prev) =>
      prev.map((l) => {
        if (l.id !== id) return l;
        const updated = { ...l, ...updates };
        if (updates.anchor && updates.anchor !== 'custom' && updates.x === undefined && updates.y === undefined) {
          const coords = getCoordinatesForAnchor(updates.anchor);
          updated.x = coords.x;
          updated.y = coords.y;
        }
        return updated;
      })
    );
  }, []);

  const setAnchorForLogo = useCallback((id: string, anchor: LogoAnchor) => {
    updateLogo(id, { anchor });
  }, [updateLogo]);

  const setPresetLogo = useCallback((url: string, name?: string) => {
    const safeUrl = url || '/logo/ja.png';
    setLogoFileState(null);
    setLogos((prev) => {
      if (prev.length === 0) {
        return [{
          id: 'logo-primary',
          logoPath: safeUrl,
          name: name || 'Primary Logo',
          anchor: 'bottom-right',
          scale: 80,
          opacity: 90,
          padding: 24,
          x: 85,
          y: 85
        }];
      }
      return prev.map((l, idx) =>
        idx === 0 ? { ...l, logoPath: safeUrl, name: name || l.name } : l
      );
    });
  }, []);

  const setAnchor = useCallback((anchor: LogoAnchor) => {
    if (activeLogo) {
      setAnchorForLogo(activeLogo.id, anchor);
    }
  }, [activeLogo, setAnchorForLogo]);

  // Backward compatibility object for single logo callers
  const logoConfig: LogoConfig = {
    anchor: activeLogo?.anchor || 'bottom-right',
    x: activeLogo?.x ?? 85,
    y: activeLogo?.y ?? 85,
    scale: activeLogo?.scale ?? 80,
    opacity: activeLogo?.opacity ?? 90,
    padding: activeLogo?.padding ?? 24
  };

  const setLogoConfig = useCallback(
    (updater: LogoConfig | ((prev: LogoConfig) => LogoConfig)) => {
      if (!activeLogo) return;
      const nextConfig = typeof updater === 'function' ? updater(logoConfig) : updater;
      updateLogo(activeLogo.id, {
        anchor: nextConfig.anchor,
        x: nextConfig.x,
        y: nextConfig.y,
        scale: nextConfig.scale,
        opacity: nextConfig.opacity,
        padding: nextConfig.padding
      });
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [activeLogo?.id, updateLogo, logoConfig.x, logoConfig.y, logoConfig.scale, logoConfig.opacity, logoConfig.anchor]
  );

  // Composite static Image on 2D Canvas with Multi-Logo support
  const compositeImage = useCallback(
    async (
      imageSrc: string
    ): Promise<{ blob: Blob; dataUrl: string }> => {
      return new Promise((resolve, reject) => {
        const baseImg = new Image();
        baseImg.crossOrigin = 'anonymous';

        baseImg.onload = async () => {
          try {
            const width = baseImg.naturalWidth || 1080;
            const height = baseImg.naturalHeight || 1080;

            const canvas = document.createElement('canvas');
            canvas.width = width;
            canvas.height = height;
            const ctx = canvas.getContext('2d');
            if (!ctx) {
              return reject(new Error('Canvas context unavailable'));
            }

            // Draw base image
            ctx.drawImage(baseImg, 0, 0, width, height);

            // Draw all logos in sequence
            for (const logo of logos) {
              if (!logo.logoPath) continue;
              const lImg = new Image();
              lImg.crossOrigin = 'anonymous';
              await new Promise<void>((res) => {
                lImg.onload = () => res();
                lImg.onerror = () => res();
                lImg.src = logo.logoPath;
              });

              if (lImg.naturalWidth > 0) {
                ctx.save();
                ctx.globalAlpha = (logo.opacity ?? 90) / 100;
                const baseSize = width * 0.22;
                const aspect = lImg.naturalHeight / lImg.naturalWidth;
                const logoW = baseSize * ((logo.scale ?? 80) / 100);
                const logoH = logoW * aspect;
                const lx = logo.x ?? 85;
                const ly = logo.y ?? 85;
                const logoX = (width * lx) / 100 - logoW / 2;
                const logoY = (height * ly) / 100 - logoH / 2;

                ctx.shadowColor = 'rgba(0,0,0,0.55)';
                ctx.shadowBlur = 10;
                ctx.shadowOffsetX = 2;
                ctx.shadowOffsetY = 2;

                ctx.drawImage(lImg, logoX, logoY, logoW, logoH);
                ctx.restore();
              }
            }

            // Draw text overlay if enabled
            if (textEnabled && textConfig.text.trim()) {
              ctx.save();
              const fontStyle = textConfig.italic ? 'italic ' : '';
              const fontWeight = textConfig.bold ? 'bold ' : '';
              const scaleFactor = width / 720;
              const computedFontSize = Math.max(14, Math.round(textConfig.fontSize * scaleFactor));
              ctx.font = `${fontStyle}${fontWeight}${computedFontSize}px system-ui, -apple-system, sans-serif`;
              ctx.fillStyle = textConfig.color;
              ctx.textAlign = 'center';
              ctx.textBaseline = 'middle';

              ctx.shadowColor = 'rgba(0,0,0,0.85)';
              ctx.shadowBlur = 8;
              ctx.shadowOffsetX = 1;
              ctx.shadowOffsetY = 2;

              const textX = (width * textConfig.x) / 100;
              const textY = (height * textConfig.y) / 100;
              ctx.fillText(textConfig.text, textX, textY);
              ctx.restore();
            }

            canvas.toBlob((blob) => {
              if (blob) {
                const dataUrl = canvas.toDataURL('image/png');
                resolve({ blob, dataUrl });
              } else {
                reject(new Error('Failed to create image blob from canvas'));
              }
            }, 'image/png');
          } catch (err) {
            reject(err);
          }
        };

        baseImg.onerror = () => reject(new Error('Failed to load image for watermarking'));
        baseImg.src = imageSrc;
      });
    },
    [logos, textConfig, textEnabled]
  );

  // Composite Video frame-by-frame using MediaRecorder with Multi-Logo support
  const compositeVideo = useCallback(
    async (
      videoSrc: string,
      originalFileName: string = 'aura_reel.mp4',
      onComplete?: (result: { blob: Blob; url: string; fileName: string }) => void
    ) => {
      if (!videoSrc) {
        toast.error('No video source available for export');
        return;
      }

      setIsExporting(true);
      setExportProgress(0);

      try {
        const video = document.createElement('video');
        video.crossOrigin = 'anonymous';
        video.src = videoSrc;
        video.muted = true;
        video.playsInline = true;

        await new Promise<void>((resolve, reject) => {
          video.addEventListener('loadedmetadata', () => resolve(), { once: true });
          video.addEventListener(
            'error',
            () => reject(new Error('Failed to load video element for compositing.')),
            { once: true }
          );
        });

        const width = video.videoWidth || 720;
        const height = video.videoHeight || 1280;

        const canvas = document.createElement('canvas');
        canvas.width = width;
        canvas.height = height;
        const ctx = canvas.getContext('2d');
        if (!ctx) throw new Error('Canvas 2D context not supported.');

        // Preload all logos
        const loadedLogos: Array<{ img: HTMLImageElement; logo: WatermarkLogo }> = [];
        for (const logo of logos) {
          if (!logo.logoPath) continue;
          const img = new Image();
          img.crossOrigin = 'anonymous';
          await new Promise<void>((res) => {
            img.onload = () => res();
            img.onerror = () => res();
            img.src = logo.logoPath;
          });
          if (img.naturalWidth > 0) {
            loadedLogos.push({ img, logo });
          }
        }

        const possibleMimes = [
          'video/mp4;codecs=avc1',
          'video/mp4',
          'video/webm;codecs=vp9,opus',
          'video/webm;codecs=vp8,opus',
          'video/webm'
        ];

        let mimeType = '';
        for (const mime of possibleMimes) {
          if (MediaRecorder.isTypeSupported(mime)) {
            mimeType = mime;
            break;
          }
        }

        if (!mimeType) {
          throw new Error('No supported video recording formats found in this browser.');
        }

        const stream = canvas.captureStream(30);
        const recorder = new MediaRecorder(stream, {
          mimeType,
          videoBitsPerSecond: 8000000
        });

        const chunks: Blob[] = [];
        recorder.addEventListener('dataavailable', (e: BlobEvent) => {
          if (e.data && e.data.size > 0) chunks.push(e.data);
        });

        const exportPromise = new Promise<void>((resolve, reject) => {
          recorder.addEventListener(
            'stop',
            () => {
              try {
                const extension = mimeType.includes('mp4') ? 'mp4' : 'webm';
                const blob = new Blob(chunks, { type: mimeType });
                const url = URL.createObjectURL(blob);
                const finalFileName = `branded_${originalFileName.replace(/\.[^/.]+$/, '')}.${extension}`;
                if (onComplete) onComplete({ blob, url, fileName: finalFileName });
                resolve();
              } catch (err) {
                reject(err);
              }
            },
            { once: true }
          );

          recorder.addEventListener(
            'error',
            (e: Event) => {
              const errorEvent = e as unknown as { error?: Error };
              reject(new Error(`Recording error: ${errorEvent.error?.message || 'unknown'}`));
            },
            { once: true }
          );
        });

        recorder.start(100);
        video.currentTime = 0;
        await video.play();

        const renderFrame = () => {
          if (video.paused && !video.ended) {
            requestAnimationFrame(renderFrame);
            return;
          }

          ctx.drawImage(video, 0, 0, width, height);

          // Draw all configured logos
          for (const item of loadedLogos) {
            const logo = item.logo;
            ctx.save();
            ctx.globalAlpha = (logo.opacity ?? 90) / 100;
            const baseSize = width * 0.22;
            const aspect = item.img.naturalHeight / item.img.naturalWidth;
            const logoW = baseSize * ((logo.scale ?? 80) / 100);
            const logoH = logoW * aspect;
            const lx = logo.x ?? 85;
            const ly = logo.y ?? 85;
            const logoX = (width * lx) / 100 - logoW / 2;
            const logoY = (height * ly) / 100 - logoH / 2;

            ctx.shadowColor = 'rgba(0,0,0,0.55)';
            ctx.shadowBlur = 8;
            ctx.shadowOffsetX = 2;
            ctx.shadowOffsetY = 2;

            ctx.drawImage(item.img, logoX, logoY, logoW, logoH);
            ctx.restore();
          }

          if (textEnabled && textConfig.text.trim()) {
            ctx.save();
            const fontStyle = textConfig.italic ? 'italic ' : '';
            const fontWeight = textConfig.bold ? 'bold ' : '';
            const scaleFactor = width / 720;
            const computedFontSize = Math.max(12, Math.round(textConfig.fontSize * scaleFactor));
            ctx.font = `${fontStyle}${fontWeight}${computedFontSize}px system-ui, -apple-system, sans-serif`;
            ctx.fillStyle = textConfig.color;
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';

            ctx.shadowColor = 'rgba(0,0,0,0.85)';
            ctx.shadowBlur = 6;
            ctx.shadowOffsetX = 1;
            ctx.shadowOffsetY = 2;

            const textX = (width * textConfig.x) / 100;
            const textY = (height * textConfig.y) / 100;
            ctx.fillText(textConfig.text, textX, textY);
            ctx.restore();
          }

          if (video.duration > 0) {
            const pct = Math.min(99, Math.round((video.currentTime / video.duration) * 100));
            setExportProgress(pct);
          }

          if (!video.ended) {
            requestAnimationFrame(renderFrame);
          }
        };

        requestAnimationFrame(renderFrame);

        await new Promise<void>((res) => {
          video.addEventListener('ended', () => res(), { once: true });
        });

        await new Promise((r) => setTimeout(r, 200));
        recorder.stop();
        setExportProgress(100);
        await exportPromise;
      } catch (err: unknown) {
        const errorMsg = err instanceof Error ? err.message : 'Video compositing error';
        console.error('Video composite error:', err);
        toast.error(`Video compositing failed: ${errorMsg}`);
      } finally {
        setIsExporting(false);
      }
    },
    [logos, textConfig, textEnabled]
  );

  return {
    logoFile,
    setLogoFile,
    logos,
    activeLogoId,
    activeLogo,
    setActiveLogoId,
    addLogo,
    removeLogo,
    updateLogo,
    setAnchorForLogo,
    logoSrc: activeLogo?.logoPath || null,
    setPresetLogo,
    logoConfig,
    setLogoConfig,
    setAnchor,
    textConfig,
    setTextConfig,
    textEnabled,
    setTextEnabled,
    isExporting,
    exportProgress,
    compositeImage,
    compositeVideo
  };
}
