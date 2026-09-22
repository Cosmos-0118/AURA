'use client';

import React, { useState, useEffect, useRef } from 'react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Icons } from '@/components/icons';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';

export default function CompetitorIntelligencePage() {
  const [serviceUrl, setServiceUrl] = useState('http://localhost:8787');
  const [isOnline, setIsOnline] = useState<boolean | null>(null);
  const [isChecking, setIsChecking] = useState(true);
  const iframeRef = useRef<HTMLIFrameElement>(null);

  useEffect(() => {
    const configuredUrl = process.env.NEXT_PUBLIC_COMPETITOR_INTEL_URL || 'http://localhost:8787';
    setServiceUrl(configuredUrl);

    let isMounted = true;
    const checkHealth = async () => {
      setIsChecking(true);
      try {
        const res = await fetch(`${configuredUrl}/api/health`, {
          method: 'GET',
          mode: 'cors'
        });
        if (isMounted) {
          setIsOnline(res.ok);
        }
      } catch {
        if (isMounted) {
          setIsOnline(false);
        }
      } finally {
        if (isMounted) {
          setIsChecking(false);
        }
      }
    };

    checkHealth();
    const interval = setInterval(checkHealth, 15000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  const handleRefreshIframe = () => {
    if (iframeRef.current) {
      iframeRef.current.src = serviceUrl;
    }
  };

  return (
    <div className='flex flex-col gap-4 p-4 md:p-6 w-full max-w-[1600px] mx-auto min-h-[calc(100vh-4rem)]'>
      {/* Minimum AURA Integration Header */}
      <div className='flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b pb-3.5'>
        <div>
          <div className='flex items-center gap-2'>
            <h1 className='text-xl font-bold tracking-tight text-foreground'>
              Competitor Intelligence
            </h1>
            <Badge
              variant='outline'
              className={`text-[10px] font-mono py-0 ${
                isOnline
                  ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-600'
                  : 'border-amber-500/30 bg-amber-500/10 text-amber-600'
              }`}
            >
              {isChecking ? 'Checking...' : isOnline ? 'Service Active (Port 8787)' : 'Offline / Standalone'}
            </Badge>
          </div>
          <p className='text-xs text-muted-foreground mt-0.5'>
            Monitor competitors, track changes, and surface actionable intelligence.
          </p>
        </div>

        <div className='flex items-center gap-2'>
          <Button
            size='xs'
            variant='outline'
            onClick={handleRefreshIframe}
            className='text-xs h-8 gap-1.5'
          >
            <Icons.spinner className='size-3.5' />
            <span>Reload Module</span>
          </Button>

          <Button
            size='xs'
            variant='default'
            onClick={() => window.open(serviceUrl, '_blank')}
            className='text-xs h-8 gap-1.5'
          >
            <span>Open in New Tab</span>
            <Icons.externalLink className='size-3.5' />
          </Button>
        </div>
      </div>

      {/* Offline Notice (shown only if server is not responding) */}
      {isOnline === false && (
        <Card className='border-amber-500/30 bg-amber-500/5 shadow-xs'>
          <CardHeader className='pb-2'>
            <div className='flex items-center gap-2'>
              <Icons.warning className='size-4 text-amber-600 dark:text-amber-400' />
              <CardTitle className='text-sm font-bold text-foreground'>
                Competitor Intelligence Module Not Detected on Port 8787
              </CardTitle>
            </div>
            <CardDescription className='text-xs'>
              The competitor intelligence engine runs on its dedicated port (8787) alongside changedetection (5001).
            </CardDescription>
          </CardHeader>
          <CardContent className='text-xs space-y-2'>
            <p className='text-muted-foreground'>
              To start the service in a separate terminal:
            </p>
            <div className='bg-muted/80 p-2.5 rounded-lg font-mono text-[11px] text-foreground space-y-1'>
              <div className='text-muted-foreground'># Fast local Python server:</div>
              <div className='text-primary font-bold'>python -m competitor_intelligence</div>
              <div className='text-muted-foreground mt-1.5'># Or full stack with changedetection.io:</div>
              <div className='text-primary font-bold'>cd competitor-intelligence && ./run.sh</div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Embedded Existing Competitor Intelligence Module */}
      <div className='flex-1 w-full rounded-xl overflow-hidden border bg-card shadow-xs min-h-[680px]'>
        <iframe
          ref={iframeRef}
          src={serviceUrl}
          title='JA Assure Competitor Intelligence'
          className='w-full h-full min-h-[680px] border-0'
          allow='clipboard-read; clipboard-write'
        />
      </div>
    </div>
  );
}
