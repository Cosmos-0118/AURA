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
  IconFilter
} from '@tabler/icons-react';

const BRAND_LABELS: Record<string, string> = {
  jade: 'Jade',
  doctorshield: 'DoctorShield',
  jaguar: 'Jaguar Transit'
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
  onOpenInBrandMarker: (url: string, prompt: string) => void;
  onRegenerate: (prompt: string) => void;
}

function HistoryRow({ record, onOpenInBrandMarker, onRegenerate }: HistoryRowProps) {
  const [isExpired, setIsExpired] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);
  const [isHovered, setIsHovered] = useState(false);
  const videoRef = useRef<HTMLVideoElement>(null);

  const isCompleted = record.status === 'COMPLETED' && !!record.video_url;
  const isFailed = record.status === 'FAILED';
  const isInProgress = record.status === 'IN_PROGRESS';

  const handleVideoError = () => {
    if (record.video_url) setIsExpired(true);
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
      {/* Thumbnail / Status Area */}
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
              src={record.video_url!}
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
              "
            </span>
            {promptDisplay}
            <span className='font-mono text-[11px] text-muted-foreground select-none ml-0.5'>
              "
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

        {/* Metadata chips */}
        <div className='flex flex-wrap items-center gap-1.5'>
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
          {record.file_size && (
            <Badge variant='outline' className='text-[10px] py-0 px-2 text-muted-foreground'>
              {formatBytes(record.file_size)}
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
          {isCompleted && !isExpired && record.video_url && (
            <>
              <a
                href={record.video_url}
                download={record.file_name || 'aura_reel_5s.mp4'}
                target='_blank'
                rel='noopener noreferrer'
              >
                <Button variant='outline' size='sm' className='h-7 text-xs gap-1.5'>
                  <IconDownload className='size-3' />
                  Download
                </Button>
              </a>
              <Button
                variant='outline'
                size='sm'
                className='h-7 text-xs gap-1.5 border-primary/40 hover:border-primary hover:bg-primary/5'
                onClick={() => onOpenInBrandMarker(record.video_url!, record.prompt)}
              >
                <IconSparkles className='size-3 text-primary' />
                Open in Brand Marker
              </Button>
            </>
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
  /** When a new video is generated in the current session, pass the record here to prepend it instantly. */
  latestRecord?: VideoGenerationRecord | null;
  /** Called when the user clicks "Open in Brand Marker" — parent should switch to the brand tab. */
  onOpenInBrandMarker: (url: string) => void;
  /** Called when the user clicks "Re-generate from prompt" — parent should set the prompt and trigger generation. */
  onRegenerate: (prompt: string) => void;
}

export function VideoHistory({
  latestRecord,
  onOpenInBrandMarker,
  onRegenerate
}: VideoHistoryProps) {
  const [records, setRecords] = useState<VideoGenerationRecord[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isOffline, setIsOffline] = useState(false);
  const [brandFilter, setBrandFilter] = useState<string>('all');

  const [refreshTick, setRefreshTick] = useState(0);

  const fetchHistory = useCallback(() => {
    setRefreshTick((n) => n + 1);
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      startTransition(() => {
        setIsLoading(true);
        setIsOffline(false);
      });
      try {
        const data = await listVideoHistory({ limit: 30 });
        if (!cancelled) {
          startTransition(() => {
            setRecords(data);
            setIsLoading(false);
          });
        }
      } catch {
        if (!cancelled) {
          startTransition(() => {
            setIsOffline(true);
            setRecords([]);
            setIsLoading(false);
          });
        }
      }
    })();
    return () => {
      cancelled = true;
    };
    // refreshTick is the manual refresh signal; latestRecord is excluded — handled below
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refreshTick]);

  // Prepend latest result from the current session instantly (no re-fetch)
  useEffect(() => {
    if (!latestRecord) return;
    startTransition(() => {
      setRecords((prev) => {
        if (prev.some((r) => r.id === latestRecord.id)) return prev;
        return [latestRecord, ...prev];
      });
    });
  }, [latestRecord]);

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
              All video reels generated in this studio — newest first.
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
                <option value='jade'>Jade</option>
                <option value='doctorshield'>DoctorShield</option>
                <option value='jaguar'>Jaguar Transit</option>
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
        {/* Offline / DB unavailable notice */}
        {isOffline && (
          <div className='mx-4 mb-4 flex items-center gap-2.5 rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-700 dark:text-amber-400'>
            <IconAlertTriangle className='size-4 shrink-0' />
            <span>
              History unavailable — database offline or table not yet created. Video generation
              still works normally.
            </span>
          </div>
        )}

        {/* Skeleton loading */}
        {isLoading ? (
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
                onOpenInBrandMarker={(url, _prompt) => onOpenInBrandMarker(url)}
                onRegenerate={onRegenerate}
              />
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
