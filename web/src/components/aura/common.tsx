'use client';

import React from 'react';
import type { BrandId, Platform, AssetStatus, ComplianceVerdict, Risk } from '@/lib/api/types';
import { Badge } from '@/components/ui/badge';
import { Icons } from '@/components/icons';
import { cn } from '@/lib/utils';

export function BrandBadge({ brandId, className }: { brandId: BrandId; className?: string }) {
  const configs: Record<BrandId, { label: string; className: string; border: string }> = {
    jade: {
      label: 'Jade',
      className: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/20',
      border: 'border-emerald-500'
    },
    doctorshield: {
      label: 'DoctorShield',
      className: 'bg-sky-500/10 text-sky-700 dark:text-sky-400 border-sky-500/20',
      border: 'border-sky-500'
    },
    jaguar: {
      label: 'Jaguar Transit',
      className: 'bg-amber-500/10 text-amber-700 dark:text-amber-400 border-amber-500/20',
      border: 'border-amber-500'
    }
  };

  const config = configs[brandId] || configs.jade;

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-semibold uppercase tracking-wider',
        config.className,
        className
      )}
    >
      <span className='h-1.5 w-1.5 rounded-full bg-current' />
      {config.label}
    </span>
  );
}

export function ComplianceVerdictBadge({
  verdict,
  risk,
  className
}: {
  verdict?: ComplianceVerdict | null;
  risk?: Risk | null;
  className?: string;
}) {
  if (!verdict) return null;

  if (verdict === 'PASS') {
    return (
      <Badge
        variant='outline'
        className={cn(
          'border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 text-xs font-medium gap-1',
          className
        )}
      >
        <Icons.circleCheck className='size-3.5' />
        PASS {risk ? `· ${risk} Risk` : ''}
      </Badge>
    );
  }

  if (verdict === 'REVIEW') {
    return (
      <Badge
        variant='outline'
        className={cn(
          'border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-400 text-xs font-medium gap-1',
          className
        )}
      >
        <Icons.warning className='size-3.5' />
        REVIEW REQUIRED {risk ? `· ${risk}` : ''}
      </Badge>
    );
  }

  return (
    <Badge
      variant='outline'
      className={cn(
        'border-destructive/40 bg-destructive/10 text-destructive text-xs font-medium gap-1 animate-pulse',
        className
      )}
    >
      <Icons.circleX className='size-3.5' />
      FAILED {risk ? `· ${risk} Risk` : ''}
    </Badge>
  );
}

export function AssetStatusBadge({ status }: { status: AssetStatus }) {
  const configs: Record<AssetStatus, { label: string; className: string }> = {
    draft: { label: 'Draft', className: 'bg-muted text-muted-foreground' },
    pending_review: {
      label: 'Awaiting Review',
      className: 'bg-amber-500/10 text-amber-700 dark:text-amber-400 border-amber-500/20'
    },
    compliance_failed: {
      label: 'Compliance Failed',
      className: 'bg-destructive/10 text-destructive border-destructive/20 font-semibold'
    },
    approved: {
      label: 'Approved',
      className: 'bg-blue-500/10 text-blue-700 dark:text-blue-400 border-blue-500/20'
    },
    rejected: {
      label: 'Rejected',
      className: 'bg-zinc-500/10 text-zinc-600 dark:text-zinc-400 border-zinc-500/20'
    },
    scheduled: {
      label: 'Scheduled',
      className: 'bg-purple-500/10 text-purple-700 dark:text-purple-400 border-purple-500/20'
    },
    published: {
      label: 'Published',
      className: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/20 font-semibold'
    }
  };

  const config = configs[status] || configs.draft;

  return (
    <Badge variant='outline' className={cn('text-xs font-medium', config.className)}>
      {config.label}
    </Badge>
  );
}

export function PlatformTag({ platform }: { platform: Platform }) {
  const configs: Record<Platform, { label: string; icon: string }> = {
    linkedin: { label: 'LinkedIn', icon: 'post' },
    instagram: { label: 'Instagram', icon: 'media' },
    x: { label: 'X (Twitter)', icon: 'twitter' },
    blog: { label: 'Blog / Article', icon: 'page' },
    reel: { label: 'Reel / Script', icon: 'video' }
  };

  const config = configs[platform] || { label: platform, icon: 'post' };

  return (
    <span className='inline-flex items-center gap-1.5 text-xs text-muted-foreground font-medium'>
      <span>{config.label}</span>
    </span>
  );
}

export function AuraPipelineLifecycle() {
  const stages = [
    { label: 'Research', desc: 'Competitors & Trends' },
    { label: 'Generate', desc: 'Multi-variant AI' },
    { label: 'Localise', desc: 'Cultural context' },
    { label: 'Check Compliance', desc: '12-rule engine' },
    { label: 'Human Review', desc: 'Editorial inspection', highlight: true },
    { label: 'Approve', desc: 'Publishing lock' },
    { label: 'Learn', desc: 'Feedback memory', highlight: true },
    { label: 'Publish', desc: 'Project 2 Delivery' }
  ];

  return (
    <div className='w-full overflow-x-auto rounded-xl border bg-card/60 p-3 shadow-xs'>
      <div className='flex items-center justify-between min-w-[700px] gap-2'>
        {stages.map((stage, idx) => (
          <React.Fragment key={stage.label}>
            <div
              className={cn(
                'flex flex-col items-center rounded-lg px-2.5 py-1.5 text-center transition-colors',
                stage.highlight
                  ? 'bg-primary/10 border border-primary/20 text-primary font-medium'
                  : 'text-muted-foreground'
              )}
            >
              <span className='text-xs font-semibold tracking-tight text-foreground'>
                {stage.label}
              </span>
              <span className='text-[10px] text-muted-foreground mt-0.5'>{stage.desc}</span>
            </div>
            {idx < stages.length - 1 && (
              <Icons.chevronRight className='size-3.5 shrink-0 text-muted-foreground/40' />
            )}
          </React.Fragment>
        ))}
      </div>
    </div>
  );
}
