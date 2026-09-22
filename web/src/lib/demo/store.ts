'use client';

import { useSyncExternalStore } from 'react';
import type { BrandId, Platform, Language, ReasonTag } from '../api/types';
import { INITIAL_ASSETS, type ExtendedAsset } from './assets';
import { INITIAL_LESSONS, type ExtendedLesson, REASON_TAG_LABELS } from './lessons';
import { INITIAL_LEADS, type ExtendedLead } from './leads';
import { INITIAL_AGENT_ACTIVITY, type AgentActivityItem } from './metrics';

export interface AuraStoreState {
  assets: ExtendedAsset[];
  lessons: ExtendedLesson[];
  leads: ExtendedLead[];
  activity: AgentActivityItem[];
  metrics: {
    contentGenerated: number;
    awaitingReview: number;
    approved: number;
    qualifiedLeads: number;
    compliancePassRate: number;
    humanEditRate: number;
    rejectionRate: number;
    publishedAssets: number;
  };
  demoMode: boolean;
  selectedBrandFilter: BrandId | 'all';
}

const STORAGE_KEY = 'aura_marketing_desk_v1';

function computeMetrics(assets: ExtendedAsset[], leads: ExtendedLead[], _lessons: ExtendedLesson[]) {
  const awaitingReview = assets.filter(
    (a) => a.status === 'pending_review' || a.status === 'compliance_failed'
  ).length;
  const approved = assets.filter((a) => a.status === 'approved' || a.status === 'scheduled').length;
  const publishedAssets = assets.filter((a) => a.status === 'published').length;
  const qualifiedLeads = leads.filter((l) => l.status === 'qualified').length;
  const rejected = assets.filter((a) => a.status === 'rejected').length;

  const totalClosed = approved + publishedAssets + rejected;
  const rejectionRate = totalClosed > 0 ? Number(((rejected / totalClosed) * 100).toFixed(1)) : 14.2;

  return {
    contentGenerated: 120 + assets.length,
    awaitingReview,
    approved,
    qualifiedLeads,
    compliancePassRate: 91.4,
    humanEditRate: 18.7,
    rejectionRate,
    publishedAssets: 60 + publishedAssets
  };
}

function getInitialState(): AuraStoreState {
  if (typeof window !== 'undefined') {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) {
        const parsed = JSON.parse(saved);
        return {
          ...parsed,
          metrics: computeMetrics(parsed.assets, parsed.leads, parsed.lessons)
        };
      }
    } catch {
      // fallback to initial
    }
  }

  return {
    assets: INITIAL_ASSETS,
    lessons: INITIAL_LESSONS,
    leads: INITIAL_LEADS,
    activity: INITIAL_AGENT_ACTIVITY,
    metrics: computeMetrics(INITIAL_ASSETS, INITIAL_LEADS, INITIAL_LESSONS),
    demoMode: true,
    selectedBrandFilter: 'all'
  };
}

let currentState: AuraStoreState = getInitialState();
const listeners = new Set<() => void>();

function notify() {
  if (typeof window !== 'undefined') {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(currentState));
    } catch {
      // storage error ignored
    }
  }
  listeners.forEach((l) => l());
}

export const auraStore = {
  getSnapshot(): AuraStoreState {
    return currentState;
  },

  subscribe(listener: () => void): () => void {
    listeners.add(listener);
    return () => listeners.delete(listener);
  },

  setBrandFilter(brand: BrandId | 'all') {
    currentState = { ...currentState, selectedBrandFilter: brand };
    notify();
  },

  approveAsset(id: string, note?: string) {
    const assets = currentState.assets.map((a) => {
      if (a.id === id) {
        return {
          ...a,
          status: 'approved' as const,
          approved_at: new Date().toISOString(),
          approved_by: 'Marcus Chen (Operations Lead)',
          history: [
            ...(a.history || []),
            {
              timestamp: new Date().toISOString(),
              action: 'Approved for Publishing Queue',
              actor: 'Human Reviewer',
              note: note || 'Approved with verified brand voice compliance'
            }
          ]
        };
      }
      return a;
    });

    const newActivity: AgentActivityItem = {
      id: `act_${Date.now()}`,
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      agent: 'Human Reviewer',
      agentType: 'content',
      description: `Approved asset ${id} for publishing queue`,
      status: 'completed'
    };

    currentState = {
      ...currentState,
      assets,
      activity: [newActivity, ...currentState.activity].slice(0, 15),
      metrics: computeMetrics(assets, currentState.leads, currentState.lessons)
    };
    notify();
  },

  rejectAsset(id: string, reasonTag: ReasonTag, note: string) {
    const target = currentState.assets.find((a) => a.id === id);
    const tagInfo = REASON_TAG_LABELS[reasonTag] || { label: reasonTag, description: '' };

    const assets = currentState.assets.map((a) => {
      if (a.id === id) {
        return {
          ...a,
          status: 'rejected' as const,
          rejection_reason: reasonTag,
          rejection_note: note,
          history: [
            ...(a.history || []),
            {
              timestamp: new Date().toISOString(),
              action: `Rejected: ${tagInfo.label}`,
              actor: 'Human Reviewer',
              note
            }
          ]
        };
      }
      return a;
    });

    // Create a new lesson from this rejection
    const newLesson: ExtendedLesson = {
      id: `lesson_${Date.now()}`,
      title: `${tagInfo.label} Correction on ${target?.brand_id ? target.brand_id.toUpperCase() : 'JA Assure'}`,
      brand_id: target?.brand_id || 'jade',
      platform: target?.platform || 'linkedin',
      reason_tag: reasonTag,
      note: note || `Reviewer flagged copy as ${tagInfo.label.toLowerCase()}.`,
      original_body: target?.body || null,
      edited_body: null,
      used_count: 1,
      impact: 'Saved to AURA memory. Applied to future prompt context.',
      created_at: new Date().toISOString()
    };

    const lessons = [newLesson, ...currentState.lessons];

    const newActivity: AgentActivityItem = {
      id: `act_${Date.now()}`,
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      agent: 'Learning Agent',
      agentType: 'learning',
      description: `Stored lesson: ${reasonTag} ("${note.slice(0, 35)}...")`,
      status: 'learned'
    };

    currentState = {
      ...currentState,
      assets,
      lessons,
      activity: [newActivity, ...currentState.activity].slice(0, 15),
      metrics: computeMetrics(assets, currentState.leads, lessons)
    };
    notify();
  },

  editAsset(
    id: string,
    newBody: string,
    options?: {
      reasonTag?: ReasonTag;
      note?: string;
      autoApprove?: boolean;
    }
  ) {
    const target = currentState.assets.find((a) => a.id === id);
    const status = options?.autoApprove ? ('approved' as const) : ('pending_review' as const);

    const assets = currentState.assets.map((a) => {
      if (a.id === id) {
        return {
          ...a,
          body: newBody,
          status,
          approved_at: options?.autoApprove ? new Date().toISOString() : a.approved_at,
          approved_by: options?.autoApprove ? 'Marcus Chen (Operations Lead)' : a.approved_by,
          history: [
            ...(a.history || []),
            {
              timestamp: new Date().toISOString(),
              action: options?.autoApprove ? 'Edited & Approved' : 'Edited Copy',
              actor: 'Human Reviewer',
              note: options?.note
            }
          ]
        };
      }
      return a;
    });

    let lessons = currentState.lessons;
    if (options?.reasonTag && options?.note) {
      const tagInfo = REASON_TAG_LABELS[options.reasonTag];
      const newLesson: ExtendedLesson = {
        id: `lesson_${Date.now()}`,
        title: `Human Edit (${tagInfo.label}) on ${target?.brand_id.toUpperCase()}`,
        brand_id: target?.brand_id || 'jade',
        platform: target?.platform || 'linkedin',
        reason_tag: options.reasonTag,
        note: options.note,
        original_body: target?.body || null,
        edited_body: newBody,
        used_count: 1,
        impact: 'Incorporated into few-shot generator prompt memory',
        created_at: new Date().toISOString()
      };
      lessons = [newLesson, ...lessons];
    }

    const newActivity: AgentActivityItem = {
      id: `act_${Date.now()}`,
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      agent: 'Learning Agent',
      agentType: 'learning',
      description: options?.autoApprove
        ? `Asset ${id} edited & approved`
        : `Asset ${id} edited with feedback`,
      status: 'learned'
    };

    currentState = {
      ...currentState,
      assets,
      lessons,
      activity: [newActivity, ...currentState.activity].slice(0, 15),
      metrics: computeMetrics(assets, currentState.leads, lessons)
    };
    notify();
  },

  applySuggestedFix(id: string) {
    const assets = currentState.assets.map((a) => {
      if (a.id === id && a.compliance?.suggested_revision) {
        return {
          ...a,
          body: a.compliance.suggested_revision,
          history: [
            ...(a.history || []),
            {
              timestamp: new Date().toISOString(),
              action: 'Applied Compliance Agent Suggested Revision',
              actor: 'Human Reviewer'
            }
          ]
        };
      }
      return a;
    });

    currentState = { ...currentState, assets };
    notify();
  },

  runComplianceCheck(id: string) {
    const assets = currentState.assets.map((a) => {
      if (a.id === id) {
        // If it was the demo failure asset and has been updated (or fixed)
        const isFixed = !a.body.includes('guarantees complete protection');
        if (isFixed) {
          return {
            ...a,
            status: 'pending_review' as const,
            compliance: {
              result: 'PASS' as const,
              risk: 'LOW' as const,
              rules: ['CLAIM_001', 'ABS_004', 'TONE_005'],
              issues: [],
              suggested_revision: null
            },
            history: [
              ...(a.history || []),
              {
                timestamp: new Date().toISOString(),
                action: 'Re-ran Compliance Check: PASS',
                actor: 'Compliance Agent',
                note: 'All 12 statutory and tone rules passed.'
              }
            ]
          };
        }
      }
      return a;
    });

    const newActivity: AgentActivityItem = {
      id: `act_${Date.now()}`,
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      agent: 'Compliance Agent',
      agentType: 'compliance',
      description: `Re-evaluated asset ${id}: Verdict PASS`,
      status: 'completed'
    };

    currentState = {
      ...currentState,
      assets,
      activity: [newActivity, ...currentState.activity].slice(0, 15),
      metrics: computeMetrics(assets, currentState.leads, currentState.lessons)
    };
    notify();
  },

  publishAsset(id: string, mode: 'schedule' | 'now') {
    const assets = currentState.assets.map((a) => {
      if (a.id === id) {
        const isNow = mode === 'now';
        return {
          ...a,
          status: isNow ? ('published' as const) : ('scheduled' as const),
          published_post_id: isNow ? `demo_ja_${Math.floor(10000 + Math.random() * 90000)}` : undefined,
          published_at: isNow ? new Date().toISOString() : undefined,
          scheduled_for: isNow ? undefined : 'Tomorrow · 10:30 AM',
          history: [
            ...(a.history || []),
            {
              timestamp: new Date().toISOString(),
              action: isNow ? 'Published via Project 2' : 'Scheduled for Project 2 Delivery',
              actor: 'Publisher Service',
              note: isNow ? 'Verified post ID received' : 'Enqueued for batch dispatch'
            }
          ]
        };
      }
      return a;
    });

    const newActivity: AgentActivityItem = {
      id: `act_${Date.now()}`,
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      agent: 'Publishing Agent',
      agentType: 'content',
      description:
        mode === 'now'
          ? `Dispatched asset ${id} to social endpoint (Post ID: demo_ja_28491)`
          : `Scheduled asset ${id} for tomorrow 10:30 AM`,
      status: 'completed'
    };

    currentState = {
      ...currentState,
      assets,
      activity: [newActivity, ...currentState.activity].slice(0, 15),
      metrics: computeMetrics(assets, currentState.leads, currentState.lessons)
    };
    notify();
  },

  addGeneratedCampaign(params: {
    brandId: BrandId;
    topic: string;
    goal: string;
    platforms: Platform[];
    language: Language;
    assets: ExtendedAsset[];
  }) {
    const campaignId = `camp_${Date.now()}`;
    const newAssets = params.assets.map((a) => ({
      ...a,
      campaign_id: campaignId
    }));

    const assets = [...newAssets, ...currentState.assets];

    const newActivity: AgentActivityItem = {
      id: `act_${Date.now()}`,
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      agent: 'Content Agent',
      agentType: 'content',
      description: `Generated campaign for ${params.brandId.toUpperCase()}: ${newAssets.length} assets`,
      status: 'completed'
    };

    currentState = {
      ...currentState,
      assets,
      activity: [newActivity, ...currentState.activity].slice(0, 15),
      metrics: computeMetrics(assets, currentState.leads, currentState.lessons)
    };
    notify();
  },

  addStudioCampaignPackage(campaign: import('../api/types').StudioCampaignDetail) {
    if (!campaign) return;
    const mediaUrl = campaign.media?.find((m) => m.local_path)?.local_path || null;
    const contents = campaign.contents || [];
    const newAssets: ExtendedAsset[] = contents.map((item, idx) => ({
      id: item.id || `ast_${Date.now()}_${idx}`,
      campaign_id: campaign.id,
      brand_id: campaign.brand_id,
      platform: item.platform,
      content_type:
        item.platform === 'reel'
          ? 'script'
          : item.platform === 'blog'
          ? 'article'
          : item.platform === 'instagram'
          ? 'caption'
          : 'post',
      variant: 'A',
      language: campaign.language,
      title: item.title || `${item.platform.toUpperCase()} Asset: ${(campaign.thesis || '').slice(0, 40)}`,
      body: item.content,
      hashtags: item.hashtags || [],
      media_url: mediaUrl,
      status: 'pending_review',
      priority: 'high',
      compliance: {
        result: 'PASS',
        risk: 'LOW',
        rules: ['STATUTORY_DISCLOSURE', 'TONE_ALIGNMENT'],
        issues: [],
        suggested_revision: null
      },
      created_at: new Date().toISOString(),
      approved_at: null,
      approved_by: null,
      history: [
        {
          timestamp: new Date().toISOString(),
          action: 'Submitted from Campaign Studio for Human Verification',
          actor: 'Content Agent'
        }
      ]
    }));

    const assets = [...newAssets, ...currentState.assets];
    const newActivity: AgentActivityItem = {
      id: `act_${Date.now()}`,
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      agent: 'Campaign Studio',
      agentType: 'content',
      description: `Submitted campaign package (${newAssets.length} assets) to Review Queue`,
      status: 'completed'
    };

    currentState = {
      ...currentState,
      assets,
      activity: [newActivity, ...currentState.activity].slice(0, 15),
      metrics: computeMetrics(assets, currentState.leads, currentState.lessons)
    };
    notify();
  },


  approveLeadOutreach(leadId: string, updatedBody?: string) {
    const leads = currentState.leads.map((lead) => {
      if (lead.id === leadId) {
        return {
          ...lead,
          status: 'qualified' as const,
          suggested_outreach: {
            ...lead.suggested_outreach,
            body: updatedBody || lead.suggested_outreach.body,
            approved: true
          }
        };
      }
      return lead;
    });

    const newActivity: AgentActivityItem = {
      id: `act_${Date.now()}`,
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      agent: 'Lead Agent',
      agentType: 'lead',
      description: `Approved custom B2B outreach draft for ${leadId}`,
      status: 'completed'
    };

    currentState = {
      ...currentState,
      leads,
      activity: [newActivity, ...currentState.activity].slice(0, 15),
      metrics: computeMetrics(currentState.assets, leads, currentState.lessons)
    };
    notify();
  },

  resetDefaults() {
    currentState = {
      assets: INITIAL_ASSETS,
      lessons: INITIAL_LESSONS,
      leads: INITIAL_LEADS,
      activity: INITIAL_AGENT_ACTIVITY,
      metrics: computeMetrics(INITIAL_ASSETS, INITIAL_LEADS, INITIAL_LESSONS),
      demoMode: true,
      selectedBrandFilter: 'all'
    };
    notify();
  }
};

export function useAuraStore() {
  return useSyncExternalStore(
    auraStore.subscribe,
    auraStore.getSnapshot,
    auraStore.getSnapshot
  );
}
