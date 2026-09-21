import type { Brand, BrandId, Platform } from '../api/types';

export interface ExtendedBrand extends Brand {
  tagline: string;
  description: string;
  personality: string[];
  preferred_platforms: Platform[];
  products: string[];
  compliance_considerations: string;
  stats: {
    assets: number;
    approvalRate: number;
    published: number;
  };
}

export const DEMO_BRANDS: Record<BrandId, ExtendedBrand> = {
  jade: {
    id: 'jade',
    name: 'Jade',
    tagline: 'Specialist Jewellery & Fine Art Risk Protection',
    description: 'Premium specialist insurance for jewellery, fine art and other high-value assets.',
    personality: ['Authoritative', 'Premium', 'Specialist', 'Intelligent', 'B2B', 'Risk-aware', 'Never overly salesy'],
    audience: 'Jewellers, fine-art businesses, luxury asset businesses, and high-value asset owners.',
    tone: ['Authoritative', 'Premium', 'Educational'],
    do_list: [
      'Frame risk prevention and business continuity education first',
      'Highlight high-value asset underwriting expertise and specialist care',
      'Use restrained, sophisticated, institutional language',
      'Reference secure vaults, specialist transit, and valuation rigor'
    ],
    dont_list: [
      'Never use aggressive sales hype, urgency counters, or exclamation marks',
      'Never guarantee 100% loss prevention or payout speed without qualifiers',
      'Avoid generic insurance jargon and cheap retail promotional phrasing'
    ],
    preferred_platforms: ['linkedin', 'instagram', 'blog'],
    products: [
      'Bespoke Jewellers Block Cover',
      'Fine Art & Exhibition Indemnity',
      'Private Collection Vault Protection'
    ],
    compliance_considerations:
      'Strict claim wording required under insurance standards. Must never guarantee complete recovery or prevention of bespoke losses.',
    stats: {
      assets: 42,
      approvalRate: 87,
      published: 32
    }
  },
  doctorshield: {
    id: 'doctorshield',
    name: 'DoctorShield',
    tagline: 'Medical Indemnity & Professional Protection',
    description: 'Medical indemnity / professional protection for doctors, clinics, and medical practitioners.',
    personality: ['Reassuring', 'Educational', 'Professional', 'Trustworthy', 'Human', 'Calm'],
    audience: 'Doctors, clinics, medical practitioners, and healthcare businesses.',
    tone: ['Calm', 'Trustworthy', 'Human', 'Educational'],
    do_list: [
      'Focus on doctor well-being, clinical discretion, and peer legal support',
      'Educate on evolving medical council inquiry procedures and complaint mitigation',
      'Maintain empathetic, collegial, and calm professional bedside manner in all copy',
      'Clarify retrospective cover and run-off protection nuances'
    ],
    dont_list: [
      'Never use fear-based marketing, malpractice sensationalism, or lawsuit panic',
      'Never promise immunity from medical council hearings or malpractice claims',
      'Avoid overly technical legalistic threats that heighten clinical anxiety'
    ],
    preferred_platforms: ['linkedin', 'instagram', 'blog'],
    products: [
      'Specialist Medical Malpractice Indemnity',
      'Clinic Entity & Staff Liability',
      'Medico-Legal Inquiry Defence'
    ],
    compliance_considerations:
      'Must adhere strictly to medical ethics and healthcare advertising regulations. Zero medical claims advice.',
    stats: {
      assets: 38,
      approvalRate: 92,
      published: 21
    }
  },
  jaguar: {
    id: 'jaguar',
    name: 'Jaguar Transit',
    tagline: 'Valuables & Cargo in Transit Protection',
    description: 'Insurance and risk protection related to high-value goods and valuables in transit across ASEAN.',
    personality: ['Secure', 'Operational', 'Fast', 'Precise', 'Reliable'],
    audience: 'Couriers, logistics companies, high-value goods businesses, and SMEs.',
    tone: ['Precise', 'Confident', 'Direct', 'Operational'],
    do_list: [
      'Detail precise chain-of-custody, telemetry tracking, and multi-modal transit cover',
      'Address real cross-border customs inspection checkpoints and bonded logistics',
      'Provide concise operational checklists for freight handlers and secure dispatchers',
      'Highlight rapid claim verification via digital tamper seals'
    ],
    dont_list: [
      'Never guarantee zero transit theft or foolproof cargo security',
      'Never make unsupported speed or payout timeframe promises without policy qualifiers',
      'Avoid vague descriptions of carrier liability limits'
    ],
    preferred_platforms: ['linkedin', 'x', 'reel'],
    products: [
      'Armoured & High-Value Transit Shield',
      'Cross-Border Bonded Cargo Cover',
      'Last-Mile Precious Consignment'
    ],
    compliance_considerations:
      'Conforms to regional logistics carriage conventions and bonded transit statutes. Clear boundary between shipper and carrier liability.',
    stats: {
      assets: 27,
      approvalRate: 89,
      published: 10
    }
  }
};

export function getDemoBrandsList(): ExtendedBrand[] {
  return Object.values(DEMO_BRANDS);
}
