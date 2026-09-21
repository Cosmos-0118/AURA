'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { DEMO_BRANDS, type ExtendedBrand } from '@/lib/demo/brands';
import { BrandBadge } from '@/components/aura/common';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter
} from '@/components/ui/dialog';
import { Icons } from '@/components/icons';

export default function BrandsPage() {
  const [selectedBrand, setSelectedBrand] = useState<ExtendedBrand | null>(null);

  return (
    <div className='flex flex-col gap-6 p-4 md:p-8 max-w-7xl mx-auto w-full'>
      {/* Header */}
      <div className='flex flex-col md:flex-row md:items-center justify-between gap-4 border-b pb-5'>
        <div>
          <div className='flex items-center gap-2 text-xs font-semibold text-muted-foreground uppercase tracking-widest'>
            <span>JA Assure Group</span>
            <span>•</span>
            <span className='text-primary'>Brand Knowledge Base</span>
          </div>
          <h1 className='text-3xl font-bold tracking-tight text-foreground mt-1'>
            Brand Portfolios
          </h1>
          <p className='text-sm text-muted-foreground mt-0.5'>
            Institutional brand personalities, tone guardrails, and underwriting audience definitions.
          </p>
        </div>

        <Link href='/dashboard/studio'>
          <Button size='sm'>
            <Icons.sparkles className='size-4 mr-1.5' />
            Create for Brand
          </Button>
        </Link>
      </div>

      {/* 3 Large Brand Cards */}
      <div className='grid grid-cols-1 md:grid-cols-3 gap-6'>
        {Object.values(DEMO_BRANDS).map((brand) => (
          <Card
            key={brand.id}
            className='shadow-xs hover:border-foreground/40 transition-all flex flex-col justify-between'
          >
            <CardHeader className='pb-3'>
              <div className='flex items-center justify-between'>
                <BrandBadge brandId={brand.id} />
                <Badge variant='outline' className='text-xs font-semibold text-emerald-600 dark:text-emerald-400'>
                  {brand.stats.approvalRate}% Approval
                </Badge>
              </div>

              <CardTitle className='text-lg font-bold text-foreground mt-2'>
                {brand.name}
              </CardTitle>
              <p className='text-xs font-medium text-primary'>{brand.tagline}</p>
              <CardDescription className='text-xs mt-1 leading-relaxed'>
                {brand.description}
              </CardDescription>
            </CardHeader>

            <CardContent className='flex flex-col gap-4 pt-0'>
              {/* Voice Tags */}
              <div>
                <span className='text-[11px] font-bold text-muted-foreground uppercase tracking-wider block mb-1.5'>
                  Brand Voice
                </span>
                <div className='flex flex-wrap gap-1'>
                  {brand.tone.map((t) => (
                    <Badge key={t} variant='secondary' className='text-[11px]'>
                      {t}
                    </Badge>
                  ))}
                </div>
              </div>

              {/* Audience */}
              <div>
                <span className='text-[11px] font-bold text-muted-foreground uppercase tracking-wider block mb-1'>
                  Primary Audiences
                </span>
                <p className='text-xs text-foreground/90'>{brand.audience}</p>
              </div>

              {/* Avoid */}
              <div className='rounded-md border border-destructive/20 bg-destructive/5 p-2.5 text-xs text-destructive'>
                <span className='font-bold flex items-center gap-1 mb-1'>
                  <Icons.warning className='size-3.5' /> Avoid (Hard Constraint):
                </span>
                <ul className='list-disc list-inside text-[11px] space-y-0.5 text-foreground/80'>
                  {brand.dont_list.slice(0, 2).map((d, i) => (
                    <li key={i}>{d}</li>
                  ))}
                </ul>
              </div>

              {/* Stats Footer */}
              <div className='flex items-center justify-between pt-3 border-t text-xs text-muted-foreground'>
                <span>
                  <strong className='text-foreground'>{brand.stats.assets}</strong> assets ·{' '}
                  <strong className='text-foreground'>{brand.stats.published}</strong> published
                </span>
                <Button size='xs' variant='outline' onClick={() => setSelectedBrand(brand)}>
                  Full DNA →
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* BRAND DETAIL MODAL */}
      {selectedBrand && (
        <Dialog open={Boolean(selectedBrand)} onOpenChange={(open) => !open && setSelectedBrand(null)}>
          <DialogContent className='max-w-2xl max-h-[90vh] overflow-y-auto p-6'>
            <DialogHeader className='border-b pb-4'>
              <div className='flex items-center justify-between'>
                <BrandBadge brandId={selectedBrand.id} />
                <span className='text-xs text-muted-foreground'>
                  AURA Underwriting Portfolio
                </span>
              </div>
              <DialogTitle className='text-xl font-bold text-foreground mt-2'>
                {selectedBrand.name} — Full Brand Guidelines
              </DialogTitle>
              <DialogDescription className='text-xs'>
                {selectedBrand.tagline}
              </DialogDescription>
            </DialogHeader>

            <div className='flex flex-col gap-4 my-2 text-xs'>
              {/* Personality */}
              <div>
                <strong className='text-xs font-bold text-foreground block mb-1.5'>
                  Personality Traits
                </strong>
                <div className='flex flex-wrap gap-1.5'>
                  {selectedBrand.personality.map((p) => (
                    <Badge key={p} variant='outline' className='text-xs'>
                      {p}
                    </Badge>
                  ))}
                </div>
              </div>

              {/* Underwriting Products */}
              <div>
                <strong className='text-xs font-bold text-foreground block mb-1.5'>
                  Key Underwriting Products
                </strong>
                <div className='grid grid-cols-1 sm:grid-cols-2 gap-2'>
                  {selectedBrand.products.map((prod) => (
                    <div key={prod} className='rounded-md border p-2 bg-muted/20 text-xs font-medium'>
                      • {prod}
                    </div>
                  ))}
                </div>
              </div>

              {/* Do List */}
              <div className='rounded-lg border border-emerald-500/30 bg-emerald-500/5 p-3 flex flex-col gap-1.5'>
                <strong className='text-emerald-700 dark:text-emerald-400 font-bold flex items-center gap-1.5'>
                  <Icons.circleCheck className='size-4' /> Content Do's (Approved Patterns)
                </strong>
                <ul className='list-disc list-inside space-y-1 text-foreground/90 text-xs'>
                  {selectedBrand.do_list.map((item, idx) => (
                    <li key={idx}>{item}</li>
                  ))}
                </ul>
              </div>

              {/* Don't List */}
              <div className='rounded-lg border border-destructive/30 bg-destructive/5 p-3 flex flex-col gap-1.5'>
                <strong className='text-destructive font-bold flex items-center gap-1.5'>
                  <Icons.circleX className='size-4' /> Content Don'ts (Strict Boundaries)
                </strong>
                <ul className='list-disc list-inside space-y-1 text-foreground/90 text-xs'>
                  {selectedBrand.dont_list.map((item, idx) => (
                    <li key={idx}>{item}</li>
                  ))}
                </ul>
              </div>

              {/* Compliance Considerations */}
              <div className='rounded-md border bg-card p-3'>
                <strong className='text-foreground font-semibold block mb-1'>
                  Regulatory & Compliance Considerations
                </strong>
                <p className='text-muted-foreground text-xs leading-relaxed'>
                  {selectedBrand.compliance_considerations}
                </p>
              </div>
            </div>

            <DialogFooter className='border-t pt-4'>
              <Button size='sm' onClick={() => setSelectedBrand(null)}>
                Close
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
}
