'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { toast } from 'sonner';
import { COMPETITOR_INTEL, EMERGING_TRENDS, type EmergingTrend } from '@/lib/demo/research';
import { BrandBadge } from '@/components/aura/common';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter
} from '@/components/ui/dialog';
import { Icons } from '@/components/icons';

export default function ResearchPage() {
  const router = useRouter();
  const [selectedTrend, setSelectedTrend] = useState<EmergingTrend | null>(null);

  const handleGenerateFromIntel = (topic: string) => {
    toast.info(`Pre-filling Campaign Studio with topic: "${topic.slice(0, 30)}..."`);
    router.push('/dashboard/studio');
  };

  return (
    <div className='flex flex-col gap-6 p-4 md:p-8 max-w-7xl mx-auto w-full'>
      {/* Header */}
      <div className='flex flex-col md:flex-row md:items-center justify-between gap-4 border-b pb-5'>
        <div>
          <div className='flex items-center gap-2 text-xs font-semibold text-muted-foreground uppercase tracking-widest'>
            <span>Autonomous Surveillance Agent</span>
            <span>•</span>
            <span className='text-primary'>Signal Intelligence</span>
          </div>
          <h1 className='text-3xl font-bold tracking-tight text-foreground mt-1'>
            Market Intelligence
          </h1>
          <p className='text-sm text-muted-foreground mt-0.5'>
            What changed in the market? Monitoring competitor maneuvers and emerging insurance risks.
          </p>
        </div>

        <div className='flex items-center gap-2'>
          <Button
            variant='outline'
            size='sm'
            onClick={() => toast.success('Agent scan completed: 4 competitor sites checked, 0 new changes since 10:31 PM')}
          >
            <Icons.search className='size-4 mr-1.5' />
            Run Crawl Scan
          </Button>
        </div>
      </div>

      {/* Top Metrics Cards */}
      <div className='grid grid-cols-2 md:grid-cols-4 gap-4'>
        <Card className='shadow-xs'>
          <CardHeader className='pb-2'>
            <CardTitle className='text-xs font-medium text-muted-foreground'>
              Competitors Monitored
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className='text-2xl font-bold text-foreground'>18</div>
            <p className='text-[11px] text-muted-foreground mt-0.5'>Across SG, MY, TH, ID</p>
          </CardContent>
        </Card>

        <Card className='shadow-xs'>
          <CardHeader className='pb-2'>
            <CardTitle className='text-xs font-medium text-muted-foreground'>
              Changes Detected
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className='text-2xl font-bold text-foreground'>12</div>
            <p className='text-[11px] text-amber-600 dark:text-amber-400 mt-0.5 font-medium'>
              +3 in last 48 hours
            </p>
          </CardContent>
        </Card>

        <Card className='shadow-xs'>
          <CardHeader className='pb-2'>
            <CardTitle className='text-xs font-medium text-muted-foreground'>
              New Trends
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className='text-2xl font-bold text-foreground'>7</div>
            <p className='text-[11px] text-emerald-600 dark:text-emerald-400 mt-0.5 font-medium'>
              4 high relevance
            </p>
          </CardContent>
        </Card>

        <Card className='shadow-xs border-primary/20 bg-primary/[0.02]'>
          <CardHeader className='pb-2'>
            <CardTitle className='text-xs font-medium text-muted-foreground'>
              Opportunities
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className='text-2xl font-bold text-primary'>9</div>
            <p className='text-[11px] text-primary mt-0.5 font-medium'>Content responses suggested</p>
          </CardContent>
        </Card>
      </div>

      {/* Two Column Section: Competitor Intelligence & Emerging Trends */}
      <div className='grid grid-cols-1 lg:grid-cols-12 gap-8'>
        {/* Left Column: Competitor Intelligence */}
        <div className='lg:col-span-7 flex flex-col gap-4'>
          <div className='flex items-center justify-between'>
            <div>
              <h2 className='text-base font-bold text-foreground'>Competitor Intelligence</h2>
              <p className='text-xs text-muted-foreground'>
                Recent policy modifications, marketing pushes, and positioning shifts.
              </p>
            </div>
            <Badge variant='outline' className='text-xs'>
              Live Feed
            </Badge>
          </div>

          <div className='flex flex-col gap-3.5'>
            {COMPETITOR_INTEL.map((item) => (
              <Card key={item.id} className='shadow-xs hover:border-foreground/30 transition-colors'>
                <CardContent className='p-4 flex flex-col gap-2.5'>
                  <div className='flex items-center justify-between gap-2'>
                    <div className='flex items-center gap-2'>
                      <span className='font-bold text-sm text-foreground'>
                        {item.competitor_name}
                      </span>
                      <BrandBadge brandId={item.target_brand} />
                    </div>
                    <div className='flex items-center gap-2'>
                      <Badge
                        variant={item.impact === 'High' ? 'destructive' : 'secondary'}
                        className='text-[10px]'
                      >
                        {item.impact} Impact
                      </Badge>
                      <span className='text-[11px] text-muted-foreground'>{item.timestamp}</span>
                    </div>
                  </div>

                  <div className='text-xs text-muted-foreground bg-muted/30 p-2.5 rounded-md'>
                    <strong className='text-foreground'>Detected change:</strong> {item.detected_change}
                  </div>

                  <div className='rounded-md border border-primary/20 bg-primary/5 p-3 text-xs flex flex-col gap-2'>
                    <div className='text-foreground font-medium'>
                      💡 <strong className='text-primary'>Opportunity:</strong> {item.opportunity}
                    </div>
                    <div className='flex items-center justify-between pt-1 border-t border-primary/10'>
                      <span className='text-[11px] text-muted-foreground italic truncate max-w-[340px]'>
                        "{item.suggested_topic}"
                      </span>
                      <Button
                        size='xs'
                        onClick={() => handleGenerateFromIntel(item.suggested_topic)}
                      >
                        <Icons.sparkles className='size-3 mr-1' />
                        Generate Content
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>

        {/* Right Column: Emerging Trends */}
        <div className='lg:col-span-5 flex flex-col gap-4'>
          <div className='flex items-center justify-between'>
            <div>
              <h2 className='text-base font-bold text-foreground'>Emerging Topics</h2>
              <p className='text-xs text-muted-foreground'>
                Trend momentum calculated from industry forums, news, and search signals.
              </p>
            </div>
            <span className='text-xs text-muted-foreground font-medium'>Relevance Score</span>
          </div>

          <div className='flex flex-col gap-3'>
            {EMERGING_TRENDS.map((trend) => (
              <Card
                key={trend.id}
                onClick={() => setSelectedTrend(trend)}
                className='shadow-xs hover:border-primary/50 cursor-pointer transition-all p-4'
              >
                <div className='flex items-start justify-between gap-2 mb-2'>
                  <div>
                    <h3 className='text-xs font-bold text-foreground hover:text-primary transition-colors'>
                      {trend.title}
                    </h3>
                    <p className='text-[11px] text-muted-foreground mt-0.5 line-clamp-1'>
                      {trend.summary}
                    </p>
                  </div>
                  <BrandBadge brandId={trend.target_brand} className='shrink-0' />
                </div>

                <div className='flex items-center gap-3 mt-3'>
                  <Progress value={trend.percentage} className='h-2 flex-1' />
                  <span className='text-xs font-bold text-foreground w-10 text-right'>
                    {trend.percentage}%
                  </span>
                </div>

                <div className='flex items-center justify-between mt-2 pt-2 border-t text-[10px] text-muted-foreground'>
                  <span>Click to view underwriting response</span>
                  <span className='text-primary font-medium flex items-center'>
                    Inspect Trend <Icons.chevronRight className='size-3 ml-0.5' />
                  </span>
                </div>
              </Card>
            ))}
          </div>
        </div>
      </div>

      {/* TREND DETAIL MODAL */}
      {selectedTrend && (
        <Dialog open={Boolean(selectedTrend)} onOpenChange={(open) => !open && setSelectedTrend(null)}>
          <DialogContent className='max-w-lg p-6'>
            <DialogHeader className='border-b pb-3'>
              <div className='flex items-center gap-2'>
                <BrandBadge brandId={selectedTrend.target_brand} />
                <Badge variant='outline' className='text-xs'>
                  {selectedTrend.percentage}% Momentum
                </Badge>
              </div>
              <DialogTitle className='text-base font-bold text-foreground mt-2'>
                {selectedTrend.title}
              </DialogTitle>
              <DialogDescription className='text-xs'>
                Audience: {selectedTrend.target_audience}
              </DialogDescription>
            </DialogHeader>

            <div className='flex flex-col gap-3 my-2 text-xs'>
              <div>
                <strong className='text-foreground font-semibold'>Why it matters:</strong>
                <p className='text-muted-foreground mt-0.5 leading-relaxed'>
                  {selectedTrend.why_it_matters}
                </p>
              </div>

              <div>
                <strong className='text-foreground font-semibold'>Information Sources:</strong>
                <div className='flex flex-wrap gap-1.5 mt-1'>
                  {selectedTrend.sources.map((src) => (
                    <Badge key={src} variant='secondary' className='text-[10px]'>
                      {src}
                    </Badge>
                  ))}
                </div>
              </div>

              <div className='rounded-lg border border-primary/20 bg-primary/5 p-3'>
                <strong className='text-primary font-semibold flex items-center gap-1.5'>
                  <Icons.sparkles className='size-3.5' /> Suggested JA Assure Response:
                </strong>
                <p className='text-foreground text-xs mt-1 leading-relaxed'>
                  {selectedTrend.suggested_response}
                </p>
              </div>
            </div>

            <DialogFooter className='gap-2 pt-3 border-t'>
              <Button variant='outline' size='sm' onClick={() => setSelectedTrend(null)}>
                Close
              </Button>
              <Button
                size='sm'
                onClick={() => {
                  setSelectedTrend(null);
                  handleGenerateFromIntel(selectedTrend.suggested_response);
                }}
              >
                <Icons.sparkles className='size-3.5 mr-1.5' />
                Generate Campaign from Trend
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
}
