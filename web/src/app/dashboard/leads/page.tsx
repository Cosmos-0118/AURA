'use client';

import React, { useState } from 'react';
import { toast } from 'sonner';
import { useAuraStore, auraStore } from '@/lib/demo/store';
import type { ExtendedLead } from '@/lib/demo/leads';
import type { BrandId } from '@/lib/api/types';
import { BrandBadge } from '@/components/aura/common';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter
} from '@/components/ui/dialog';
import { Icons } from '@/components/icons';

export default function LeadsPage() {
  const store = useAuraStore();
  const [selectedLead, setSelectedLead] = useState<ExtendedLead | null>(null);
  const [isEditingOutreach, setIsEditingOutreach] = useState(false);
  const [outreachBody, setOutreachBody] = useState('');
  const [brandFilter, setBrandFilter] = useState<BrandId | 'all'>('all');
  const [searchQuery, setSearchQuery] = useState('');

  const filteredLeads = store.leads.filter((lead) => {
    if (brandFilter !== 'all' && lead.brand_id !== brandFilter) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      return (
        lead.name.toLowerCase().includes(q) ||
        lead.industry.toLowerCase().includes(q) ||
        (lead.country && lead.country.toLowerCase().includes(q))
      );
    }
    return true;
  });

  const openLeadDetail = (lead: ExtendedLead) => {
    setSelectedLead(lead);
    setOutreachBody(lead.suggested_outreach.body);
    setIsEditingOutreach(false);
  };

  const handleApproveOutreach = () => {
    if (!selectedLead) return;
    auraStore.approveLeadOutreach(selectedLead.id, outreachBody);
    toast.success(`Outreach draft for ${selectedLead.name} approved for relationship desk`);
    setSelectedLead(null);
  };

  return (
    <div className='flex flex-col gap-6 p-4 md:p-8 max-w-7xl mx-auto w-full'>
      {/* Header */}
      <div className='flex flex-col md:flex-row md:items-center justify-between gap-4 border-b pb-5'>
        <div>
          <div className='flex items-center gap-2 text-xs font-semibold text-muted-foreground uppercase tracking-widest'>
            <span>Account Intelligence</span>
            <span>•</span>
            <span className='text-primary'>Prospect Discovery</span>
          </div>
          <h1 className='text-3xl font-bold tracking-tight text-foreground mt-1'>
            Lead Intelligence
          </h1>
          <p className='text-sm text-muted-foreground mt-0.5'>
            Find organisations that may need JA Assure's underwriting expertise across ASEAN.
          </p>
        </div>

        <div className='flex items-center gap-2'>
          <Button
            variant='outline'
            size='sm'
            onClick={() => toast.success('Lead Agent enriched 14 corporate registries in SG & MY')}
          >
            <Icons.teams className='size-4 mr-1.5' />
            Run Discovery Agent
          </Button>
        </div>
      </div>

      {/* Top Metrics Row */}
      <div className='grid grid-cols-2 md:grid-cols-4 gap-4'>
        <Card className='shadow-xs'>
          <CardHeader className='pb-2'>
            <CardTitle className='text-xs font-medium text-muted-foreground'>
              Prospects Scanned
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className='text-2xl font-bold text-foreground'>184</div>
            <p className='text-[11px] text-muted-foreground mt-0.5'>High-exposure enterprises</p>
          </CardContent>
        </Card>

        <Card className='shadow-xs border-emerald-500/20 bg-emerald-500/[0.02]'>
          <CardHeader className='pb-2'>
            <CardTitle className='text-xs font-medium text-muted-foreground'>
              Qualified Leads
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className='text-2xl font-bold text-emerald-600 dark:text-emerald-400'>
              {store.metrics.qualifiedLeads}
            </div>
            <p className='text-[11px] text-emerald-600 dark:text-emerald-400 mt-0.5 font-medium'>
              +21% this month
            </p>
          </CardContent>
        </Card>

        <Card className='shadow-xs'>
          <CardHeader className='pb-2'>
            <CardTitle className='text-xs font-medium text-muted-foreground'>
              High Fit Score (85+)
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className='text-2xl font-bold text-foreground'>17</div>
            <p className='text-[11px] text-muted-foreground mt-0.5'>Immediate outreach ready</p>
          </CardContent>
        </Card>

        <Card className='shadow-xs'>
          <CardHeader className='pb-2'>
            <CardTitle className='text-xs font-medium text-muted-foreground'>
              Outreach Drafts
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className='text-2xl font-bold text-foreground'>26</div>
            <p className='text-[11px] text-primary mt-0.5 font-medium'>Human review required</p>
          </CardContent>
        </Card>
      </div>

      {/* Filter and Search Bar */}
      <div className='flex flex-col sm:flex-row items-center justify-between gap-3'>
        <div className='relative w-full sm:w-80'>
          <Icons.search className='absolute left-2.5 top-2.5 size-4 text-muted-foreground' />
          <Input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder='Search enterprise by name, industry...'
            className='pl-9 text-xs h-9'
          />
        </div>

        <div className='flex items-center gap-2 self-start sm:self-auto'>
          <span className='text-xs text-muted-foreground font-medium'>Brand Fit:</span>
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

      {/* Lead Table */}
      <Card className='shadow-xs overflow-hidden'>
        <div className='overflow-x-auto'>
          <table className='w-full text-left text-xs'>
            <thead className='border-b bg-muted/30 text-muted-foreground font-medium'>
              <tr>
                <th className='py-3 px-4 font-semibold'>Company</th>
                <th className='py-3 px-4 font-semibold'>Industry</th>
                <th className='py-3 px-4 font-semibold'>Country</th>
                <th className='py-3 px-4 font-semibold'>Brand Fit</th>
                <th className='py-3 px-4 font-semibold text-center'>JA Fit Score</th>
                <th className='py-3 px-4 font-semibold'>Status</th>
                <th className='py-3 px-4 font-semibold text-right'>Action</th>
              </tr>
            </thead>
            <tbody className='divide-y'>
              {filteredLeads.map((lead) => (
                <tr
                  key={lead.id}
                  className='hover:bg-muted/40 transition-colors cursor-pointer'
                  onClick={() => openLeadDetail(lead)}
                >
                  <td className='py-3.5 px-4'>
                    <div className='font-bold text-foreground'>{lead.name}</div>
                    <div className='text-[11px] text-muted-foreground'>{lead.location}</div>
                  </td>
                  <td className='py-3.5 px-4 text-muted-foreground'>{lead.industry}</td>
                  <td className='py-3.5 px-4'>
                    <Badge variant='outline' className='text-[10px]'>
                      {lead.country}
                    </Badge>
                  </td>
                  <td className='py-3.5 px-4'>
                    <BrandBadge brandId={lead.brand_id} />
                  </td>
                  <td className='py-3.5 px-4 text-center'>
                    <span
                      className={`inline-flex items-center justify-center font-bold px-2 py-0.5 rounded-full text-xs ${
                        lead.fit_score >= 90
                          ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400'
                          : lead.fit_score >= 80
                          ? 'bg-blue-500/10 text-blue-600 dark:text-blue-400'
                          : 'bg-amber-500/10 text-amber-600 dark:text-amber-400'
                      }`}
                    >
                      {lead.fit_score} / 100
                    </span>
                  </td>
                  <td className='py-3.5 px-4'>
                    <Badge
                      variant='outline'
                      className={`text-[10px] font-medium capitalize ${
                        lead.status === 'qualified'
                          ? 'bg-emerald-500/10 text-emerald-600 border-emerald-500/20'
                          : 'bg-amber-500/10 text-amber-600 border-amber-500/20'
                      }`}
                    >
                      {lead.status}
                    </Badge>
                  </td>
                  <td className='py-3.5 px-4 text-right'>
                    <Button
                      size='xs'
                      variant='ghost'
                      onClick={(e) => {
                        e.stopPropagation();
                        openLeadDetail(lead);
                      }}
                    >
                      Inspect Lead →
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {/* LEAD DETAIL & PERSONALIZED OUTREACH MODAL */}
      {selectedLead && (
        <Dialog open={Boolean(selectedLead)} onOpenChange={(open) => !open && setSelectedLead(null)}>
          <DialogContent className='max-w-2xl max-h-[90vh] overflow-y-auto p-6'>
            <DialogHeader className='border-b pb-4'>
              <div className='flex items-center justify-between gap-3'>
                <div className='flex items-center gap-2'>
                  <BrandBadge brandId={selectedLead.brand_id} />
                  <span className='text-xs text-muted-foreground'>
                    {selectedLead.country} · {selectedLead.industry}
                  </span>
                </div>
                <div className='flex items-center gap-1.5'>
                  <span className='text-xs text-muted-foreground'>Fit Score:</span>
                  <strong className='text-sm font-bold text-emerald-600 dark:text-emerald-400'>
                    {selectedLead.fit_score} / 100
                  </strong>
                </div>
              </div>

              <DialogTitle className='text-xl font-bold text-foreground mt-2'>
                {selectedLead.name}
              </DialogTitle>
              <DialogDescription className='text-xs'>
                Exposure Profile: {selectedLead.estimated_exposure} · {selectedLead.employee_count} employees
              </DialogDescription>
            </DialogHeader>

            <div className='flex flex-col gap-4 my-2 text-xs'>
              {/* Why this lead section */}
              <div className='rounded-lg border bg-muted/30 p-3 flex flex-col gap-2'>
                <h4 className='font-bold text-foreground flex items-center gap-1.5'>
                  <Icons.sparkles className='size-3.5 text-primary' /> Why this lead?
                </h4>
                <p className='text-muted-foreground italic text-[11px]'>{selectedLead.why}</p>
                <div className='flex flex-col gap-1 mt-1'>
                  {selectedLead.reasons.map((r) => (
                    <div key={r} className='flex items-start gap-2 text-[11px] text-foreground'>
                      <Icons.check className='size-3 text-emerald-600 dark:text-emerald-400 mt-0.5 shrink-0' />
                      <span>{r}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Personalized Outreach Generator Section */}
              <div className='flex flex-col gap-2'>
                <div className='flex items-center justify-between'>
                  <div>
                    <h4 className='font-bold text-foreground'>Suggested Outreach Draft</h4>
                    <p className='text-[10px] text-muted-foreground'>
                      Target Role: {selectedLead.suggested_outreach.recipient_role}
                    </p>
                  </div>
                  <Button
                    size='xs'
                    variant='ghost'
                    onClick={() => setIsEditingOutreach(!isEditingOutreach)}
                  >
                    <Icons.edit className='size-3 mr-1' />
                    {isEditingOutreach ? 'View Mode' : 'Edit Draft'}
                  </Button>
                </div>

                <div className='rounded-md border bg-card p-2 text-xs'>
                  <span className='font-semibold text-muted-foreground'>Subject:</span>{' '}
                  <span className='text-foreground font-medium'>
                    {selectedLead.suggested_outreach.subject}
                  </span>
                </div>

                {isEditingOutreach ? (
                  <Textarea
                    value={outreachBody}
                    onChange={(e) => setOutreachBody(e.target.value)}
                    rows={8}
                    className='text-xs font-mono'
                  />
                ) : (
                  <div className='rounded-lg border bg-muted/20 p-3.5 font-mono text-xs whitespace-pre-wrap leading-relaxed max-h-56 overflow-y-auto'>
                    {outreachBody}
                  </div>
                )}

                <div className='rounded-md border border-amber-500/30 bg-amber-500/5 p-2 text-[10px] text-amber-700 dark:text-amber-400 flex items-center gap-1.5'>
                  <Icons.warning className='size-3.5 shrink-0' />
                  <span>
                    <strong>Safety Constraint:</strong> AURA never automatically sends cold outreach. All correspondence requires human approval and relationship desk dispatch.
                  </span>
                </div>
              </div>
            </div>

            <DialogFooter className='border-t pt-4 gap-2'>
              <Button variant='outline' size='sm' onClick={() => setSelectedLead(null)}>
                Cancel
              </Button>
              <Button
                variant='destructive'
                size='sm'
                onClick={() => {
                  toast.info(`Marked ${selectedLead.name} as rejected`);
                  setSelectedLead(null);
                }}
              >
                Reject Lead
              </Button>
              <Button size='sm' onClick={handleApproveOutreach}>
                <Icons.circleCheck className='size-4 mr-1.5' />
                Approve Outreach Draft
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
}
