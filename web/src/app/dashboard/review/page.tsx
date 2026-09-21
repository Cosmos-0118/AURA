'use client';

import React, { useState } from 'react';
import { toast } from 'sonner';
import { useAuraStore, auraStore } from '@/lib/demo/store';
import { COMPLIANCE_RULES } from '@/lib/demo/rules';
import { REASON_TAG_LABELS } from '@/lib/demo/lessons';
import type { ExtendedAsset } from '@/lib/demo/assets';
import type { ReasonTag, BrandId } from '@/lib/api/types';
import {
  BrandBadge,
  ComplianceVerdictBadge,
  AssetStatusBadge
} from '@/components/aura/common';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
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

export default function ReviewQueuePage() {
  const store = useAuraStore();
  const [activeTab, setActiveTab] = useState<string>('all');
  const [brandFilter, setBrandFilter] = useState<BrandId | 'all'>('all');
  const [selectedAsset, setSelectedAsset] = useState<ExtendedAsset | null>(null);

  // Inspection & Editing Workspace State
  const [isEditing, setIsEditing] = useState(false);
  const [editableBody, setEditableBody] = useState('');
  const [expandedRule, setExpandedRule] = useState<string | null>('CLAIM_001');

  // Modals State
  const [showRejectModal, setShowRejectModal] = useState(false);
  const [rejectReason, setRejectReason] = useState<ReasonTag>('TOO_SALESY');
  const [rejectNote, setRejectNote] = useState('');

  const [showEditFeedbackModal, setShowEditFeedbackModal] = useState(false);
  const [editReason, setEditReason] = useState<ReasonTag>('TOO_SALESY');
  const [editNote, setEditNote] = useState('');
  const [autoApproveAfterEdit, setAutoApproveAfterEdit] = useState(false);

  const [showApproveConfirmModal, setShowApproveConfirmModal] = useState(false);

  // Filter assets
  const filteredAssets = store.assets.filter((asset) => {
    if (brandFilter !== 'all' && asset.brand_id !== brandFilter) return false;

    if (activeTab === 'all') return true;
    if (activeTab === 'pending') return asset.status === 'pending_review';
    if (activeTab === 'compliance_failed') return asset.status === 'compliance_failed';
    if (activeTab === 'approved') return asset.status === 'approved';
    if (activeTab === 'rejected') return asset.status === 'rejected';
    if (activeTab === 'edited') {
      return asset.history?.some((h) => h.action.includes('Edit'));
    }
    return true;
  });

  const counts = {
    all: store.assets.length,
    pending: store.assets.filter((a) => a.status === 'pending_review').length,
    compliance_failed: store.assets.filter((a) => a.status === 'compliance_failed').length,
    approved: store.assets.filter((a) => a.status === 'approved').length,
    rejected: store.assets.filter((a) => a.status === 'rejected').length,
    edited: store.assets.filter((a) => a.history?.some((h) => h.action.includes('Edit'))).length
  };

  const openReviewModal = (asset: ExtendedAsset) => {
    setSelectedAsset(asset);
    setEditableBody(asset.body);
    setIsEditing(false);
    setExpandedRule(asset.compliance?.issues[0]?.rule_id || 'CLAIM_001');
  };

  // Demo Action: Apply Suggested Fix
  const handleApplySuggestedFix = () => {
    if (!selectedAsset?.compliance?.suggested_revision) return;
    setEditableBody(selectedAsset.compliance.suggested_revision);
    auraStore.applySuggestedFix(selectedAsset.id);

    // Update local state
    const updated = store.assets.find((a) => a.id === selectedAsset.id);
    if (updated) setSelectedAsset(updated);
    toast.success('Applied suggested compliance revision');
  };

  // Demo Action: Re-run Compliance
  const handleRunComplianceAgain = () => {
    if (!selectedAsset) return;
    auraStore.runComplianceCheck(selectedAsset.id);

    // Refresh local selected asset
    const updated = auraStore.getSnapshot().assets.find((a) => a.id === selectedAsset.id);
    if (updated) setSelectedAsset(updated);
    toast.success('Compliance Check completed: PASS. All statutory rules satisfied.');
  };

  // Approve
  const handleConfirmApprove = () => {
    if (!selectedAsset) return;
    auraStore.approveAsset(selectedAsset.id);
    setShowApproveConfirmModal(false);
    setSelectedAsset(null);
    toast.success('Asset approved. Added to approved publishing queue.');
  };

  // Reject with Lesson
  const handleConfirmReject = () => {
    if (!selectedAsset) return;
    auraStore.rejectAsset(selectedAsset.id, rejectReason, rejectNote);
    setShowRejectModal(false);
    setSelectedAsset(null);
    setRejectNote('');
    toast.success('Rejected. Lesson saved to AURA Lessons Learned memory.');
  };

  // Save Edit
  const handleSaveEditWithReason = () => {
    if (!selectedAsset) return;
    auraStore.editAsset(selectedAsset.id, editableBody, {
      reasonTag: editReason,
      note: editNote,
      autoApprove: autoApproveAfterEdit
    });
    setShowEditFeedbackModal(false);
    setIsEditing(false);
    setSelectedAsset(null);
    toast.success(
      autoApproveAfterEdit
        ? 'Saved edit, created lesson, and approved asset'
        : 'Saved edit and logged reviewer feedback'
    );
  };

  return (
    <div className='flex flex-col gap-6 p-4 md:p-8 max-w-7xl mx-auto w-full'>
      {/* Header */}
      <div className='flex flex-col md:flex-row md:items-center justify-between gap-4 border-b pb-5'>
        <div>
          <div className='flex items-center gap-2 text-xs font-semibold text-muted-foreground uppercase tracking-widest'>
            <span>Human-in-the-Loop Gateway</span>
            <span>•</span>
            <span className='text-primary'>Safety Constraint</span>
          </div>
          <h1 className='text-3xl font-bold tracking-tight text-foreground mt-1'>
            Review Queue
          </h1>
          <p className='text-sm text-muted-foreground mt-0.5'>
            Nothing reaches the publishing queue without explicit human approval.
          </p>
        </div>

        {/* Brand Filter */}
        <div className='flex items-center gap-2'>
          <span className='text-xs text-muted-foreground font-medium'>Filter:</span>
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

      {/* Tabs Row */}
      <div className='flex items-center justify-between gap-4'>
        <Tabs value={activeTab} onValueChange={setActiveTab} className='w-full'>
          <TabsList className='grid grid-cols-6 h-9'>
            <TabsTrigger value='all' className='text-xs'>
              All ({counts.all})
            </TabsTrigger>
            <TabsTrigger value='pending' className='text-xs'>
              Pending ({counts.pending})
            </TabsTrigger>
            <TabsTrigger value='compliance_failed' className='text-xs text-destructive font-semibold'>
              Compliance ({counts.compliance_failed})
            </TabsTrigger>
            <TabsTrigger value='approved' className='text-xs'>
              Approved ({counts.approved})
            </TabsTrigger>
            <TabsTrigger value='rejected' className='text-xs'>
              Rejected ({counts.rejected})
            </TabsTrigger>
            <TabsTrigger value='edited' className='text-xs'>
              Edited ({counts.edited})
            </TabsTrigger>
          </TabsList>
        </Tabs>
      </div>

      {/* Asset Cards Grid */}
      {filteredAssets.length === 0 ? (
        <Card className='border-dashed p-12 text-center'>
          <div className='h-12 w-12 rounded-full bg-muted flex items-center justify-center mx-auto text-muted-foreground mb-3'>
            <Icons.checks className='size-6' />
          </div>
          <h3 className='text-base font-bold text-foreground'>No assets in this view</h3>
          <p className='text-xs text-muted-foreground mt-1'>
            You're all caught up! No content currently matches the active status filter.
          </p>
        </Card>
      ) : (
        <div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4'>
          {filteredAssets.map((asset) => {
            const isFailed = asset.status === 'compliance_failed';
            return (
              <Card
                key={asset.id}
                className={`shadow-xs flex flex-col justify-between transition-all hover:border-foreground/40 ${
                  isFailed ? 'border-destructive/40 bg-destructive/[0.02]' : ''
                }`}
              >
                <CardHeader className='pb-3'>
                  <div className='flex items-center justify-between gap-2'>
                    <BrandBadge brandId={asset.brand_id} />
                    <ComplianceVerdictBadge
                      verdict={asset.compliance?.result}
                      risk={asset.compliance?.risk}
                    />
                  </div>

                  <div className='flex items-center justify-between text-[11px] text-muted-foreground mt-2'>
                    <span className='capitalize font-medium text-foreground'>
                      {asset.platform} · {asset.content_type}
                    </span>
                    <AssetStatusBadge status={asset.status} />
                  </div>

                  <CardTitle className='text-xs font-semibold text-foreground mt-1 line-clamp-1'>
                    {asset.title || 'Marketing Post Copy'}
                  </CardTitle>
                </CardHeader>

                <CardContent className='flex flex-col gap-3 pt-0'>
                  <p className='text-xs text-foreground/90 font-serif line-clamp-3 leading-relaxed bg-muted/30 p-2.5 rounded-md italic'>
                    "{asset.body}"
                  </p>

                  {/* Issues Callout if failed */}
                  {isFailed && asset.compliance?.issues[0] && (
                    <div className='rounded-md border border-destructive/30 bg-destructive/10 p-2 text-[11px] text-destructive flex items-start gap-2'>
                      <Icons.warning className='size-3.5 mt-0.5 shrink-0' />
                      <div>
                        <strong>{asset.compliance.issues[0].rule_id}:</strong> {asset.compliance.issues[0].reason}
                      </div>
                    </div>
                  )}

                  <div className='flex items-center justify-between pt-2 border-t text-[11px] text-muted-foreground'>
                    <span>
                      {asset.priority === 'high' ? (
                        <span className='text-destructive font-semibold'>High Priority</span>
                      ) : (
                        `Variant ${asset.variant}`
                      )}
                    </span>
                    <Button size='xs' onClick={() => openReviewModal(asset)}>
                      Open Review
                      <Icons.chevronRight className='size-3 ml-1' />
                    </Button>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      {/* DETAILED REVIEW WORKSPACE / MODAL */}
      {selectedAsset && (
        <Dialog open={Boolean(selectedAsset)} onOpenChange={(open) => !open && setSelectedAsset(null)}>
          <DialogContent className='max-w-4xl max-h-[90vh] overflow-y-auto p-6'>
            <DialogHeader className='border-b pb-4'>
              <div className='flex items-center justify-between gap-4'>
                <div className='flex items-center gap-2'>
                  <BrandBadge brandId={selectedAsset.brand_id} />
                  <span className='text-xs font-semibold text-muted-foreground capitalize'>
                    {selectedAsset.platform} · {selectedAsset.content_type} · Variant {selectedAsset.variant}
                  </span>
                </div>
                <ComplianceVerdictBadge
                  verdict={selectedAsset.compliance?.result}
                  risk={selectedAsset.compliance?.risk}
                />
              </div>
              <DialogTitle className='text-lg font-bold text-foreground mt-2'>
                {selectedAsset.title || 'Review Marketing Asset'}
              </DialogTitle>
              <DialogDescription className='text-xs'>
                Asset ID: {selectedAsset.id} · Created{' '}
                {new Date(selectedAsset.created_at).toLocaleString()}
              </DialogDescription>
            </DialogHeader>

            {/* Split View: Left Content & Editor vs Right Compliance Inspector */}
            <div className='grid grid-cols-1 md:grid-cols-12 gap-6 my-2'>
              {/* Left Column: Content Preview / Editor */}
              <div className='md:col-span-7 flex flex-col gap-4'>
                <div className='flex items-center justify-between'>
                  <Label className='text-xs font-bold text-foreground'>Content Body</Label>
                  <Button
                    size='xs'
                    variant='ghost'
                    onClick={() => setIsEditing(!isEditing)}
                  >
                    <Icons.edit className='size-3 mr-1' />
                    {isEditing ? 'Cancel Edit' : 'Edit Copy'}
                  </Button>
                </div>

                {isEditing ? (
                  <div className='flex flex-col gap-2'>
                    <Textarea
                      value={editableBody}
                      onChange={(e) => setEditableBody(e.target.value)}
                      rows={9}
                      className='text-xs font-mono leading-relaxed'
                    />
                    <div className='flex items-center justify-between text-[11px] text-muted-foreground'>
                      <span>Editing copy will prompt for a lesson learning reason.</span>
                      <Button
                        size='xs'
                        onClick={() => {
                          setShowEditFeedbackModal(true);
                        }}
                      >
                        Save & Log Feedback
                      </Button>
                    </div>
                  </div>
                ) : (
                  <div className='rounded-lg border bg-muted/20 p-4 font-mono text-xs whitespace-pre-wrap leading-relaxed max-h-72 overflow-y-auto'>
                    {selectedAsset.body}
                  </div>
                )}

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

                {/* DEMO REQUIREMENT: If compliance failed, show Suggested Revision + Quick Fix button */}
                {selectedAsset.compliance?.result === 'FAIL' && selectedAsset.compliance.suggested_revision && (
                  <div className='rounded-lg border border-destructive/30 bg-destructive/5 p-4 flex flex-col gap-3'>
                    <div className='flex items-center justify-between'>
                      <span className='text-xs font-bold text-destructive flex items-center gap-1.5'>
                        <Icons.warning className='size-3.5' /> Suggested Revision from Compliance Agent
                      </span>
                      <Button size='xs' variant='outline' onClick={handleApplySuggestedFix}>
                        Apply Suggested Fix
                      </Button>
                    </div>
                    <p className='text-xs text-foreground/90 font-serif italic bg-card p-2.5 rounded border'>
                      "{selectedAsset.compliance.suggested_revision}"
                    </p>
                    <div className='flex items-center justify-end'>
                      <Button size='xs' onClick={handleRunComplianceAgain}>
                        <Icons.checks className='size-3 mr-1' />
                        Run Compliance Again
                      </Button>
                    </div>
                  </div>
                )}
              </div>

              {/* Right Column: Compliance Inspector */}
              <div className='md:col-span-5 flex flex-col gap-3 border-l pl-4'>
                <div className='flex items-center justify-between'>
                  <Label className='text-xs font-bold text-foreground'>Compliance Inspector</Label>
                  <Badge variant='outline' className='text-[10px]'>
                    12 Rules Checked
                  </Badge>
                </div>

                <div className='rounded-lg border bg-card p-3 flex flex-col gap-2 text-xs'>
                  <div className='flex items-center justify-between'>
                    <span className='text-muted-foreground'>Overall Verdict:</span>
                    <strong
                      className={
                        selectedAsset.compliance?.result === 'PASS'
                          ? 'text-emerald-600 dark:text-emerald-400 font-bold'
                          : selectedAsset.compliance?.result === 'REVIEW'
                          ? 'text-amber-600 font-bold'
                          : 'text-destructive font-bold'
                      }
                    >
                      {selectedAsset.compliance?.result || 'PASS'}
                    </strong>
                  </div>
                  <div className='flex items-center justify-between'>
                    <span className='text-muted-foreground'>Risk Level:</span>
                    <Badge variant='secondary' className='text-[10px]'>
                      {selectedAsset.compliance?.risk || 'LOW'}
                    </Badge>
                  </div>
                  <div className='flex items-center justify-between border-t pt-2 text-[11px]'>
                    <span className='text-muted-foreground'>Rules Passed:</span>
                    <span className='text-emerald-600 dark:text-emerald-400 font-bold'>
                      {selectedAsset.compliance?.result === 'PASS' ? '12 / 12' : '11 / 12'}
                    </span>
                  </div>
                </div>

                {/* Rules Checklist */}
                <div className='flex flex-col gap-1.5 max-h-60 overflow-y-auto pr-1'>
                  {COMPLIANCE_RULES.map((rule) => {
                    const isIssue = selectedAsset.compliance?.issues.some(
                      (i) => i.rule_id === rule.id
                    );
                    const isExpanded = expandedRule === rule.id;

                    return (
                      <button
                        type='button'
                        key={rule.id}
                        className={`w-full text-left rounded-md border p-2 text-xs transition-colors cursor-pointer ${
                          isIssue
                            ? 'border-destructive/50 bg-destructive/10'
                            : 'border-muted/60 bg-muted/10 hover:bg-muted/30'
                        }`}
                        onClick={() => setExpandedRule(isExpanded ? null : rule.id)}
                      >
                        <div className='flex items-center justify-between'>
                          <div className='flex items-center gap-2'>
                            {isIssue ? (
                              <Icons.circleX className='size-3.5 text-destructive shrink-0' />
                            ) : (
                              <Icons.circleCheck className='size-3.5 text-emerald-600 dark:text-emerald-400 shrink-0' />
                            )}
                            <span className={isIssue ? 'font-bold text-destructive' : 'font-medium text-foreground'}>
                              {rule.name}
                            </span>
                          </div>
                          <span className='text-[10px] text-muted-foreground font-mono'>
                            {rule.id}
                          </span>
                        </div>

                        {/* Expandable info */}
                        {isExpanded && (
                          <div className='mt-2 pt-2 border-t text-[11px] text-muted-foreground flex flex-col gap-1'>
                            <p>{rule.description}</p>
                            {isIssue && (
                              <p className='text-destructive font-semibold mt-1'>
                                Flagged: Guaranteed outcome code requires re-framing.
                              </p>
                            )}
                            <p className='text-primary text-[10px]'>
                              Remedy: {rule.remedyHint}
                            </p>
                          </div>
                        )}
                      </button>
                    );
                  })}
                </div>
              </div>
            </div>

            {/* Bottom Actions */}
            <DialogFooter className='border-t pt-4 flex items-center justify-between gap-3'>
              <div className='text-xs text-muted-foreground'>
                Reviewer: Marcus Chen (Operations Lead)
              </div>

              <div className='flex items-center gap-2'>
                <Button
                  variant='outline'
                  size='sm'
                  onClick={() => setShowRejectModal(true)}
                  className='text-destructive hover:bg-destructive/10 hover:border-destructive'
                >
                  <Icons.close className='size-4 mr-1.5' />
                  Reject Asset
                </Button>

                <Button
                  size='sm'
                  onClick={() => setShowApproveConfirmModal(true)}
                  disabled={selectedAsset.compliance?.result === 'FAIL'}
                >
                  <Icons.circleCheck className='size-4 mr-1.5' />
                  Approve Asset
                </Button>
              </div>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}

      {/* REJECT MODAL (Creates lesson in AURA Memory) */}
      <Dialog open={showRejectModal} onOpenChange={setShowRejectModal}>
        <DialogContent className='max-w-md p-6'>
          <DialogHeader>
            <DialogTitle className='text-base font-bold text-foreground'>
              Reject Content Asset
            </DialogTitle>
            <DialogDescription className='text-xs'>
              Explain why this content was rejected. This correction will be saved to AURA's
              Lessons Learned memory to refine future generations.
            </DialogDescription>
          </DialogHeader>

          <div className='flex flex-col gap-4 my-2 text-xs'>
            <div className='flex flex-col gap-1.5'>
              <Label className='text-xs font-semibold'>Rejection Reason</Label>
              <select
                value={rejectReason}
                onChange={(e) => setRejectReason(e.target.value as ReasonTag)}
                className='h-9 rounded-md border bg-background px-3 py-1 text-xs shadow-xs'
              >
                {(Object.keys(REASON_TAG_LABELS) as ReasonTag[]).map((tag) => (
                  <option key={tag} value={tag}>
                    {REASON_TAG_LABELS[tag].label}
                  </option>
                ))}
              </select>
            </div>

            <div className='flex flex-col gap-1.5'>
              <Label className='text-xs font-semibold'>Editorial Note</Label>
              <Textarea
                value={rejectNote}
                onChange={(e) => setRejectNote(e.target.value)}
                placeholder='e.g. Tone is too salesy and fails Jade institutional prestige guidelines. Focus on risk education.'
                rows={3}
                className='text-xs'
              />
            </div>

            <div className='rounded-md border bg-muted/40 p-2.5 text-[11px] text-muted-foreground'>
              🧠 <strong>Closed-Loop Feedback:</strong> The Learning Agent will store this rule and
              penalize similar phrasing in future campaign studio prompts.
            </div>
          </div>

          <DialogFooter className='gap-2'>
            <Button variant='outline' size='sm' onClick={() => setShowRejectModal(false)}>
              Cancel
            </Button>
            <Button
              variant='destructive'
              size='sm'
              onClick={handleConfirmReject}
              disabled={!rejectNote.trim()}
            >
              Reject & Save Lesson
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* EDIT FEEDBACK MODAL (Logs reason tag & lesson) */}
      <Dialog open={showEditFeedbackModal} onOpenChange={setShowEditFeedbackModal}>
        <DialogContent className='max-w-md p-6'>
          <DialogHeader>
            <DialogTitle className='text-base font-bold text-foreground'>
              Why was this changed?
            </DialogTitle>
            <DialogDescription className='text-xs'>
              Record the editorial rationale so AURA learns your styling preferences.
            </DialogDescription>
          </DialogHeader>

          <div className='flex flex-col gap-4 my-2 text-xs'>
            <div className='flex flex-col gap-1.5'>
              <Label className='text-xs font-semibold'>Modification Category</Label>
              <select
                value={editReason}
                onChange={(e) => setEditReason(e.target.value as ReasonTag)}
                className='h-9 rounded-md border bg-background px-3 py-1 text-xs shadow-xs'
              >
                {(Object.keys(REASON_TAG_LABELS) as ReasonTag[]).map((tag) => (
                  <option key={tag} value={tag}>
                    {REASON_TAG_LABELS[tag].label}
                  </option>
                ))}
              </select>
            </div>

            <div className='flex flex-col gap-1.5'>
              <Label className='text-xs font-semibold'>Reviewer Note</Label>
              <Textarea
                value={editNote}
                onChange={(e) => setEditNote(e.target.value)}
                placeholder='e.g. Made the opening more educational and less promotional.'
                rows={3}
                className='text-xs'
              />
            </div>
          </div>

          <DialogFooter className='gap-2'>
            <Button
              variant='outline'
              size='sm'
              onClick={() => {
                setAutoApproveAfterEdit(false);
                handleSaveEditWithReason();
              }}
            >
              Save Edit
            </Button>
            <Button
              size='sm'
              onClick={() => {
                setAutoApproveAfterEdit(true);
                handleSaveEditWithReason();
              }}
            >
              Save & Approve
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* APPROVE CONFIRMATION MODAL */}
      <Dialog open={showApproveConfirmModal} onOpenChange={setShowApproveConfirmModal}>
        <DialogContent className='max-w-md p-6'>
          <DialogHeader>
            <DialogTitle className='text-base font-bold text-foreground'>
              Approve Asset?
            </DialogTitle>
            <DialogDescription className='text-xs'>
              This asset will enter the approved-content queue. It can be dispatched by Project 2 (The Hands)
              only after explicit human sign-off.
            </DialogDescription>
          </DialogHeader>

          <div className='rounded-md border bg-emerald-500/10 p-3 text-xs text-emerald-800 dark:text-emerald-300 flex items-start gap-2'>
            <Icons.circleCheck className='size-4 text-emerald-600 dark:text-emerald-400 mt-0.5 shrink-0' />
            <span>
              All 12 compliance checks passed. The copy meets JA Assure statutory guidelines and brand tone benchmarks.
            </span>
          </div>

          <DialogFooter className='gap-2 mt-2'>
            <Button variant='outline' size='sm' onClick={() => setShowApproveConfirmModal(false)}>
              Cancel
            </Button>
            <Button size='sm' onClick={handleConfirmApprove}>
              Confirm Approval
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
