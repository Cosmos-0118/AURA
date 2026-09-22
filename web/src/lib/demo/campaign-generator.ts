import type { BrandId, Platform, Language } from '../api/types';
import type { ExtendedAsset } from './assets';
import { DEMO_BRANDS } from './brands';

export interface GenerationInput {
  brandId: BrandId;
  topic: string;
  goal: string;
  platforms: Platform[];
  language: Language;
  tone: string;
}

export function generateCampaignAssets(input: GenerationInput): ExtendedAsset[] {
  const brand = DEMO_BRANDS[input.brandId];
  const now = new Date();
  const assets: ExtendedAsset[] = [];

  input.platforms.forEach((platform, idx) => {
    if (platform === 'linkedin') {
      // Variant A
      assets.push({
        id: `gen_${input.brandId}_li_a_${Date.now()}`,
        campaign_id: null,
        brand_id: input.brandId,
        platform: 'linkedin',
        content_type: 'post',
        variant: 'A',
        language: input.language,
        priority: 'high',
        title: `${input.topic} — Executive Perspective`,
        body: `Protecting high-value operations begins long before a loss event occurs.\n\nIn our latest assessment regarding "${input.topic}", our underwriting desk analyzed historical vulnerability vectors across regional hubs.\n\nKey takeaways for leadership:\n1. Audit custody handoffs before scaling volume.\n2. Ensure policy exclusions do not conflict with active operational workflows.\n3. Institutional insurance is not an expense—it is a balance-sheet stabilization strategy.\n\nHow is your organization addressing this in Q4? Let's discuss with our specialist desk.`,
        hashtags: [`#${brand.name.replace(/\s+/g, '')}`, '#RiskManagement', '#B2BOperations', '#JAAssure'],
        media_url: null,
        status: 'pending_review',
        compliance: {
          result: 'PASS',
          risk: 'LOW',
          rules: ['CLAIM_001', 'TONE_005', 'CTA_006'],
          issues: [],
          suggested_revision: null
        },
        created_at: new Date(now.getTime() - idx * 1000).toISOString(),
        approved_at: null,
        approved_by: null
      });

      // Variant B
      assets.push({
        id: `gen_${input.brandId}_li_b_${Date.now()}`,
        campaign_id: null,
        brand_id: input.brandId,
        platform: 'linkedin',
        content_type: 'post',
        variant: 'B',
        language: input.language,
        priority: 'medium',
        title: `${input.topic} — Operational Audit`,
        body: `Every specialized enterprise carries risk. The question is whether that risk has been properly understood and systematically mitigated.\n\nWhen exploring "${input.topic}", many leaders realize conventional coverage leaves substantial blind spots.\n\n${brand.name} by JA Assure partners directly with businesses to provide bespoke indemnity built for real-world scenarios.\n\nSpeak with our underwriters for an institutional review.`,
        hashtags: [`#${brand.name.replace(/\s+/g, '')}`, '#EnterpriseProtection', '#Underwriting'],
        media_url: null,
        status: 'pending_review',
        compliance: {
          result: 'PASS',
          risk: 'LOW',
          rules: ['CLAIM_001', 'TONE_005', 'PROD_007'],
          issues: [],
          suggested_revision: null
        },
        created_at: new Date(now.getTime() - (idx * 1000 + 500)).toISOString(),
        approved_at: null,
        approved_by: null
      });
    }

    if (platform === 'instagram') {
      assets.push({
        id: `gen_${input.brandId}_ig_${Date.now()}`,
        campaign_id: null,
        brand_id: input.brandId,
        platform: 'instagram',
        content_type: 'caption',
        variant: 'A',
        language: input.language,
        priority: 'medium',
        title: `Visual Brief: ${input.topic}`,
        body: `Behind every seamless operation lies structured risk prevention.\n\nSwipe through our guide to "${input.topic}" tailored for ${brand.audience.split(',')[0]}.\n\n• Slide 1: The core vulnerability most teams overlook\n• Slide 2: Practical verification protocols\n• Slide 3: How ${brand.name} provides dedicated backing\n\nLink in bio to read the full underwriting memo.`,
        hashtags: [`#${brand.name.replace(/\s+/g, '')}`, '#RiskPrevention', '#ProfessionalInsight'],
        media_url: null,
        status: 'pending_review',
        compliance: {
          result: 'PASS',
          risk: 'LOW',
          rules: ['TONE_005', 'CTA_006'],
          issues: [],
          suggested_revision: null
        },
        created_at: new Date(now.getTime() - idx * 2000).toISOString(),
        approved_at: null,
        approved_by: null
      });
    }

    if (platform === 'x') {
      assets.push({
        id: `gen_${input.brandId}_x_${Date.now()}`,
        campaign_id: null,
        brand_id: input.brandId,
        platform: 'x',
        content_type: 'post',
        variant: 'A',
        language: input.language,
        priority: 'low',
        title: `Quick Take: ${input.topic}`,
        body: `1/3 When evaluating "${input.topic}", conventional solutions focus on post-loss claims rather than active pre-loss controls.\n\n2/3 ${brand.name} structures underwriting around your operational reality.\n\n3/3 Learn more about proactive risk mitigation: jaassure.com/${input.brandId}`,
        hashtags: [`#${brand.name.replace(/\s+/g, '')}`, '#RiskManagement'],
        media_url: null,
        status: 'pending_review',
        compliance: {
          result: 'PASS',
          risk: 'LOW',
          rules: ['CLAIM_001', 'TONE_005'],
          issues: [],
          suggested_revision: null
        },
        created_at: new Date(now.getTime() - idx * 3000).toISOString(),
        approved_at: null,
        approved_by: null
      });
    }

    if (platform === 'reel') {
      assets.push({
        id: `gen_${input.brandId}_reel_${Date.now()}`,
        campaign_id: null,
        brand_id: input.brandId,
        platform: 'reel',
        content_type: 'script',
        variant: 'A',
        language: input.language,
        priority: 'medium',
        title: `Short-form Script: ${input.topic}`,
        body: `[SCRIPT & VOICEOVER BRIEF]\n\nDuration: 45s\nAspect Ratio: 9:16 (Vertical Video)\n\n[00:00-00:05] HOOK:\n"Most businesses only discover their insurance policy gaps after the incident has already occurred."\n\n[00:05-00:20] THE PROBLEM:\nVisual: Macro shot of secure facility / clinical environment / transit checkpoint.\nVO: "When dealing with ${input.topic}, standard commercial policies carry hidden exclusions around custody transfer and sub-limits."\n\n[00:20-00:35] THE SOLUTION:\nVO: "${brand.name} by JA Assure was designed specifically for ${brand.audience.split(',')[0]}—bringing underwriter precision directly into your workflow."\n\n[00:35-00:45] CALL TO ACTION:\nOn-screen text: "Audit Your Exposure with JA Assure specialists. Link below."`,
        hashtags: [`#${brand.name.replace(/\s+/g, '')}`, '#Operations', '#RiskBrief'],
        media_url: null,
        status: 'pending_review',
        compliance: {
          result: 'PASS',
          risk: 'LOW',
          rules: ['CLAIM_001', 'TONE_005', 'CTA_006'],
          issues: [],
          suggested_revision: null
        },
        created_at: new Date(now.getTime() - idx * 4000).toISOString(),
        approved_at: null,
        approved_by: null
      });
    }

    if (platform === 'blog') {
      assets.push({
        id: `gen_${input.brandId}_blog_${Date.now()}`,
        campaign_id: null,
        brand_id: input.brandId,
        platform: 'blog',
        content_type: 'article',
        variant: 'A',
        language: input.language,
        priority: 'low',
        title: `In-Depth Guide: ${input.topic}`,
        body: `Executive Summary: Why ${input.topic} Demands Institutional Governance\n\nIn modern Southeast Asian commerce, specialized operations cannot rely on off-the-shelf coverage. Whether dealing with high-value retail, clinical integrity, or bonded cargo corridors, risk parameters have evolved rapidly.\n\nSection 1: The Anatomy of Operational Vulnerability\nHistorical loss analysis indicates that 60% of claim disputes stem from mismatched policy schedules. When policies do not accurately reflect day-to-day handling, operators bear unforeseen exposure.\n\nSection 2: The ${brand.name} Framework\nAt JA Assure, our approach combines specialized underwriting with proactive risk mitigation advisory, ensuring that your balance sheet remains insulated against volatility.\n\nConclusion: Speak with our underwriting committee for a tailored exposure review.`,
        hashtags: [`#${brand.name.replace(/\s+/g, '')}`, '#ThoughtLeadership', '#Whitepaper'],
        media_url: null,
        status: 'pending_review',
        compliance: {
          result: 'PASS',
          risk: 'LOW',
          rules: ['CLAIM_001', 'TONE_005', 'PROD_007'],
          issues: [],
          suggested_revision: null
        },
        created_at: new Date(now.getTime() - idx * 5000).toISOString(),
        approved_at: null,
        approved_by: null
      });
    }
  });

  return assets;
}
