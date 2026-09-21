'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { useAuraStore } from '@/lib/demo/store';
import { DEMO_BRANDS } from '@/lib/demo/brands';
import {
  BrandBadge,
  ComplianceVerdictBadge,
  AuraPipelineLifecycle
} from '@/components/aura/common';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Icons } from '@/components/icons';

export default function DashboardOverviewPage() {
  const store = useAuraStore();
  const [greeting, setGreeting] = useState('Good day');
  const [currentDateStr, setCurrentDateStr] = useState('');

  useEffect(() => {
    const hour = new Date().getHours();
    if (hour < 12) setGreeting('Good morning');
    else if (hour < 17) setGreeting('Good afternoon');
    else setGreeting('Good evening');

    setCurrentDateStr(
      new Date().toLocaleDateString('en-US', {
        weekday: 'long',
        month: 'long',
        day: 'numeric',
        year: 'numeric'
      })
    );
  }, []);

  const pendingReviewAssets = store.assets.filter(
    (a) => a.status === 'pending_review' || a.status === 'compliance_failed'
  );

  return (
    <div className='flex flex-col gap-6 p-4 md:p-8 max-w-7xl mx-auto w-full'>
      {/* Top Header */}
      <div className='flex flex-col md:flex-row md:items-center justify-between gap-4 border-b pb-5'>
        <div>
          <div className='flex items-center gap-2 text-xs font-semibold text-muted-foreground uppercase tracking-widest'>
            <span>JA Assure Operations</span>
            <span>•</span>
            <span className='text-primary'>{currentDateStr}</span>
          </div>
          <h1 className='text-3xl font-bold tracking-tight text-foreground mt-1'>
            {greeting}
          </h1>
          <p className='text-sm text-muted-foreground mt-0.5'>
            AURA Command Center · Your marketing operation at a glance.
          </p>
        </div>

        <div className='flex items-center gap-2'>
          <Link href='/dashboard/review'>
            <Button variant='outline' size='sm'>
              <Icons.checks className='size-4 mr-1.5' />
              Review Queue ({pendingReviewAssets.length})
            </Button>
          </Link>
          <Link href='/dashboard/studio'>
            <Button size='sm'>
              <Icons.sparkles className='size-4 mr-1.5' />
              New Campaign
            </Button>
          </Link>
        </div>
      </div>

      {/* Global Pipeline Banner */}
      <AuraPipelineLifecycle />

      {/* Primary Metrics Row */}
      <div className='grid grid-cols-2 md:grid-cols-4 gap-4'>
        <Card className='shadow-xs'>
          <CardHeader className='flex flex-row items-center justify-between pb-2 space-y-0'>
            <CardTitle className='text-xs font-medium text-muted-foreground'>
              Content Generated
            </CardTitle>
            <Icons.post className='size-4 text-muted-foreground' />
          </CardHeader>
          <CardContent>
            <div className='text-2xl font-bold text-foreground'>{store.metrics.contentGenerated}</div>
            <p className='text-[11px] text-emerald-600 dark:text-emerald-400 mt-1 flex items-center font-medium'>
              <Icons.trendingUp className='size-3 mr-1' /> +18% this week
            </p>
          </CardContent>
        </Card>

        <Card className='shadow-xs border-amber-500/20 bg-amber-500/[0.02]'>
          <CardHeader className='flex flex-row items-center justify-between pb-2 space-y-0'>
            <CardTitle className='text-xs font-medium text-muted-foreground'>
              Awaiting Review
            </CardTitle>
            <Icons.clock className='size-4 text-amber-500' />
          </CardHeader>
          <CardContent>
            <div className='text-2xl font-bold text-foreground'>{store.metrics.awaitingReview}</div>
            <p className='text-[11px] text-amber-600 dark:text-amber-400 mt-1 flex items-center font-medium'>
              <Icons.warning className='size-3 mr-1' /> 3 high priority
            </p>
          </CardContent>
        </Card>

        <Card className='shadow-xs'>
          <CardHeader className='flex flex-row items-center justify-between pb-2 space-y-0'>
            <CardTitle className='text-xs font-medium text-muted-foreground'>
              Approved Assets
            </CardTitle>
            <Icons.circleCheck className='size-4 text-muted-foreground' />
          </CardHeader>
          <CardContent>
            <div className='text-2xl font-bold text-foreground'>{store.metrics.approved}</div>
            <p className='text-[11px] text-emerald-600 dark:text-emerald-400 mt-1 flex items-center font-medium'>
              <Icons.trendingUp className='size-3 mr-1' /> +12 this week
            </p>
          </CardContent>
        </Card>

        <Card className='shadow-xs'>
          <CardHeader className='flex flex-row items-center justify-between pb-2 space-y-0'>
            <CardTitle className='text-xs font-medium text-muted-foreground'>
              Qualified Leads
            </CardTitle>
            <Icons.teams className='size-4 text-muted-foreground' />
          </CardHeader>
          <CardContent>
            <div className='text-2xl font-bold text-foreground'>{store.metrics.qualifiedLeads}</div>
            <p className='text-[11px] text-emerald-600 dark:text-emerald-400 mt-1 flex items-center font-medium'>
              <Icons.trendingUp className='size-3 mr-1' /> +21% this month
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Secondary Operational Metrics Row */}
      <div className='grid grid-cols-2 md:grid-cols-4 gap-4'>
        <div className='rounded-lg border bg-card/60 p-4 shadow-xs'>
          <div className='text-xs text-muted-foreground font-medium'>Compliance Pass Rate</div>
          <div className='text-xl font-bold text-foreground mt-1'>
            {store.metrics.compliancePassRate}%
          </div>
          <div className='text-[11px] text-emerald-600 dark:text-emerald-400 mt-0.5'>
            ↑ 8.2% vs last month
          </div>
        </div>

        <div className='rounded-lg border bg-card/60 p-4 shadow-xs'>
          <div className='text-xs text-muted-foreground font-medium'>Human Edit Rate</div>
          <div className='text-xl font-bold text-foreground mt-1'>
            {store.metrics.humanEditRate}%
          </div>
          <div className='text-[11px] text-emerald-600 dark:text-emerald-400 mt-0.5'>
            ↓ 5.8% (less friction)
          </div>
        </div>

        <div className='rounded-lg border bg-card/60 p-4 shadow-xs'>
          <div className='text-xs text-muted-foreground font-medium'>Rejection Rate</div>
          <div className='text-xl font-bold text-foreground mt-1'>
            {store.metrics.rejectionRate}%
          </div>
          <div className='text-[11px] text-emerald-600 dark:text-emerald-400 mt-0.5'>
            ↓ 7.4% reduction
          </div>
        </div>

        <div className='rounded-lg border bg-card/60 p-4 shadow-xs'>
          <div className='text-xs text-muted-foreground font-medium'>Published Assets</div>
          <div className='text-xl font-bold text-foreground mt-1'>
            {store.metrics.publishedAssets}
          </div>
          <div className='text-[11px] text-muted-foreground mt-0.5'>Project 2 (The Hands)</div>
        </div>
      </div>

      {/* Two Column Grid: Priority Review & Agent Activity Feed */}
      <div className='grid grid-cols-1 lg:grid-cols-12 gap-6'>
        {/* Needs Your Attention: Priority Review */}
        <div className='lg:col-span-7 flex flex-col gap-4'>
          <div className='flex items-center justify-between'>
            <div>
              <h2 className='text-base font-bold text-foreground'>Needs your attention</h2>
              <p className='text-xs text-muted-foreground'>
                Content awaiting human editorial and statutory compliance inspection.
              </p>
            </div>
            <Link
              href='/dashboard/review'
              className='text-xs font-semibold text-primary hover:underline flex items-center'
            >
              View all ({pendingReviewAssets.length}) <Icons.arrowRight className='size-3 ml-1' />
            </Link>
          </div>

          <div className='flex flex-col gap-3'>
            {pendingReviewAssets.slice(0, 3).map((asset) => (
              <Card
                key={asset.id}
                className='shadow-xs hover:border-foreground/30 transition-colors border'
              >
                <CardContent className='p-4'>
                  <div className='flex items-start justify-between gap-3'>
                    <div className='flex items-center gap-2 flex-wrap'>
                      <BrandBadge brandId={asset.brand_id} />
                      <span className='text-xs font-medium text-muted-foreground capitalize'>
                        {asset.platform} · {asset.content_type}
                      </span>
                      {asset.priority === 'high' && (
                        <Badge variant='destructive' className='text-[10px] py-0 px-1.5'>
                          High Priority
                        </Badge>
                      )}
                    </div>
                    <ComplianceVerdictBadge
                      verdict={asset.compliance?.result}
                      risk={asset.compliance?.risk}
                    />
                  </div>

                  <p className='text-xs text-foreground/90 mt-2.5 line-clamp-2 italic font-serif leading-relaxed'>
                    "{asset.body}"
                  </p>

                  <div className='flex items-center justify-between mt-3 pt-2 border-t text-[11px] text-muted-foreground'>
                    <span>
                      Generated {Math.round((Date.now() - new Date(asset.created_at).getTime()) / 60000)} mins ago
                    </span>
                    <Link href='/dashboard/review'>
                      <Button size='xs'>
                        Review Asset
                        <Icons.chevronRight className='size-3 ml-1' />
                      </Button>
                    </Link>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>

          {/* Quick Nav to other modules */}
          <div className='grid grid-cols-3 gap-3 pt-2'>
            <Link
              href='/dashboard/research'
              className='rounded-lg border p-3 bg-card hover:bg-muted/40 transition-colors flex flex-col gap-1'
            >
              <div className='flex items-center gap-1.5 text-xs font-semibold text-foreground'>
                <Icons.search className='size-3.5 text-primary' /> Market Intel
              </div>
              <span className='text-[11px] text-muted-foreground'>12 competitor changes detected</span>
            </Link>

            <Link
              href='/dashboard/leads'
              className='rounded-lg border p-3 bg-card hover:bg-muted/40 transition-colors flex flex-col gap-1'
            >
              <div className='flex items-center gap-1.5 text-xs font-semibold text-foreground'>
                <Icons.teams className='size-3.5 text-primary' /> Leads
              </div>
              <span className='text-[11px] text-muted-foreground'>34 qualified enterprise fits</span>
            </Link>

            <Link
              href='/dashboard/publishing'
              className='rounded-lg border p-3 bg-card hover:bg-muted/40 transition-colors flex flex-col gap-1'
            >
              <div className='flex items-center gap-1.5 text-xs font-semibold text-foreground'>
                <Icons.send className='size-3.5 text-primary' /> Publishing
              </div>
              <span className='text-[11px] text-muted-foreground'>8 ready to dispatch</span>
            </Link>
          </div>
        </div>

        {/* Agent Activity Section */}
        <div className='lg:col-span-5 flex flex-col gap-4'>
          <div>
            <h2 className='text-base font-bold text-foreground'>Agent Activity</h2>
            <p className='text-xs text-muted-foreground'>
              Real-time telemetry across autonomous pipeline agents.
            </p>
          </div>

          <Card className='shadow-xs'>
            <CardContent className='p-4 flex flex-col gap-3.5'>
              {store.activity.slice(0, 5).map((item) => (
                <div key={item.id} className='flex items-start gap-3 text-xs'>
                  <div className='rounded-md border p-1.5 bg-muted/60 shrink-0 text-foreground'>
                    {item.agentType === 'content' && <Icons.post className='size-3.5' />}
                    {item.agentType === 'compliance' && <Icons.warning className='size-3.5 text-amber-500' />}
                    {item.agentType === 'research' && <Icons.search className='size-3.5 text-sky-500' />}
                    {item.agentType === 'learning' && <Icons.sparkles className='size-3.5 text-purple-500' />}
                    {item.agentType === 'lead' && <Icons.teams className='size-3.5 text-emerald-500' />}
                  </div>

                  <div className='flex flex-col flex-1 min-w-0'>
                    <div className='flex items-center justify-between'>
                      <span className='font-semibold text-foreground'>{item.agent}</span>
                      <span className='text-[10px] text-muted-foreground'>{item.time}</span>
                    </div>
                    <p className='text-muted-foreground text-[11px] mt-0.5 truncate'>
                      {item.description}
                    </p>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Brand Performance Section */}
      <div className='flex flex-col gap-3 pt-2 border-t'>
        <div className='flex items-center justify-between'>
          <div>
            <h2 className='text-base font-bold text-foreground'>Brand Performance</h2>
            <p className='text-xs text-muted-foreground'>
              Active underwriting product portfolios managed by AURA.
            </p>
          </div>
          <Link
            href='/dashboard/brands'
            className='text-xs font-semibold text-primary hover:underline flex items-center'
          >
            Manage brand DNA <Icons.arrowRight className='size-3 ml-1' />
          </Link>
        </div>

        <div className='grid grid-cols-1 md:grid-cols-3 gap-4'>
          {Object.values(DEMO_BRANDS).map((brand) => (
            <Card key={brand.id} className='shadow-xs'>
              <CardHeader className='pb-2'>
                <div className='flex items-center justify-between'>
                  <BrandBadge brandId={brand.id} />
                  <span className='text-xs font-semibold text-emerald-600 dark:text-emerald-400'>
                    {brand.stats.approvalRate}% Approval
                  </span>
                </div>
                <CardTitle className='text-sm font-bold text-foreground mt-2'>
                  {brand.tagline}
                </CardTitle>
                <CardDescription className='text-xs line-clamp-2'>
                  {brand.description}
                </CardDescription>
              </CardHeader>
              <CardContent className='pt-2 border-t flex items-center justify-between text-xs text-muted-foreground'>
                <span>
                  <strong className='text-foreground'>{brand.stats.assets}</strong> assets
                </span>
                <span>
                  <strong className='text-foreground'>{brand.stats.published}</strong> published
                </span>
                <Link
                  href='/dashboard/studio'
                  className='text-xs font-semibold text-primary hover:underline'
                >
                  Create →
                </Link>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
}
