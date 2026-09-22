'use client';

import React, { useState } from 'react';
import { useApiMode } from '@/context/api-mode-context';
import { Switch } from '@/components/ui/switch';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Popover,
  PopoverContent,
  PopoverTrigger
} from '@/components/ui/popover';
import {
  IconBolt,
  IconBroadcast,
  IconServer,
  IconActivity,
  IconCircleCheck,
  IconCircleX,
  IconLoader2,
  IconCpu,
  IconSparkles,
  IconDatabase
} from '@tabler/icons-react';
import { cn } from '@/lib/utils';

interface ApiModeToggleProps {
  variant?: 'header' | 'compact' | 'studio';
  className?: string;
}

export function ApiModeToggle({ variant = 'header', className }: ApiModeToggleProps) {
  const {
    isRealApi,
    modeInfo,
    backendStatus,
    latencyMs,
    isToggling,
    toggleApiMode,
    testConnection
  } = useApiMode();

  const [testing, setTesting] = useState(false);

  const handleTest = async () => {
    setTesting(true);
    try {
      await testConnection();
    } finally {
      setTesting(false);
    }
  };

  if (variant === 'studio') {
    return (
      <div
        className={cn(
          'flex items-center gap-3 px-3 py-1.5 rounded-lg border bg-card/70 backdrop-blur-sm transition-all',
          isRealApi
            ? 'border-emerald-500/30 shadow-sm shadow-emerald-500/5'
            : 'border-amber-500/30 shadow-sm shadow-amber-500/5',
          className
        )}
      >
        <div className='flex items-center gap-2'>
          <span className='relative flex h-2.5 w-2.5'>
            {isRealApi && backendStatus === 'connected' && (
              <span className='animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75'></span>
            )}
            <span
              className={cn(
                'relative inline-flex rounded-full h-2.5 w-2.5',
                isRealApi
                  ? backendStatus === 'connected'
                    ? 'bg-emerald-500'
                    : 'bg-rose-500'
                  : 'bg-amber-500'
              )}
            />
          </span>
          <span className='text-xs font-semibold tracking-wider uppercase text-muted-foreground'>
            Mode:
          </span>
          <span
            className={cn(
              'text-xs font-bold uppercase tracking-wider',
              isRealApi
                ? 'text-emerald-600 dark:text-emerald-400'
                : 'text-amber-600 dark:text-amber-400'
            )}
          >
            {isRealApi ? 'Real API' : 'Mock Simulator'}
          </span>
        </div>

        <div className='flex items-center gap-2 pl-2 border-l border-border/60'>
          <span className='text-[11px] text-muted-foreground hidden sm:inline'>
            Mock
          </span>
          <Switch
            checked={isRealApi}
            onCheckedChange={(checked) => toggleApiMode(checked)}
            disabled={isToggling}
            size='sm'
            aria-label='Toggle Mock vs Real API connection'
          />
          <span className='text-[11px] text-muted-foreground hidden sm:inline'>
            Real
          </span>
        </div>

        <Button
          variant='ghost'
          size='sm'
          onClick={handleTest}
          disabled={testing}
          className='h-6 px-2 text-[11px] text-muted-foreground hover:text-foreground hidden md:flex items-center gap-1'
        >
          {testing ? (
            <IconLoader2 className='size-3 animate-spin' />
          ) : (
            <IconActivity className='size-3' />
          )}
          Ping {latencyMs ? `(${latencyMs}ms)` : ''}
        </Button>
      </div>
    );
  }

  return (
    <Popover>
      <div className={cn('flex items-center gap-1.5', className)}>
        <PopoverTrigger
          className={cn(
            'group flex items-center gap-2 rounded-full border px-2.5 py-1 text-xs font-medium transition-all hover:bg-accent/60 outline-none focus-visible:ring-2 focus-visible:ring-ring cursor-pointer',
            isRealApi
              ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300'
              : 'border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-300'
          )}
        >
          <span className='relative flex h-2 w-2'>
            {isRealApi && backendStatus === 'connected' && (
              <span className='animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75'></span>
            )}
            <span
              className={cn(
                'relative inline-flex rounded-full h-2 w-2',
                isRealApi
                  ? backendStatus === 'connected'
                    ? 'bg-emerald-500'
                    : 'bg-rose-500'
                  : 'bg-amber-500'
              )}
            />
          </span>

          {isRealApi ? (
            <IconBolt className='size-3.5 text-emerald-600 dark:text-emerald-400' />
          ) : (
            <IconBroadcast className='size-3.5 text-amber-600 dark:text-amber-400' />
          )}

          <span className='font-semibold'>
            {isRealApi ? 'Real API' : 'Mock Mode'}
          </span>

          {backendStatus === 'offline' && isRealApi && (
            <span className='text-[10px] text-rose-500 font-bold'>(Offline)</span>
          )}
        </PopoverTrigger>

        <Switch
          checked={isRealApi}
          onCheckedChange={(checked) => toggleApiMode(checked)}
          disabled={isToggling}
          size='sm'
          className='data-checked:bg-emerald-600 dark:data-checked:bg-emerald-500'
          aria-label='Toggle Mock and Real API'
        />
      </div>

      <PopoverContent align='end' className='w-80 p-3 space-y-3'>
        <div className='flex items-center justify-between pb-2 border-b border-border'>
          <div className='space-y-0.5'>
            <div className='text-xs font-semibold text-foreground flex items-center gap-1.5'>
              <IconServer className='size-3.5 text-primary' />
              API Connection Manager
            </div>
            <p className='text-[11px] text-muted-foreground'>
              Switch between Real AI calls and Mock simulation
            </p>
          </div>
          <Badge
            variant={isRealApi ? 'default' : 'secondary'}
            className={cn(
              'text-[10px] uppercase font-bold tracking-wider',
              isRealApi
                ? 'bg-emerald-600 hover:bg-emerald-600 text-white'
                : 'bg-amber-600 hover:bg-amber-600 text-white'
            )}
          >
            {isRealApi ? 'Live AI' : 'Mock'}
          </Badge>
        </div>

        {/* Big On/Off switch in dropdown */}
        <div className='flex items-center justify-between p-2 rounded-md bg-muted/50 border border-border/50'>
          <div className='space-y-0.5'>
            <span className='text-xs font-medium'>API Mode</span>
            <p className='text-[11px] text-muted-foreground'>
              {isRealApi
                ? 'Groq LLM + FAL AI active'
                : 'Local mock simulation active'}
            </p>
          </div>
          <div className='flex items-center gap-2'>
            <span className='text-[11px] font-mono font-medium text-muted-foreground'>
              {isRealApi ? 'REAL' : 'MOCK'}
            </span>
            <Switch
              checked={isRealApi}
              onCheckedChange={(checked) => toggleApiMode(checked)}
              disabled={isToggling}
              className='data-checked:bg-emerald-600'
            />
          </div>
        </div>

        {/* Diagnostics Info */}
        <div className='space-y-1.5 text-xs'>
          <div className='flex items-center justify-between text-muted-foreground py-0.5'>
            <span className='flex items-center gap-1.5'>
              <IconActivity className='size-3 text-muted-foreground' /> Backend Server:
            </span>
            <span className='font-mono text-[11px] flex items-center gap-1'>
              {backendStatus === 'connected' ? (
                <>
                  <IconCircleCheck className='size-3 text-emerald-500' />
                  <span className='text-emerald-600 dark:text-emerald-400 font-semibold'>
                    Online {latencyMs ? `(${latencyMs}ms)` : ''}
                  </span>
                </>
              ) : backendStatus === 'checking' ? (
                <span className='text-muted-foreground'>Pinging...</span>
              ) : (
                <>
                  <IconCircleX className='size-3 text-rose-500' />
                  <span className='text-rose-500 font-semibold'>Offline (port 8000)</span>
                </>
              )}
            </span>
          </div>

          <div className='flex items-center justify-between text-muted-foreground py-0.5'>
            <span className='flex items-center gap-1.5'>
              <IconCpu className='size-3 text-muted-foreground' /> Groq Model:
            </span>
            <span className='font-mono text-[11px] text-foreground font-medium'>
              {modeInfo?.groq_model || 'openai/gpt-oss-20b'}
            </span>
          </div>

          <div className='flex items-center justify-between text-muted-foreground py-0.5'>
            <span className='flex items-center gap-1.5'>
              <IconSparkles className='size-3 text-muted-foreground' /> FAL Flux Model:
            </span>
            <span className='font-mono text-[11px] text-foreground font-medium truncate max-w-[130px]'>
              {modeInfo?.image_model || 'fal-ai/flux/schnell'}
            </span>
          </div>

          <div className='flex items-center justify-between text-muted-foreground py-0.5'>
            <span className='flex items-center gap-1.5'>
              <IconDatabase className='size-3 text-muted-foreground' /> Database:
            </span>
            <span className='font-mono text-[11px] text-foreground font-medium'>
              MySQL (aura)
            </span>
          </div>
        </div>

        {/* Ping Test Button */}
        <div className='pt-1'>
          <Button
            size='sm'
            variant='outline'
            onClick={handleTest}
            disabled={testing}
            className='w-full text-xs h-8 flex items-center justify-center gap-1.5'
          >
            {testing ? (
              <>
                <IconLoader2 className='size-3.5 animate-spin' />
                Testing Connection...
              </>
            ) : (
              <>
                <IconActivity className='size-3.5 text-emerald-500' />
                Test Real API Connection Now
              </>
            )}
          </Button>
        </div>
      </PopoverContent>
    </Popover>
  );
}
