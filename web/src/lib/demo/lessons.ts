import type { Lesson, ReasonTag } from '../api/types';

export interface ExtendedLesson extends Lesson {
  used_count: number;
  impact: string;
  title: string;
}

export const INITIAL_LESSONS: ExtendedLesson[] = [
  {
    id: 'lesson_001',
    title: 'Educational Framing over Direct Selling',
    brand_id: 'jade',
    platform: 'linkedin',
    reason_tag: 'TOO_SALESY',
    note: 'Use educational framing instead of direct product promotion.',
    original_body: 'Looking for insurance? Protect your diamonds with Jade now! Get covered today.',
    edited_body:
      'High-value stones require precision underwriting. Here is how specialist jewellers structure their inventory risk before peak exhibition seasons.',
    used_count: 7,
    impact: 'Reduced rejection rate by 14% on Jade LinkedIn assets',
    created_at: '2026-09-18T10:24:00Z'
  },
  {
    id: 'lesson_002',
    title: 'Avoid Absolute Council Immunity Claims',
    brand_id: 'doctorshield',
    platform: 'instagram',
    reason_tag: 'UNSUPPORTED_CLAIM',
    note: 'Avoid absolute medical outcomes or claims of lawsuit immunity. Highlight peer guidance instead.',
    original_body: 'DoctorShield ensures you never face a patient complaint or disciplinary tribunal.',
    edited_body:
      'When facing clinical inquiries, having experienced medico-legal counsel by your side provides reassurance and clarity.',
    used_count: 12,
    impact: 'Zero compliance flags on Instagram this month',
    created_at: '2026-09-19T14:15:00Z'
  },
  {
    id: 'lesson_003',
    title: 'Consultative B2B CTA for Freight Handlers',
    brand_id: 'jaguar',
    platform: 'linkedin',
    reason_tag: 'WRONG_CTA',
    note: 'Replace generic "Sign up" buttons with "Consult logistics risk desk". Logistics directors need underwriting consults, not instant carts.',
    original_body: 'Sign up for transit cover today and secure your parcels in 5 minutes.',
    edited_body:
      'Request a bonded transit corridor risk assessment with our ASEAN logistics underwriters.',
    used_count: 9,
    impact: '+18% click-through on B2B logistics leads',
    created_at: '2026-09-20T08:30:00Z'
  },
  {
    id: 'lesson_004',
    title: 'Institutional Discretion in Art Valuation',
    brand_id: 'jade',
    platform: 'blog',
    reason_tag: 'WRONG_BRAND_VOICE',
    note: 'Tone must reflect private bank discretion, not sensational retail insurance.',
    original_body: 'Top 5 crazy vault heists and why you need cover right now!',
    edited_body:
      'Structural vulnerability in private vault environments: An analysis of multi-custody safeguards and dual-authentication protocols.',
    used_count: 5,
    impact: 'High editorial benchmark maintained across gallery partner network',
    created_at: '2026-09-21T02:00:00Z'
  }
];

export const REASON_TAG_LABELS: Record<ReasonTag, { label: string; description: string }> = {
  TOO_SALESY: {
    label: 'Too Salesy',
    description: 'Tone is promotional, aggressive, or sounds like retail consumer advertising.'
  },
  WRONG_CTA: {
    label: 'Wrong Call-to-Action',
    description: 'CTA is mismatched with the target audience stage or brand tone.'
  },
  UNSUPPORTED_CLAIM: {
    label: 'Unsupported Claim',
    description: 'Statement makes unsubstantiated assertions, guarantees, or factual leaps.'
  },
  WRONG_BRAND_VOICE: {
    label: 'Off Brand Voice',
    description: 'Violates core brand identity (e.g. Jade missing elegance, DoctorShield missing empathy).'
  },
  BAD_LOCALIZATION: {
    label: 'Bad Localization',
    description: 'Inaccurate regional nuances, phrasing, or jurisdictional mismatch.'
  },
  OTHER: {
    label: 'Other Modification',
    description: 'Structural formatting, typographical adjustment, or factual clarification.'
  }
};
