'use client';

import React, { useState } from 'react';
import { useAuraStore } from '@/lib/demo/store';
import { REJECTION_REASONS_DATA, LEARNING_TREND_DATA } from '@/lib/demo/metrics';
import type { BrandId } from '@/lib/api/types';
import { BrandBadge } from '@/components/aura/common';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Progress } from '@/components/ui/progress';
import { Icons } from '@/components/icons';

export default function InsightsPage() {
  const store = useAuraStore();
  const [searchQuery, setSearchQuery] = useState('');
  const [brandFilter, setBrandFilter] = useState<BrandId | 'all'>('all');

  const filteredLessons = store.lessons.filter((l) => {
    if (brandFilter !== 'all' && l.brand_id !== brandFilter) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      return (
        l.note.toLowerCase().includes(q) ||
        l.title.toLowerCase().includes(q) ||
        l.reason_tag.toLowerCase().includes(q)
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
            <span>Feedback Learning Loop</span>
            <span>•</span>
            <span className='text-primary'>Core Differentiator</span>
          </div>
          <h1 className='text-3xl font-bold tracking-tight text-foreground mt-1'>
            Learning & Insights
          </h1>
          <p className='text-sm text-muted-foreground mt-0.5'>
            AURA gets better from every human decision. Editorial corrections become generative prompt memory.
          </p>
        </div>

        <Badge variant='outline' className='text-xs text-primary border-primary/30 py-1 px-2.5'>
          Closed-Loop Memory: Active
        </Badge>
      </div>

      {/* Top Closed-Loop KPIs */}
      <div className='grid grid-cols-2 md:grid-cols-4 gap-4'>
        <Card className='shadow-xs border-primary/20 bg-primary/[0.02]'>
          <CardHeader className='pb-2'>
            <CardTitle className='text-xs font-medium text-muted-foreground'>
              Lessons Learned
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className='text-2xl font-bold text-primary'>{store.lessons.length}</div>
            <p className='text-[11px] text-muted-foreground mt-0.5'>In active generator context</p>
          </CardContent>
        </Card>

        <Card className='shadow-xs'>
          <CardHeader className='pb-2'>
            <CardTitle className='text-xs font-medium text-muted-foreground'>
              Rejection Rate
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className='text-2xl font-bold text-foreground'>{store.metrics.rejectionRate}%</div>
            <p className='text-[11px] text-emerald-600 dark:text-emerald-400 mt-0.5 font-medium flex items-center'>
              <Icons.trendingDown className='size-3 mr-1' /> ↓ 7.4% reduction
            </p>
          </CardContent>
        </Card>

        <Card className='shadow-xs'>
          <CardHeader className='pb-2'>
            <CardTitle className='text-xs font-medium text-muted-foreground'>
              Human Edit Rate
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className='text-2xl font-bold text-foreground'>{store.metrics.humanEditRate}%</div>
            <p className='text-[11px] text-emerald-600 dark:text-emerald-400 mt-0.5 font-medium flex items-center'>
              <Icons.trendingDown className='size-3 mr-1' /> ↓ 5.8% (fewer edits)
            </p>
          </CardContent>
        </Card>

        <Card className='shadow-xs'>
          <CardHeader className='pb-2'>
            <CardTitle className='text-xs font-medium text-muted-foreground'>
              Compliance Pass Rate
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className='text-2xl font-bold text-emerald-600 dark:text-emerald-400'>
              {store.metrics.compliancePassRate}%
            </div>
            <p className='text-[11px] text-emerald-600 dark:text-emerald-400 mt-0.5 font-medium flex items-center'>
              <Icons.trendingUp className='size-3 mr-1' /> ↑ 8.2% improvement
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Analytics Charts Grid */}
      <div className='grid grid-cols-1 md:grid-cols-12 gap-8'>
        {/* Rejection Reasons Distribution */}
        <div className='md:col-span-6 flex flex-col gap-4'>
          <Card className='shadow-xs'>
            <CardHeader className='pb-2'>
              <CardTitle className='text-sm font-bold text-foreground'>
                Rejection Reasons Analysis
              </CardTitle>
              <CardDescription className='text-xs'>
                Distribution of human reviewer flags over the past 30 days.
              </CardDescription>
            </CardHeader>
            <CardContent className='flex flex-col gap-3 pt-2'>
              {REJECTION_REASONS_DATA.map((item) => (
                <div key={item.reason} className='flex flex-col gap-1'>
                  <div className='flex items-center justify-between text-xs'>
                    <span className='font-medium text-foreground'>{item.reason}</span>
                    <span className='text-muted-foreground font-semibold'>
                      {item.percentage}% ({item.count} assets)
                    </span>
                  </div>
                  <Progress value={item.percentage} className='h-2' />
                </div>
              ))}
            </CardContent>
          </Card>
        </div>

        {/* Learning Trend: Human Edit Rate Decreasing */}
        <div className='md:col-span-6 flex flex-col gap-4'>
          <Card className='shadow-xs'>
            <CardHeader className='pb-2'>
              <CardTitle className='text-sm font-bold text-foreground'>
                Human Edit Rate Trend
              </CardTitle>
              <CardDescription className='text-xs'>
                Human intervention is decreasing as lessons accumulate in memory.
              </CardDescription>
            </CardHeader>
            <CardContent className='flex flex-col gap-4 pt-2'>
              <div className='grid grid-cols-4 gap-3 text-center'>
                {LEARNING_TREND_DATA.map((point) => (
                  <div key={point.week} className='rounded-lg border bg-muted/20 p-3 flex flex-col'>
                    <span className='text-xs font-medium text-muted-foreground'>{point.week}</span>
                    <span className='text-xl font-bold text-foreground mt-1'>
                      {point.editRate}%
                    </span>
                    <span className='text-[10px] text-muted-foreground mt-0.5'>Edit Rate</span>
                  </div>
                ))}
              </div>

              <div className='rounded-md border border-emerald-500/30 bg-emerald-500/5 p-3 text-xs text-emerald-800 dark:text-emerald-300 flex items-start gap-2'>
                <Icons.trendingDown className='size-4 text-emerald-600 dark:text-emerald-400 mt-0.5 shrink-0' />
                <div>
                  <strong>Autonomous Alignment:</strong> Human edit rate reduced from 42% in Week 1 to 18.7% in Week 4 as 40+ reviewer guidelines were committed to few-shot system prompts.
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Lessons Memory Feed */}
      <div className='flex flex-col gap-4 pt-2 border-t'>
        <div className='flex flex-col md:flex-row md:items-center justify-between gap-3'>
          <div>
            <h2 className='text-base font-bold text-foreground'>Lessons Learned Memory</h2>
            <p className='text-xs text-muted-foreground'>
              Searchable catalog of rules synthesized from human reviewer rejections and edits.
            </p>
          </div>

          <div className='flex items-center gap-2'>
            <div className='relative w-64'>
              <Icons.search className='absolute left-2.5 top-2.5 size-3.5 text-muted-foreground' />
              <Input
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder='Search lessons...'
                className='pl-8 h-8 text-xs'
              />
            </div>

            {(['all', 'jade', 'doctorshield', 'jaguar'] as const).map((b) => (
              <Button
                key={b}
                size='xs'
                variant={brandFilter === b ? 'default' : 'outline'}
                onClick={() => setBrandFilter(b)}
                className='capitalize'
              >
                {b}
              </Button>
            ))}
          </div>
        </div>

        <div className='grid grid-cols-1 md:grid-cols-2 gap-4'>
          {filteredLessons.map((lesson) => (
            <Card key={lesson.id} className='shadow-xs hover:border-primary/40 transition-colors'>
              <CardContent className='p-4 flex flex-col gap-2.5'>
                <div className='flex items-center justify-between gap-2'>
                  <div className='flex items-center gap-2'>
                    <Badge variant='outline' className='text-[10px] font-bold font-mono'>
                      {lesson.reason_tag}
                    </Badge>
                    <BrandBadge brandId={lesson.brand_id} />
                  </div>
                  {lesson.platform && (
                    <span className='text-[11px] text-muted-foreground capitalize'>
                      {lesson.platform}
                    </span>
                  )}
                </div>

                <h3 className='text-xs font-bold text-foreground'>{lesson.title}</h3>

                <p className='text-xs text-foreground/90 font-serif italic bg-muted/30 p-2.5 rounded-md'>
                  "{lesson.note}"
                </p>

                {lesson.original_body && (
                  <div className='text-[11px] text-muted-foreground flex flex-col gap-1 border-t pt-2'>
                    <span className='line-through text-destructive/80 text-[10px]'>
                      Original: "{lesson.original_body.slice(0, 90)}..."
                    </span>
                    {lesson.edited_body && (
                      <span className='text-emerald-600 dark:text-emerald-400 font-medium text-[10px]'>
                        Human Revision: "{lesson.edited_body.slice(0, 90)}..."
                      </span>
                    )}
                  </div>
                )}

                <div className='flex items-center justify-between pt-2 border-t text-[11px] text-muted-foreground'>
                  <span>
                    Used in <strong className='text-foreground'>{lesson.used_count}</strong> future generations
                  </span>
                  <span className='text-emerald-600 dark:text-emerald-400 font-medium'>
                    {lesson.impact}
                  </span>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
}
