'use client';

import { useState, useCallback } from 'react';
import { toast } from 'sonner';
import type { LogoConfig, TextConfig, LogoAnchor } from './types';

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

export function useWatermarkComposer() {
  const [logoFile, setLogoFileState] = useState<File | null>(null);
  const [logoSrc, setLogoSrc] = useState<string | null>(null);
  const [logoConfig, setLogoConfig] = useState<LogoConfig>(DEFAULT_LOGO_CONFIG);

  const [textConfig, setTextConfig] = useState<TextConfig>(DEFAULT_TEXT_CONFIG);
  const [textEnabled, setTextEnabled] = useState<boolean>(false);

  const [isExporting, setIsExporting] = useState<boolean>(false);
  const [exportProgress, setExportProgress] = useState<number>(0);

  const setLogoFile = useCallback((file: File | null) => {
    setLogoFileState(file);
    if (file) {
      const url = URL.createObjectURL(file);
      setLogoSrc(url);
    } else {
      setLogoSrc(null);
    }
  }, []);

  const setPresetLogo = useCallback((url: string) => {
    setLogoFileState(null);
    setLogoSrc(url);
  }, []);

  const setAnchor = useCallback((anchor: LogoAnchor) => {
    setLogoConfig((prev) => {
      let x = prev.x;
      let y = prev.y;

      switch (anchor) {
        case 'top-left':
          x = 15;
          y = 15;
          break;
        case 'top-right':
          x = 85;
          y = 15;
          break;
        case 'bottom-left':
          x = 15;
          y = 85;
          break;
        case 'bottom-right':
          x = 85;
          y = 85;
          break;
        case 'center':
          x = 50;
          y = 50;
          break;
        case 'custom':
        default:
          break;
      }

      return {
        ...prev,
        anchor,
        x,
        y
      };
    });
  }, []);

  // Composite static Image on 2D Canvas
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

            // Draw logo if present
            if (logoSrc) {
              const lImg = new Image();
              lImg.crossOrigin = 'anonymous';
              await new Promise<void>((res) => {
                lImg.onload = () => res();
                lImg.onerror = () => res();
                lImg.src = logoSrc;
              });

              if (lImg.naturalWidth > 0) {
                ctx.save();
                ctx.globalAlpha = logoConfig.opacity / 100;
                const baseSize = width * 0.22;
                const aspect = lImg.naturalHeight / lImg.naturalWidth;
                const logoW = baseSize * (logoConfig.scale / 100);
                const logoH = logoW * aspect;
                const logoX = (width * logoConfig.x) / 100 - logoW / 2;
                const logoY = (height * logoConfig.y) / 100 - logoH / 2;

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
    [logoSrc, logoConfig, textConfig, textEnabled]
  );

  // Composite Video frame-by-frame using MediaRecorder
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

        let logoImg: HTMLImageElement | null = null;
        if (logoSrc) {
          logoImg = new Image();
          logoImg.crossOrigin = 'anonymous';
          await new Promise<void>((resolve) => {
            if (!logoImg) return resolve();
            logoImg.addEventListener('load', () => resolve(), { once: true });
            logoImg.addEventListener('error', () => resolve(), { once: true });
            logoImg.src = logoSrc;
          });
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
          if (video.paused || video.ended) return;

          ctx.drawImage(video, 0, 0, width, height);

          if (logoImg && logoImg.complete && logoImg.naturalWidth > 0) {
            ctx.save();
            ctx.globalAlpha = logoConfig.opacity / 100;
            const baseSize = width * 0.22;
            const aspect = logoImg.naturalHeight / logoImg.naturalWidth;
            const logoW = baseSize * (logoConfig.scale / 100);
            const logoH = logoW * aspect;
            const logoX = (width * logoConfig.x) / 100 - logoW / 2;
            const logoY = (height * logoConfig.y) / 100 - logoH / 2;

            ctx.shadowColor = 'rgba(0,0,0,0.55)';
            ctx.shadowBlur = 8;
            ctx.shadowOffsetX = 2;
            ctx.shadowOffsetY = 2;

            ctx.drawImage(logoImg, logoX, logoY, logoW, logoH);
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
    [logoSrc, logoConfig, textConfig, textEnabled]
  );

  return {
    logoFile,
    setLogoFile,
    logoSrc,
    setLogoSrc,
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
