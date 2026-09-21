'use client';

import React from 'react';
import { toast } from 'sonner';
import { auraStore } from '@/lib/demo/store';
import { COMPLIANCE_RULES } from '@/lib/demo/rules';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Icons } from '@/components/icons';

function handleResetData() {
  auraStore.resetDefaults();
  toast.success('Reset all demo state to clean hackathon baseline');
}

export default function SettingsPage() {

  return (
    <div className='flex flex-col gap-6 p-4 md:p-8 max-w-4xl mx-auto w-full'>
      {/* Header */}
      <div className='border-b pb-5'>
        <div className='flex items-center gap-2 text-xs font-semibold text-muted-foreground uppercase tracking-widest'>
          <span>System Architecture</span>
          <span>•</span>
          <span className='text-primary'>Configuration</span>
        </div>
        <h1 className='text-3xl font-bold tracking-tight text-foreground mt-1'>
          System Settings
        </h1>
        <p className='text-sm text-muted-foreground mt-0.5'>
          Enterprise workspace credentials, compliance policy rules, and safety constraints.
        </p>
      </div>

      <div className='flex flex-col gap-6'>
        {/* Workspace */}
        <Card className='shadow-xs'>
          <CardHeader className='pb-3'>
            <CardTitle className='text-sm font-bold text-foreground'>
              Enterprise Workspace
            </CardTitle>
            <CardDescription className='text-xs'>
              Underwriting entity and regional operations authority.
            </CardDescription>
          </CardHeader>
          <CardContent className='flex flex-col gap-3 text-xs'>
            <div className='grid grid-cols-1 sm:grid-cols-2 gap-3'>
              <div className='flex flex-col gap-1.5'>
                <Label className='text-xs'>Organization Name</Label>
                <Input value='JA Assure Group Pte. Ltd.' readOnly className='h-9 bg-muted/30 text-xs' />
              </div>
              <div className='flex flex-col gap-1.5'>
                <Label className='text-xs'>Operational Territory</Label>
                <Input value='ASEAN (SG, MY, TH, ID)' readOnly className='h-9 bg-muted/30 text-xs' />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* AI Provider */}
        <Card className='shadow-xs'>
          <CardHeader className='pb-3'>
            <div className='flex items-center justify-between'>
              <CardTitle className='text-sm font-bold text-foreground'>
                AI Generative Foundation
              </CardTitle>
              <Badge variant='outline' className='bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20 text-xs gap-1'>
                <Icons.circleCheck className='size-3.5' /> Connected
              </Badge>
            </div>
            <CardDescription className='text-xs'>
              Primary LLM reasoning and multi-modal creative synthesis provider.
            </CardDescription>
          </CardHeader>
          <CardContent className='flex flex-col gap-3 text-xs'>
            <div className='flex items-center justify-between p-3 rounded-lg border bg-muted/20'>
              <div className='flex items-center gap-3'>
                <div className='h-8 w-8 rounded-lg bg-foreground text-background flex items-center justify-center font-bold text-xs'>
                  G
                </div>
                <div>
                  <div className='font-bold text-foreground'>Google Gemini 1.5 Pro & Flash</div>
                  <div className='text-[11px] text-muted-foreground'>
                    Active for Content Agent, Research Agent, and Compliance Engine
                  </div>
                </div>
              </div>
              <span className='text-xs font-mono text-muted-foreground'>
                gemini-1.5-pro-002
              </span>
            </div>

            <div className='text-[11px] text-muted-foreground italic'>
              Note: API keys and credentials are encrypted on the backend server environment and never exposed to the client.
            </div>
          </CardContent>
        </Card>

        {/* Compliance Safety Engine */}
        <Card className='shadow-xs'>
          <CardHeader className='pb-3'>
            <div className='flex items-center justify-between'>
              <CardTitle className='text-sm font-bold text-foreground'>
                Statutory Compliance Engine
              </CardTitle>
              <Badge variant='outline' className='text-xs font-mono'>
                {COMPLIANCE_RULES.length} Rules Active
              </Badge>
            </div>
            <CardDescription className='text-xs'>
              Deterministic and neural compliance checks enforcing insurance statutory standards.
            </CardDescription>
          </CardHeader>
          <CardContent className='flex flex-col gap-2 text-xs'>
            <div className='grid grid-cols-1 sm:grid-cols-2 gap-2'>
              {COMPLIANCE_RULES.map((rule) => (
                <div key={rule.id} className='rounded-md border p-2.5 bg-card flex items-start gap-2'>
                  <Icons.check className='size-3.5 text-emerald-600 dark:text-emerald-400 mt-0.5 shrink-0' />
                  <div>
                    <div className='font-semibold text-foreground text-xs'>
                      {rule.name}
                    </div>
                    <div className='text-[10px] text-muted-foreground font-mono'>
                      Rule ID: {rule.id} · {rule.category.toUpperCase()}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Human Review Enforcement Constraint */}
        <Card className='shadow-xs border-primary/30 bg-primary/[0.02]'>
          <CardHeader className='pb-3'>
            <div className='flex items-center justify-between'>
              <CardTitle className='text-sm font-bold text-foreground flex items-center gap-2'>
                <Icons.lock className='size-4 text-primary' /> Core Safety Constraint: Human Approval
              </CardTitle>
              <Badge className='bg-primary text-primary-foreground text-xs font-semibold'>
                ✓ Enforced (Non-Editable)
              </Badge>
            </div>
            <CardDescription className='text-xs'>
              Architectural guarantee ensuring no AI-generated post or lead outreach is published without human sign-off.
            </CardDescription>
          </CardHeader>
          <CardContent className='text-xs text-muted-foreground leading-relaxed'>
            In accordance with JA Assure risk governance, autonomous publication bypass is permanently disabled. Every piece of copy must traverse the Human Review Queue before Project 2 dispatch.
          </CardContent>
        </Card>

        {/* Hackathon Demo Controls */}
        <Card className='shadow-xs border-amber-500/20'>
          <CardHeader className='pb-3'>
            <CardTitle className='text-sm font-bold text-foreground'>
              Hackathon Presentation & Demo Controls
            </CardTitle>
            <CardDescription className='text-xs'>
              Utilities for live jury evaluation and demonstration resets.
            </CardDescription>
          </CardHeader>
          <CardContent className='flex flex-col gap-3 text-xs'>
            <div className='flex items-center justify-between p-3 rounded-lg border bg-muted/20'>
              <div>
                <div className='font-bold text-foreground'>Seeded Interactive Demo State</div>
                <div className='text-[11px] text-muted-foreground'>
                  Pre-configured with intentional compliance failures, pending review items, and realistic ASEAN leads.
                </div>
              </div>
              <Button size='sm' variant='outline' onClick={handleResetData}>
                Reset to Clean Baseline
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
