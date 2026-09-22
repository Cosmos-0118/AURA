'use client';

import React, { useState, useEffect, useCallback, startTransition, useRef } from 'react';
import type { VideoGenerationRecord } from '@/lib/api/types';
import { listVideoHistory } from '@/lib/api/client';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Icons } from '@/components/icons';
import { Skeleton } from '@/components/ui/skeleton';
import {
  IconDownload,
  IconSparkles,
  IconRefresh,
  IconAlertTriangle,
  IconPlayerPlay,
  IconVideoOff,
  IconFilter,
  IconCheck
} from '@tabler/icons-react';

const LOCAL_STORAGE_KEY = 'aura_video_generation_history_v2';

const BRAND_LABELS: Record<string, string> = {
  jade: 'J Jewellers',
  doctorshield: 'Doctor Shield',
  jaguar: 'Jagrut Trust'
};

const BRAND_COLORS: Record<string, string> = {
  jade: 'border-emerald-500/40 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400',
  doctorshield: 'border-sky-500/40 bg-sky-500/10 text-sky-600 dark:text-sky-400',
  jaguar: 'border-amber-500/40 bg-amber-500/10 text-amber-600 dark:text-amber-400'
};

function formatRelativeTime(isoString: string): string {
  const diff = Date.now() - new Date(isoString).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'Just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

function formatAbsoluteTime(isoString: string): string {
  return new Date(isoString).toLocaleString('en-GB', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });
}

function formatBytes(bytes?: number | null): string {
  if (!bytes) return '';
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

// Skeleton shimmer row
function HistorySkeleton() {
  return (
    <div className='flex items-start gap-4 p-4 border-b border-border/50 last:border-0'>
      <Skeleton className='w-[72px] h-[128px] rounded-lg shrink-0' />
      <div className='flex-1 space-y-2.5 pt-1'>
        <Skeleton className='h-3.5 w-3/4' />
        <Skeleton className='h-3 w-1/2' />
        <div className='flex gap-2 pt-1'>
          <Skeleton className='h-5 w-14 rounded-full' />
          <Skeleton className='h-5 w-14 rounded-full' />
          <Skeleton className='h-5 w-14 rounded-full' />
        </div>
        <div className='flex gap-2 pt-1'>
          <Skeleton className='h-7 w-20 rounded-md' />
          <Skeleton className='h-7 w-24 rounded-md' />
          <Skeleton className='h-7 w-36 rounded-md' />
        </div>
      </div>
    </div>
  );
}

interface HistoryRowProps {
  record: VideoGenerationRecord;
  onOpenInBrandMarker: (url: string, prompt: string, recordId: string) => void;
  onRegenerate: (prompt: string) => void;
}

function HistoryRow({ record, onOpenInBrandMarker, onRegenerate }: HistoryRowProps) {
  const [isExpired, setIsExpired] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);
  const [isHovered, setIsHovered] = useState(false);
  const [videoMode, setVideoMode] = useState<'original' | 'branded'>(
    record.branded_video_url ? 'branded' : 'original'
  );
  const videoRef = useRef<HTMLVideoElement>(null);

  const activeUrl = videoMode === 'branded' ? record.branded_video_url : record.video_url;
  const isCompleted = record.status === 'COMPLETED' && !!activeUrl;
  const isFailed = record.status === 'FAILED';
  const isInProgress = record.status === 'IN_PROGRESS';
  const hasBoth = Boolean(record.video_url && record.branded_video_url);

  const handleVideoError = () => {
    if (activeUrl) setIsExpired(true);
  };

  const handleMouseEnter = () => {
    setIsHovered(true);
    if (videoRef.current && isCompleted && !isExpired) {
      videoRef.current.play().catch(() => {});
    }
  };

  const handleMouseLeave = () => {
    setIsHovered(false);
    if (videoRef.current) {
      videoRef.current.pause();
      videoRef.current.currentTime = 0;
    }
  };

  const promptDisplay =
    record.prompt.length > 85 && !isExpanded ? `${record.prompt.slice(0, 85)}…` : record.prompt;

  const brandKey = record.brand_id ?? 'unknown';
  const brandLabel = BRAND_LABELS[brandKey] ?? brandKey.toUpperCase();
  const brandColorClass = BRAND_COLORS[brandKey] ?? 'border-border bg-muted text-muted-foreground';

  return (
    <div className='flex items-start gap-4 p-4 border-b border-border/40 last:border-0 hover:bg-muted/25 transition-colors group'>
      {/* Thumbnail / Video Preview Area */}
      <div
        className={`relative shrink-0 rounded-lg overflow-hidden bg-zinc-900 shadow-md ${
          record.aspect_ratio === '9:16'
            ? 'w-[56px] h-[100px]'
            : record.aspect_ratio === '1:1'
              ? 'w-[80px] h-[80px]'
              : 'w-[120px] h-[68px]'
        }`}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
      >
        {isCompleted && !isExpired ? (
          <>
            <video
              ref={videoRef}
              key={activeUrl}
              src={activeUrl!}
              muted
              playsInline
              preload='metadata'
              onError={handleVideoError}
              className='w-full h-full object-cover'
            >
              <track kind='captions' />
            </video>
            {!isHovered && (
              <div className='absolute inset-0 flex items-center justify-center bg-black/30'>
                <IconPlayerPlay className='size-4 text-white drop-shadow' />
              </div>
            )}
            {videoMode === 'branded' && (
              <div className='absolute top-1 left-1 bg-emerald-600/90 text-white text-[8px] font-bold px-1 rounded'>
                BRANDED
              </div>
            )}
          </>
        ) : isExpired ? (
          <div className='absolute inset-0 flex flex-col items-center justify-center bg-zinc-800 gap-1'>
            <IconAlertTriangle className='size-5 text-amber-400' />
            <span className='text-[9px] text-amber-400 font-medium text-center leading-tight px-1'>
              Link Expired
            </span>
          </div>
        ) : isFailed ? (
          <div className='absolute inset-0 flex flex-col items-center justify-center bg-zinc-900 gap-1'>
            <IconVideoOff className='size-5 text-destructive/70' />
            <span className='text-[9px] text-destructive/70 font-medium text-center leading-tight px-1'>
              Failed
            </span>
          </div>
        ) : (
          <div className='absolute inset-0 flex flex-col items-center justify-center bg-primary/10 gap-1'>
            <Icons.spinner className='size-5 text-primary animate-spin' />
            <span className='text-[9px] text-primary font-medium text-center leading-tight px-1'>
              In Progress
            </span>
          </div>
        )}
      </div>

      {/* Record Details */}
      <div className='flex-1 min-w-0 space-y-2'>
        {/* Prompt Text */}
        <div className='space-y-0.5'>
          <p className='text-sm text-foreground leading-snug'>
            <span className='font-mono text-[11px] text-muted-foreground select-none mr-1.5'>
              &quot;
            </span>
            {promptDisplay}
            <span className='font-mono text-[11px] text-muted-foreground select-none ml-0.5'>
              &quot;
            </span>
          </p>
          {record.prompt.length > 85 && (
            <button
              type='button'
              onClick={() => setIsExpanded(!isExpanded)}
              className='text-[11px] text-primary hover:underline'
            >
              {isExpanded ? 'Show less' : 'Show full prompt'}
            </button>
          )}
        </div>

        {/* Dual Mode Switcher & Metadata Chips */}
        <div className='flex flex-wrap items-center gap-1.5'>
          {/* Dual video switcher if both versions are available */}
          {hasBoth && (
            <div className='flex items-center rounded-md border border-input bg-muted/60 p-0.5 mr-1'>
              <button
                type='button'
                onClick={() => setVideoMode('original')}
                className={`rounded px-2 py-0.5 text-[10px] font-medium transition-colors ${
                  videoMode === 'original'
                    ? 'bg-background text-foreground shadow-2xs'
                    : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                Original (AI)
              </button>
              <button
                type='button'
                onClick={() => setVideoMode('branded')}
                className={`rounded px-2 py-0.5 text-[10px] font-medium transition-colors ${
                  videoMode === 'branded'
                    ? 'bg-background text-foreground shadow-2xs'
                    : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                Final (Branded)
              </button>
            </div>
          )}

          {record.brand_id && (
            <Badge variant='outline' className={`text-[10px] py-0 px-2 ${brandColorClass}`}>
              {brandLabel}
            </Badge>
          )}
          <Badge variant='secondary' className='text-[10px] py-0 px-2'>
            {record.aspect_ratio}
          </Badge>
          <Badge variant='secondary' className='text-[10px] py-0 px-2'>
            {record.resolution}
          </Badge>
          <Badge variant='secondary' className='text-[10px] py-0 px-2'>
            {record.duration_secs}s
          </Badge>
          {record.branded_video_url && (
            <Badge
              variant='outline'
              className='text-[10px] py-0 px-2 border-emerald-500/40 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 gap-1'
            >
              <IconCheck className='size-3' />
              Branded Export Ready
            </Badge>
          )}

          {/* Status badges */}
          {isExpired && (
            <Badge
              variant='outline'
              className='text-[10px] py-0 px-2 border-amber-500/40 bg-amber-500/10 text-amber-600 dark:text-amber-400 gap-1'
            >
              <IconAlertTriangle className='size-3' />
              Link Expired
            </Badge>
          )}
          {isFailed && (
            <Badge
              variant='outline'
              className='text-[10px] py-0 px-2 border-destructive/40 bg-destructive/10 text-destructive'
            >
              Generation Failed
            </Badge>
          )}
          {isInProgress && (
            <Badge
              variant='outline'
              className='text-[10px] py-0 px-2 border-primary/40 bg-primary/10 text-primary'
            >
              In Progress
            </Badge>
          )}

          {/* Timestamp */}
          <span
            className='text-[10px] text-muted-foreground ml-auto'
            title={formatAbsoluteTime(record.created_at)}
          >
            {formatRelativeTime(record.created_at)}
          </span>
        </div>

        {/* Error message for failed generations */}
        {isFailed && record.error_msg && (
          <p className='text-[11px] text-destructive/80 bg-destructive/5 px-2 py-1 rounded-md border border-destructive/20'>
            {record.error_msg}
          </p>
        )}

        {/* Action Buttons */}
        <div className='flex flex-wrap gap-2 pt-0.5'>
          {/* Download Original Video */}
          {record.video_url && !isExpired && (
            <a
              href={record.video_url}
              download={record.file_name || 'aura_raw_video.mp4'}
              target='_blank'
              rel='noopener noreferrer'
            >
              <Button variant='outline' size='sm' className='h-7 text-xs gap-1.5'>
                <IconDownload className='size-3' />
                Download Original (AI)
              </Button>
            </a>
          )}

          {/* Download Branded Video if exported */}
          {record.branded_video_url && (
            <a
              href={record.branded_video_url}
              download={record.branded_file_name || 'aura_branded_export.mp4'}
              target='_blank'
              rel='noopener noreferrer'
            >
              <Button
                variant='outline'
                size='sm'
                className='h-7 text-xs gap-1.5 border-emerald-500/50 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 hover:bg-emerald-500/20'
              >
                <IconDownload className='size-3' />
                Download Final (Branded)
              </Button>
            </a>
          )}

          {/* Open in Brand Marker */}
          {record.video_url && !isExpired && (
            <Button
              variant='outline'
              size='sm'
              className='h-7 text-xs gap-1.5 border-primary/40 hover:border-primary hover:bg-primary/5'
              onClick={() => onOpenInBrandMarker(record.video_url!, record.prompt, record.id)}
            >
              <IconSparkles className='size-3 text-primary' />
              {record.branded_video_url ? 'Re-apply Brand Marker' : 'Open in Brand Marker'}
            </Button>
          )}

          {/* Re-generate shortcut — shown for expired AND failed entries */}
          {(isExpired || isFailed) && (
            <Button
              variant='outline'
              size='sm'
              className='h-7 text-xs gap-1.5'
              onClick={() => onRegenerate(record.prompt)}
            >
              <IconRefresh className='size-3' />
              Re-generate from prompt
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}

interface VideoHistoryProps {
  latestRecord?: VideoGenerationRecord | null;
  onOpenInBrandMarker: (url: string, prompt?: string, recordId?: string) => void;
  onRegenerate: (prompt: string) => void;
}

export function VideoHistory({
  latestRecord,
  onOpenInBrandMarker,
  onRegenerate
}: VideoHistoryProps) {
  const [records, setRecords] = useState<VideoGenerationRecord[]>(() => {
    if (typeof window !== 'undefined') {
      try {
        const saved = localStorage.getItem(LOCAL_STORAGE_KEY);
        if (saved) return JSON.parse(saved);
      } catch {
        // Safe fallback
      }
    }
    return [];
  });
  const [isLoading, setIsLoading] = useState(true);
  const [brandFilter, setBrandFilter] = useState<string>('all');
  const [refreshTick, setRefreshTick] = useState(0);

  const fetchHistory = useCallback(() => {
    setRefreshTick((n) => n + 1);
  }, []);

  // Sync to localStorage whenever records change
  const saveToLocalStorage = useCallback((items: VideoGenerationRecord[]) => {
    if (typeof window !== 'undefined') {
      try {
        localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(items.slice(0, 50)));
      } catch {
        // Quota or storage unavailable
      }
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      startTransition(() => {
        setIsLoading(true);
      });
      try {
        const data = await listVideoHistory({ limit: 50 });
        if (!cancelled && Array.isArray(data)) {
          startTransition(() => {
            setRecords((prev) => {
              // Merge server and local records by ID
              const map = new Map<string, VideoGenerationRecord>();
              data.forEach((item) => map.set(item.id, item));
              prev.forEach((item) => {
                if (!map.has(item.id)) {
                  map.set(item.id, item);
                } else {
                  // Merge local branded url if server doesn't have it
                  const existing = map.get(item.id)!;
                  if (item.branded_video_url && !existing.branded_video_url) {
                    existing.branded_video_url = item.branded_video_url;
                    existing.branded_file_name = item.branded_file_name;
                  }
                }
              });
              const merged = Array.from(map.values()).sort(
                (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
              );
              saveToLocalStorage(merged);
              return merged;
            });
            setIsLoading(false);
          });
        }
      } catch {
        if (!cancelled) {
          startTransition(() => {
            setIsLoading(false);
          });
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [refreshTick, saveToLocalStorage]);

  // Prepend latest result from current session instantly
  useEffect(() => {
    if (!latestRecord) return;
    startTransition(() => {
      setRecords((prev) => {
        const map = new Map<string, VideoGenerationRecord>();
        map.set(latestRecord.id, latestRecord);
        prev.forEach((r) => {
          if (!map.has(r.id)) map.set(r.id, r);
        });
        const updated = Array.from(map.values()).sort(
          (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
        );
        saveToLocalStorage(updated);
        return updated;
      });
    });
  }, [latestRecord, saveToLocalStorage]);

  const filtered =
    brandFilter === 'all' ? records : records.filter((r) => r.brand_id === brandFilter);

  return (
    <Card className='mt-6'>
      <CardHeader className='pb-3'>
        <div className='flex items-center justify-between gap-4 flex-wrap'>
          <div>
            <div className='flex items-center gap-2'>
              <Icons.video className='size-4 text-primary' />
              <CardTitle className='text-base font-semibold'>Generated Video History</CardTitle>
              {records.length > 0 && (
                <Badge variant='secondary' className='text-[11px]'>
                  {records.length} reel{records.length !== 1 ? 's' : ''}
                </Badge>
              )}
            </div>
            <CardDescription className='mt-0.5'>
              Access and download raw AI creations or exported branded videos — newest first.
            </CardDescription>
          </div>

          <div className='flex items-center gap-2'>
            {/* Brand Filter */}
            <div className='flex items-center gap-1.5'>
              <IconFilter className='size-3.5 text-muted-foreground' />
              <select
                value={brandFilter}
                onChange={(e) => setBrandFilter(e.target.value)}
                className='rounded-md border border-input bg-background px-2.5 py-1.5 text-xs shadow-xs focus:border-ring focus:outline-hidden'
              >
                <option value='all'>All Brands</option>
                <option value='jade'>J Jewellers</option>
                <option value='doctorshield'>Doctor Shield</option>
                <option value='jaguar'>Jagrut Trust</option>
              </select>
            </div>

            {/* Refresh */}
            <Button
              variant='outline'
              size='sm'
              onClick={fetchHistory}
              disabled={isLoading}
              className='h-8 gap-1.5 text-xs'
            >
              <IconRefresh className={`size-3.5 ${isLoading ? 'animate-spin' : ''}`} />
              Refresh
            </Button>
          </div>
        </div>
      </CardHeader>

      <CardContent className='pt-0 p-0'>
        {/* Skeleton loading */}
        {isLoading && records.length === 0 ? (
          <div className='divide-y divide-border/40'>
            <HistorySkeleton />
            <HistorySkeleton />
            <HistorySkeleton />
          </div>
        ) : filtered.length === 0 ? (
          /* Empty state */
          <div className='flex flex-col items-center justify-center py-14 text-center text-muted-foreground'>
            <Icons.video className='size-12 stroke-[1.2] mb-3 opacity-30' />
            <p className='text-sm font-medium'>
              {brandFilter !== 'all'
                ? `No videos generated for ${BRAND_LABELS[brandFilter] ?? brandFilter} yet.`
                : 'No videos generated yet.'}
            </p>
            <p className='text-xs mt-1 max-w-xs'>
              Generate your first reel using the studio above ↑ — it will appear here instantly.
            </p>
          </div>
        ) : (
          /* History rows */
          <div className='divide-y divide-border/30'>
            {filtered.map((record) => (
              <HistoryRow
                key={record.id}
                record={record}
                onOpenInBrandMarker={onOpenInBrandMarker}
                onRegenerate={onRegenerate}
              />
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
