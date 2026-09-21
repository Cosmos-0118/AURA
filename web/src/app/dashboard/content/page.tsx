'use client';

import React, { useState } from 'react';
import { useAuraStore } from '@/lib/demo/store';
import type { ExtendedAsset } from '@/lib/demo/assets';
import type { BrandId, Platform, AssetStatus } from '@/lib/api/types';
import {
  BrandBadge,
  ComplianceVerdictBadge,
  AssetStatusBadge
} from '@/components/aura/common';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter
} from '@/components/ui/dialog';
import { Icons } from '@/components/icons';

export default function ContentLibraryPage() {
  const store = useAuraStore();
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [brandFilter, setBrandFilter] = useState<BrandId | 'all'>('all');
  const [platformFilter, setPlatformFilter] = useState<Platform | 'all'>('all');
  const [statusFilter, setStatusFilter] = useState<AssetStatus | 'all'>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedAsset, setSelectedAsset] = useState<ExtendedAsset | null>(null);

  const filteredAssets = store.assets.filter((a) => {
    if (brandFilter !== 'all' && a.brand_id !== brandFilter) return false;
    if (platformFilter !== 'all' && a.platform !== platformFilter) return false;
    if (statusFilter !== 'all' && a.status !== statusFilter) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      return (
        a.body.toLowerCase().includes(q) ||
        (a.title && a.title.toLowerCase().includes(q)) ||
        a.hashtags.some((h) => h.toLowerCase().includes(q))
      );
    }
    return true;
  });

  return (
    <div className='flex flex-col gap-6 p-4 md:p-8 max-w-7xl mx-auto w-full'>
      {/* Header */}
      <div className='flex flex-col md:flex-row md:items-center justify-between gap-4 border-b pb-5'>
        <div>
          <div className='flex items-center gap-2 text-xs font-semibold text-muted-foreground uppercase tracking-widest'>
            <span>Digital Asset Archive</span>
            <span>•</span>
            <span className='text-primary'>Repository</span>
          </div>
          <h1 className='text-3xl font-bold tracking-tight text-foreground mt-1'>
            Content Library
          </h1>
          <p className='text-sm text-muted-foreground mt-0.5'>
            Comprehensive lifecycle archive of all generated, reviewed, and published marketing assets.
          </p>
        </div>

        <div className='flex items-center gap-2'>
          <Button
            variant={viewMode === 'grid' ? 'default' : 'outline'}
            size='xs'
            onClick={() => setViewMode('grid')}
          >
            Grid
          </Button>
          <Button
            variant={viewMode === 'list' ? 'default' : 'outline'}
            size='xs'
            onClick={() => setViewMode('list')}
          >
            List
          </Button>
        </div>
      </div>

      {/* Filter Bar */}
      <div className='flex flex-wrap items-center justify-between gap-3 bg-muted/20 p-3 rounded-lg border'>
        <div className='flex items-center gap-2 flex-1 min-w-[240px]'>
          <Icons.search className='size-4 text-muted-foreground ml-1' />
          <Input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder='Search assets by keywords, hashtags, or title...'
            className='h-8 text-xs bg-background'
          />
        </div>

        <div className='flex flex-wrap items-center gap-2'>
          {/* Brand */}
          <select
            value={brandFilter}
            onChange={(e) => setBrandFilter(e.target.value as BrandId | 'all')}
            className='h-8 rounded-md border bg-background px-2 text-xs'
          >
            <option value='all'>All Brands</option>
            <option value='jade'>Jade</option>
            <option value='doctorshield'>DoctorShield</option>
            <option value='jaguar'>Jaguar Transit</option>
          </select>

          {/* Platform */}
          <select
            value={platformFilter}
            onChange={(e) => setPlatformFilter(e.target.value as Platform | 'all')}
            className='h-8 rounded-md border bg-background px-2 text-xs'
          >
            <option value='all'>All Platforms</option>
            <option value='linkedin'>LinkedIn</option>
            <option value='instagram'>Instagram</option>
            <option value='x'>X</option>
            <option value='blog'>Blog</option>
            <option value='reel'>Reel</option>
          </select>

          {/* Status */}
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as AssetStatus | 'all')}
            className='h-8 rounded-md border bg-background px-2 text-xs'
          >
            <option value='all'>All Statuses</option>
            <option value='pending_review'>Pending Review</option>
            <option value='approved'>Approved</option>
            <option value='scheduled'>Scheduled</option>
            <option value='published'>Published</option>
            <option value='compliance_failed'>Compliance Failed</option>
            <option value='rejected'>Rejected</option>
          </select>
        </div>
      </div>

      {/* Grid or List View */}
      {viewMode === 'grid' ? (
        <div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4'>
          {filteredAssets.map((asset) => (
            <Card
              key={asset.id}
              className='shadow-xs hover:border-foreground/40 cursor-pointer transition-all flex flex-col justify-between'
              onClick={() => setSelectedAsset(asset)}
            >
              <CardHeader className='pb-2.5'>
                <div className='flex items-center justify-between gap-2'>
                  <BrandBadge brandId={asset.brand_id} />
                  <AssetStatusBadge status={asset.status} />
                </div>
                <div className='flex items-center justify-between text-[11px] text-muted-foreground mt-1'>
                  <span className='capitalize font-medium text-foreground'>
                    {asset.platform} · {asset.content_type}
                  </span>
                  <ComplianceVerdictBadge verdict={asset.compliance?.result} />
                </div>
                <CardTitle className='text-xs font-bold text-foreground mt-1 line-clamp-1'>
                  {asset.title || 'Marketing Content'}
                </CardTitle>
              </CardHeader>
              <CardContent className='flex flex-col gap-2.5 pt-0'>
                <p className='text-xs text-foreground/80 font-mono bg-muted/30 p-2.5 rounded line-clamp-3 leading-relaxed'>
                  {asset.body}
                </p>
                <div className='flex items-center justify-between pt-2 border-t text-[10px] text-muted-foreground'>
                  <span>Variant {asset.variant} · {asset.language.toUpperCase()}</span>
                  <span className='text-primary font-medium'>View History →</span>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        /* List View */
        <Card className='shadow-xs overflow-hidden'>
          <div className='overflow-x-auto'>
            <table className='w-full text-left text-xs'>
              <thead className='border-b bg-muted/30 text-muted-foreground font-medium'>
                <tr>
                  <th className='py-3 px-4 font-semibold'>Brand</th>
                  <th className='py-3 px-4 font-semibold'>Platform</th>
                  <th className='py-3 px-4 font-semibold'>Title / Hook</th>
                  <th className='py-3 px-4 font-semibold'>Compliance</th>
                  <th className='py-3 px-4 font-semibold'>Status</th>
                  <th className='py-3 px-4 font-semibold text-right'>Actions</th>
                </tr>
              </thead>
              <tbody className='divide-y'>
                {filteredAssets.map((asset) => (
                  <tr
                    key={asset.id}
                    className='hover:bg-muted/40 transition-colors cursor-pointer'
                    onClick={() => setSelectedAsset(asset)}
                  >
                    <td className='py-3 px-4'>
                      <BrandBadge brandId={asset.brand_id} />
                    </td>
                    <td className='py-3 px-4 capitalize text-muted-foreground'>
                      {asset.platform}
                    </td>
                    <td className='py-3 px-4 font-medium text-foreground max-w-xs truncate'>
                      {asset.title || asset.body.slice(0, 45)}
                    </td>
                    <td className='py-3 px-4'>
                      <ComplianceVerdictBadge verdict={asset.compliance?.result} />
                    </td>
                    <td className='py-3 px-4'>
                      <AssetStatusBadge status={asset.status} />
                    </td>
                    <td className='py-3 px-4 text-right'>
                      <Button size='xs' variant='ghost'>
                        Inspect →
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* ASSET INSPECTOR & LIFECYCLE MODAL */}
      {selectedAsset && (
        <Dialog open={Boolean(selectedAsset)} onOpenChange={(open) => !open && setSelectedAsset(null)}>
          <DialogContent className='max-w-2xl max-h-[90vh] overflow-y-auto p-6'>
            <DialogHeader className='border-b pb-4'>
              <div className='flex items-center justify-between gap-3'>
                <div className='flex items-center gap-2'>
                  <BrandBadge brandId={selectedAsset.brand_id} />
                  <span className='text-xs text-muted-foreground capitalize'>
                    {selectedAsset.platform} · {selectedAsset.content_type}
                  </span>
                </div>
                <AssetStatusBadge status={selectedAsset.status} />
              </div>

              <DialogTitle className='text-base font-bold text-foreground mt-2'>
                {selectedAsset.title || 'Marketing Content Asset'}
              </DialogTitle>
              <DialogDescription className='text-xs'>
                Asset ID: {selectedAsset.id} · Language: {selectedAsset.language.toUpperCase()}
              </DialogDescription>
            </DialogHeader>

            <div className='flex flex-col gap-4 my-2 text-xs'>
              {/* Full copy */}
              <div>
                <Label className='text-xs font-bold text-foreground mb-1.5 block'>
                  Full Asset Copy
                </Label>
                <div className='rounded-lg border bg-muted/20 p-4 font-mono text-xs whitespace-pre-wrap leading-relaxed max-h-60 overflow-y-auto'>
                  {selectedAsset.body}
                </div>
              </div>

              {/* Hashtags */}
              {selectedAsset.hashtags?.length > 0 && (
                <div className='flex flex-wrap gap-1'>
                  {selectedAsset.hashtags.map((h) => (
                    <span key={h} className='text-[11px] text-primary font-medium'>
                      {h}
                    </span>
                  ))}
                </div>
              )}

              {/* Lifecycle & History Timeline */}
              <div className='rounded-lg border bg-card p-3.5 flex flex-col gap-2.5'>
                <Label className='text-xs font-bold text-foreground flex items-center gap-1.5'>
                  <Icons.clock className='size-3.5 text-primary' /> Lifecycle History
                </Label>

                <div className='flex flex-col gap-2 text-xs'>
                  <div className='flex items-start gap-2.5'>
                    <span className='h-2 w-2 rounded-full bg-primary mt-1.5 shrink-0' />
                    <div>
                      <div className='font-semibold text-foreground'>
                        Created via Content Agent
                      </div>
                      <div className='text-[10px] text-muted-foreground'>
                        {new Date(selectedAsset.created_at).toLocaleString()}
                      </div>
                    </div>
                  </div>

                  {selectedAsset.history?.map((h, i) => (
                    <div key={i} className='flex items-start gap-2.5'>
                      <span className='h-2 w-2 rounded-full bg-emerald-500 mt-1.5 shrink-0' />
                      <div>
                        <div className='font-semibold text-foreground'>{h.action}</div>
                        <div className='text-[10px] text-muted-foreground'>
                          {new Date(h.timestamp).toLocaleString()} · {h.actor}
                        </div>
                        {h.note && (
                          <div className='text-[11px] text-muted-foreground italic mt-0.5'>
                            Note: "{h.note}"
                          </div>
                        )}
                      </div>
                    </div>
                  ))}

                  {selectedAsset.published_post_id && (
                    <div className='flex items-start gap-2.5'>
                      <span className='h-2 w-2 rounded-full bg-emerald-600 mt-1.5 shrink-0' />
                      <div>
                        <div className='font-semibold text-emerald-600 dark:text-emerald-400'>
                          Published to Live Network
                        </div>
                        <div className='text-[10px] text-muted-foreground'>
                          Post ID: <code>{selectedAsset.published_post_id}</code>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>

            <DialogFooter className='border-t pt-4'>
              <Button size='sm' onClick={() => setSelectedAsset(null)}>
                Close
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
}
