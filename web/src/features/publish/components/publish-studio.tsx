'use client';

import Image from 'next/image';
import { useEffect, useState } from 'react';
import { Icons } from '@/components/icons';
import PageContainer from '@/components/layout/page-container';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { listAssets, listBufferChannels, publishToBuffer } from '@/lib/api/client';
import type { Asset, BufferChannel, BufferPublishResult } from '@/lib/api/types';

const SOCIAL_CARDS = [
  {
    service: 'instagram',
    label: 'Instagram',
    subtitle: 'Posts and reels',
    icon: '/social/instagram.jpg',
  },
  {
    service: 'linkedin',
    label: 'LinkedIn',
    subtitle: 'Professional posts',
    icon: '/social/linkedin.png',
  },
  {
    service: 'twitter',
    label: 'X / Twitter',
    subtitle: 'Short updates',
    icon: '/social/twitter.jpg',
  },
] as const;

function isVideo(url: string) {
  return /\.(mp4|mov|webm|m4v)(\?|$)/i.test(url);
}

function captionFor(asset: Asset) {
  const tags = asset.hashtags.filter(Boolean).map((tag) => (tag.startsWith('#') ? tag : `#${tag}`));
  return [asset.body.trim(), tags.join(' ')].filter(Boolean).join('\n\n');
}

function assetForChannel(assets: Asset[], channel: BufferChannel | undefined) {
  const approved = assets.filter((asset) => asset.status === 'approved');
  const pool = approved.length > 0 ? approved : assets;
  if (channel?.service === 'instagram') {
    return (
      pool.find((asset) => asset.platform === 'instagram' || asset.platform === 'reel') ?? pool[0]
    );
  }
  if (channel?.service === 'linkedin') {
    return pool.find((asset) => asset.platform === 'linkedin') ?? pool[0];
  }
  return pool[0];
}

export default function PublishStudio() {
  const [channels, setChannels] = useState<BufferChannel[]>([]);
  const [channelId, setChannelId] = useState('');
  const [assets, setAssets] = useState<Asset[]>([]);
  const [publishing, setPublishing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<BufferPublishResult | null>(null);

  useEffect(() => {
    listBufferChannels()
      .then((data) => {
        setChannels(data.channels);
        setChannelId(data.channels[0]?.id ?? '');
      })
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : 'Could not load channels.');
      });
    listAssets({ status: 'approved' })
      .then((rows) => setAssets(Array.isArray(rows) ? rows : []))
      .catch(() => {
        listAssets()
          .then((rows) => setAssets(Array.isArray(rows) ? rows : []))
          .catch(() => setAssets([]));
      });
  }, []);

  const handlePost = async () => {
    const channel = channels.find((item) => item.id === channelId);
    const asset = assetForChannel(assets, channel);
    if (!channel || !asset || publishing) {
      setError('Approve a campaign draft first, then choose a channel.');
      return;
    }

    const media = asset.media_url?.trim() || '';
    const video = media && isVideo(media);
    setPublishing(true);
    setError(null);
    setResult(null);
    try {
      const response = await publishToBuffer({
        channel_id: channel.id,
        text: captionFor(asset),
        mode: 'shareNow',
        image_url: media && !video ? media : null,
        video_url: video ? media : null,
        instagram_type:
          channel.service === 'instagram' ? (video ? 'reel' : 'post') : null,
      });
      setResult(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Post failed.');
    } finally {
      setPublishing(false);
    }
  };

  const channelByService = (service: string) => channels.find((item) => item.service === service);
  const selectedChannel = channels.find((item) => item.id === channelId);

  return (
    <PageContainer>
      <div className='flex flex-1 flex-col space-y-6 pb-12'>
        <div className='flex flex-col justify-between gap-4 md:flex-row md:items-center'>
          <div>
            <div className='flex items-center gap-2'>
              <h1 className='text-3xl font-bold tracking-tight'>Publish</h1>
              <Badge variant='outline' className='border-primary/40 bg-primary/10 text-primary'>
                Buffer
              </Badge>
            </div>
            <p className='mt-1 text-sm text-muted-foreground'>
              Publish approved campaign content to the connected social channel.
            </p>
          </div>
          <Badge variant='secondary' className='flex w-fit items-center gap-1.5 px-3 py-1'>
            <Icons.check className='size-3.5 text-emerald-500' />
            Human reviewed content only
          </Badge>
        </div>

        <Card>
          <CardHeader className='pb-3'>
            <CardTitle className='text-base font-semibold'>Select channel</CardTitle>
            <CardDescription>
              Choose one connected Buffer channel. The caption and media come from the approved
              campaign asset.
            </CardDescription>
          </CardHeader>
          <CardContent className='space-y-5'>
            <div className='grid gap-3 sm:grid-cols-3'>
              {SOCIAL_CARDS.map((card) => {
                const channel = channelByService(card.service);
                const active = channel?.id === channelId;
                return (
                  <button
                    key={card.service}
                    type='button'
                    onClick={() => channel && setChannelId(channel.id)}
                    disabled={!channel || publishing}
                    className={[
                      'group rounded-xl border bg-card p-4 text-left ring-1 ring-transparent transition-all',
                      active
                        ? 'border-primary bg-primary/5 shadow-xs ring-primary/20'
                        : 'border-border hover:bg-muted/40 hover:shadow-xs',
                      !channel ? 'cursor-not-allowed opacity-55' : '',
                    ].join(' ')}
                  >
                    <div className='mb-4 flex items-center justify-between gap-3'>
                      <div className='size-12 overflow-hidden rounded-xl shadow-xs ring-1 ring-foreground/10'>
                        <Image
                          src={card.icon}
                          alt={`${card.label} logo`}
                          width={48}
                          height={48}
                          className='size-full object-cover'
                        />
                      </div>
                      {active && <Icons.check className='size-4 text-primary' />}
                    </div>
                    <div className='flex items-center justify-between gap-2'>
                      <h3 className='font-medium'>{card.label}</h3>
                      {active && <Badge variant='secondary'>Selected</Badge>}
                    </div>
                    <p className='mt-1 text-xs text-muted-foreground'>{card.subtitle}</p>
                    <p className='mt-4 truncate text-xs font-medium'>
                      {channel ? channel.display_name || channel.name : 'Connect in Buffer'}
                    </p>
                  </button>
                );
              })}
            </div>

            {error && <p className='text-sm text-destructive'>{error}</p>}
            {result && (
              <p className='flex items-center gap-1.5 text-sm text-emerald-600'>
                <Icons.check className='size-4' />
                {result.message}
              </p>
            )}
          </CardContent>
          <CardFooter className='justify-between gap-3'>
            <div className='text-xs text-muted-foreground'>
              {selectedChannel
                ? `Ready for ${selectedChannel.display_name || selectedChannel.name}`
                : 'Connect a channel in Buffer to publish.'}
            </div>
            <Button
              type='button'
              onClick={() => void handlePost()}
              disabled={publishing || !selectedChannel}
            >
              <Icons.send className='size-4' />
              {publishing ? 'Posting...' : 'Post'}
            </Button>
          </CardFooter>
        </Card>
      </div>
    </PageContainer>
  );
}
