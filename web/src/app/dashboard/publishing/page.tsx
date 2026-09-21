'use client';

import React, { useState } from 'react';
import { toast } from 'sonner';
import { useAuraStore, auraStore } from '@/lib/demo/store';
import { DEMO_ENGAGEMENT_ANALYTICS, PUBLISH_STEPS } from '@/lib/demo/publishing';
import type { ExtendedAsset } from '@/lib/demo/assets';
import { BrandBadge, AssetStatusBadge } from '@/components/aura/common';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter
} from '@/components/ui/dialog';
import { Icons } from '@/components/icons';

function handleScheduleAsset(asset: ExtendedAsset) {
  auraStore.publishAsset(asset.id, 'schedule');
  toast.success('Scheduled asset for tomorrow 10:30 AM');
}

export default function PublishingPage() {
  const store = useAuraStore();
  const [activeTab, setActiveTab] = useState<string>('approved');
  const [publishingAsset, setPublishingAsset] = useState<ExtendedAsset | null>(null);
  const [publishStep, setPublishStep] = useState<number>(0);
  const [isPublishing, setIsPublishing] = useState<boolean>(false);
  const [publishedPostId, setPublishedPostId] = useState<string | null>(null);

  const approvedAssets = store.assets.filter((a) => a.status === 'approved');
  const scheduledAssets = store.assets.filter((a) => a.status === 'scheduled');
  const publishedAssets = store.assets.filter((a) => a.status === 'published');

  const filteredAssets =
    activeTab === 'approved'
      ? approvedAssets
      : activeTab === 'scheduled'
      ? scheduledAssets
      : activeTab === 'published'
      ? publishedAssets
      : [];

  const handleStartSimulatedPublish = async (asset: ExtendedAsset) => {
    setPublishingAsset(asset);
    setIsPublishing(true);
    setPublishedPostId(null);
    setPublishStep(0);

    for (let i = 0; i < PUBLISH_STEPS.length; i++) {
      setPublishStep(i);
      await new Promise((res) => setTimeout(res, PUBLISH_STEPS[i].delayMs));
    }

    const newPostId = `demo_ja_${Math.floor(10000 + Math.random() * 90000)}`;
    setPublishedPostId(newPostId);
    setIsPublishing(false);

    auraStore.publishAsset(asset.id, 'now');
    toast.success(`Published successfully! Network Post ID: ${newPostId}`);
  };

  return (
    <div className='flex flex-col gap-6 p-4 md:p-8 max-w-7xl mx-auto w-full'>
      {/* Header */}
      <div className='flex flex-col md:flex-row md:items-center justify-between gap-4 border-b pb-5'>
        <div>
          <div className='flex items-center gap-2 text-xs font-semibold text-muted-foreground uppercase tracking-widest'>
            <span>Project 2: The Hands</span>
            <span>•</span>
            <span className='text-primary'>Automated Distribution</span>
          </div>
          <h1 className='text-3xl font-bold tracking-tight text-foreground mt-1'>
            Publishing Desk
          </h1>
          <p className='text-sm text-muted-foreground mt-0.5'>
            Approved Content Queue · Dispatched to live social channels via verified API connectors.
          </p>
        </div>

        <div className='flex items-center gap-2'>
          <Badge variant='outline' className='text-xs text-emerald-600 dark:text-emerald-400 border-emerald-500/30'>
            Simulated Publisher: Connected
          </Badge>
        </div>
      </div>

      {/* Tabs */}
      <div className='flex items-center justify-between'>
        <Tabs value={activeTab} onValueChange={setActiveTab} className='w-full max-w-md'>
          <TabsList className='grid grid-cols-3 h-9'>
            <TabsTrigger value='approved' className='text-xs'>
              Approved ({approvedAssets.length})
            </TabsTrigger>
            <TabsTrigger value='scheduled' className='text-xs'>
              Scheduled ({scheduledAssets.length})
            </TabsTrigger>
            <TabsTrigger value='published' className='text-xs'>
              Published ({publishedAssets.length})
            </TabsTrigger>
          </TabsList>
        </Tabs>
      </div>

      {/* Asset Queue Cards */}
      {filteredAssets.length === 0 ? (
        <Card className='border-dashed p-10 text-center'>
          <div className='h-10 w-10 rounded-full bg-muted flex items-center justify-center mx-auto text-muted-foreground mb-2'>
            <Icons.send className='size-5' />
          </div>
          <h4 className='text-sm font-bold text-foreground'>Queue is empty</h4>
          <p className='text-xs text-muted-foreground mt-1'>
            {activeTab === 'approved'
              ? 'No approved assets waiting for dispatch. Approve content in the Review Queue.'
              : 'No assets in this status.'}
          </p>
        </Card>
      ) : (
        <div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4'>
          {filteredAssets.map((asset) => (
            <Card key={asset.id} className='shadow-xs flex flex-col justify-between'>
              <CardHeader className='pb-3'>
                <div className='flex items-center justify-between'>
                  <BrandBadge brandId={asset.brand_id} />
                  <AssetStatusBadge status={asset.status} />
                </div>
                <div className='flex items-center justify-between text-[11px] text-muted-foreground mt-1'>
                  <span className='capitalize font-semibold text-foreground'>
                    {asset.platform} · {asset.content_type}
                  </span>
                  <span>{asset.scheduled_for || (asset.published_at ? 'Live' : 'Ready')}</span>
                </div>
                <CardTitle className='text-xs font-bold text-foreground mt-1 line-clamp-1'>
                  {asset.title || 'Approved Marketing Post'}
                </CardTitle>
              </CardHeader>
              <CardContent className='flex flex-col gap-3 pt-0'>
                <p className='text-xs text-foreground/90 font-mono bg-muted/30 p-2.5 rounded line-clamp-3 leading-relaxed'>
                  {asset.body}
                </p>

                <div className='text-[11px] text-muted-foreground'>
                  Approved by:{' '}
                  <strong className='text-foreground'>{asset.approved_by || 'Marcus Chen'}</strong>
                </div>

                {asset.published_post_id && (
                  <div className='rounded-md border bg-emerald-500/10 p-2 text-[11px] text-emerald-800 dark:text-emerald-300 font-mono'>
                    Post ID: {asset.published_post_id} (Simulated)
                  </div>
                )}

                <div className='flex items-center justify-between pt-2 border-t gap-2'>
                  {asset.status === 'approved' ? (
                    <>
                      <Button
                        size='xs'
                        variant='outline'
                        onClick={() => handleScheduleAsset(asset)}
                      >
                        <Icons.clock className='size-3 mr-1' />
                        Schedule
                      </Button>
                      <Button
                        size='xs'
                        onClick={() => handleStartSimulatedPublish(asset)}
                      >
                        <Icons.send className='size-3 mr-1' />
                        Publish Now
                      </Button>
                    </>
                  ) : asset.status === 'scheduled' ? (
                    <Button
                      size='xs'
                      onClick={() => handleStartSimulatedPublish(asset)}
                      className='w-full'
                    >
                      <Icons.send className='size-3 mr-1' />
                      Publish Now
                    </Button>
                  ) : (
                    <span className='text-[11px] text-emerald-600 dark:text-emerald-400 font-medium'>
                      ✓ Live on {asset.platform}
                    </span>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Engagement Analytics Section */}
      <div className='flex flex-col gap-4 pt-4 border-t'>
        <div>
          <h2 className='text-base font-bold text-foreground'>Published Content Performance</h2>
          <p className='text-xs text-muted-foreground'>
            Live engagement telemetry fed back into Content Agent generative tuning.
          </p>
        </div>

        <div className='grid grid-cols-1 md:grid-cols-3 gap-4'>
          {DEMO_ENGAGEMENT_ANALYTICS.map((item) => (
            <Card key={item.platform} className='shadow-xs'>
              <CardHeader className='pb-2'>
                <CardTitle className='text-sm font-bold text-foreground'>
                  {item.platform}
                </CardTitle>
              </CardHeader>
              <CardContent className='flex flex-col gap-2 text-xs'>
                <div className='flex items-center justify-between'>
                  <span className='text-muted-foreground'>Reach / Impressions:</span>
                  <strong className='text-foreground'>{item.reach}</strong>
                </div>
                <div className='flex items-center justify-between'>
                  <span className='text-muted-foreground'>Engagement Rate:</span>
                  <strong className='text-emerald-600 dark:text-emerald-400'>
                    {item.engagement}
                  </strong>
                </div>
                {item.clicks && (
                  <div className='flex items-center justify-between'>
                    <span className='text-muted-foreground'>Link Clicks / CTR:</span>
                    <strong className='text-foreground'>{item.clicks}</strong>
                  </div>
                )}
                <div className='border-t pt-2 text-[11px] text-muted-foreground truncate'>
                  Top Post: "{item.topPost}"
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Feedback loop explanation card */}
        <div className='rounded-lg border border-primary/20 bg-primary/5 p-3.5 text-xs text-foreground flex items-center justify-between gap-4'>
          <div className='flex items-center gap-3'>
            <div className='h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center text-primary shrink-0'>
              <Icons.sparkles className='size-4' />
            </div>
            <div>
              <strong className='text-primary block font-bold'>
                Analytics → Content Agent Closed Feedback Loop
              </strong>
              <span className='text-muted-foreground text-[11px]'>
                High-engagement hooks and low-friction formats are automatically indexed by the Learning Agent to weight future campaign generation.
              </span>
            </div>
          </div>
          <Badge variant='outline' className='text-xs shrink-0'>
            Loop Active
          </Badge>
        </div>
      </div>

      {/* SIMULATED PUBLISHING MODAL */}
      {publishingAsset && (
        <Dialog open={Boolean(publishingAsset)} onOpenChange={(open) => !open && setPublishingAsset(null)}>
          <DialogContent className='max-w-md p-6'>
            <DialogHeader>
              <DialogTitle className='text-base font-bold text-foreground'>
                {isPublishing ? 'Publishing Asset...' : 'Asset Published Successfully'}
              </DialogTitle>
              <DialogDescription className='text-xs'>
                Project 2 (The Hands) automated distribution endpoint.
              </DialogDescription>
            </DialogHeader>

            <div className='flex flex-col gap-3 my-3 text-xs'>
              {PUBLISH_STEPS.map((step, idx) => {
                const isDone = idx < publishStep || !isPublishing;
                const isCurrent = idx === publishStep && isPublishing;
                return (
                  <div
                    key={step.label}
                    className={`flex items-center gap-3 p-2 rounded-md ${
                      isCurrent
                        ? 'bg-primary/10 text-primary font-semibold'
                        : isDone
                        ? 'text-foreground'
                        : 'text-muted-foreground/40'
                    }`}
                  >
                    {isDone ? (
                      <Icons.circleCheck className='size-4 text-emerald-600 dark:text-emerald-400 shrink-0' />
                    ) : isCurrent ? (
                      <Icons.spinner className='size-4 animate-spin text-primary shrink-0' />
                    ) : (
                      <span className='size-4 rounded-full border flex items-center justify-center text-[10px] text-muted-foreground shrink-0'>
                        {idx + 1}
                      </span>
                    )}
                    <span>{step.label}</span>
                  </div>
                );
              })}

              {!isPublishing && publishedPostId && (
                <div className='rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-3 mt-2 flex flex-col gap-1 text-xs'>
                  <span className='font-bold text-emerald-800 dark:text-emerald-300'>
                    ✓ Verified Delivery Receipt
                  </span>
                  <span className='font-mono text-muted-foreground text-[11px]'>
                    Network Post ID: {publishedPostId}
                  </span>
                  <span className='text-[10px] text-muted-foreground mt-1'>
                    Status updated to PUBLISHED in AURA central registry.
                  </span>
                </div>
              )}
            </div>

            <DialogFooter>
              <Button
                size='sm'
                disabled={isPublishing}
                onClick={() => setPublishingAsset(null)}
              >
                Close
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
}
