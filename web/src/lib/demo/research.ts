import type { BrandId } from '../api/types';

export interface CompetitorIntelItem {
  id: string;
  competitor_name: string;
  target_brand: BrandId;
  detected_change: string;
  timestamp: string;
  impact: 'High' | 'Medium' | 'Low';
  source_url: string;
  opportunity: string;
  suggested_topic: string;
}

export interface EmergingTrend {
  id: string;
  title: string;
  target_brand: BrandId;
  percentage: number;
  direction: 'up' | 'down' | 'steady';
  summary: string;
  why_it_matters: string;
  sources: string[];
  target_audience: string;
  suggested_response: string;
}

export const COMPETITOR_INTEL: CompetitorIntelItem[] = [
  {
    id: 'intel_001',
    competitor_name: 'Example Insurance Group',
    target_brand: 'jade',
    detected_change: 'Published whitepaper on luxury retail smash-and-grab trends in high-street shopping districts.',
    timestamp: '2 days ago',
    impact: 'Medium',
    source_url: 'https://example-insure.com/retail-theft-2026',
    opportunity: 'Create educational Jade content around multi-custody jewellery vaulting and display glass specifications.',
    suggested_topic: 'How luxury jewellers can reduce showroom vulnerability without sacrificing client ambiance'
  },
  {
    id: 'intel_002',
    competitor_name: 'Transit Risk Co.',
    target_brand: 'jaguar',
    detected_change: 'Launched heavy digital ad push promoting basic marine cargo policies for cross-border trucks.',
    timestamp: '1 day ago',
    impact: 'High',
    source_url: 'https://transitrisk.example/crossborder',
    opportunity:
      'Differentiate Jaguar Transit by highlighting automated telemetry tracking, digital seals, and bonded customs corridors that generic marine policies fail to cover.',
    suggested_topic: 'Why generic marine cargo policies fail at ASEAN land customs checkpoints'
  },
  {
    id: 'intel_003',
    competitor_name: 'MedicDefense Alliance',
    target_brand: 'doctorshield',
    detected_change: 'Announced 15% rate hike for private surgical specialists amidst rising tribunal hearing costs.',
    timestamp: '3 days ago',
    impact: 'High',
    source_url: 'https://medicdefense.example/updates',
    opportunity:
      'Educate private practitioners on DoctorShield’s transparent claims-made structures and proactive legal peer defense.',
    suggested_topic: 'Understanding medical defense premiums: What truly drives indemnity stability for surgical practices'
  },
  {
    id: 'intel_004',
    competitor_name: 'ArtGuard International',
    target_brand: 'jade',
    detected_change: 'Updated gallery underwriting terms with strict exclusion clauses for off-premise art fair popups.',
    timestamp: '4 days ago',
    impact: 'Medium',
    source_url: 'https://artguard.example/policy-terms',
    opportunity: 'Position Jade as the flexible, gallery-friendly underwriter offering full nail-to-nail exhibition riders.',
    suggested_topic: 'The fine art fair checklist: Eliminating transit and installation gaps in temporary galleries'
  }
];

export const EMERGING_TRENDS: EmergingTrend[] = [
  {
    id: 'trend_001',
    title: 'Jewellery theft prevention & vault protocols',
    target_brand: 'jade',
    percentage: 82,
    direction: 'up',
    summary: 'Rising discussion among ASEAN luxury retailers around physical vault standards and private salon security.',
    why_it_matters:
      'High-profile boutique robberies in regional shopping capitals have prompted jewellers to re-evaluate after-hours storage and customer viewing protocols.',
    sources: ['ASEAN Retail Security Report 2026', 'Singapore Jewellers Association Bulletin', 'Interpol Luxury Watch Taskforce'],
    target_audience: 'Master Jewellers, Fine Jewellery Store Owners, Private Client Curators',
    suggested_response:
      'Publish an authoritative B2B advisory outlining the 4 physical security layers necessary for institutional jewellers block underwriting approval.'
  },
  {
    id: 'trend_002',
    title: 'Medical malpractice & disciplinary inquiry awareness',
    target_brand: 'doctorshield',
    percentage: 71,
    direction: 'up',
    summary: 'Growing concern among doctors over protracted council hearings and patient communication disputes.',
    why_it_matters:
      'Clinicians report significant stress during disciplinary complaints, often due to unfamiliarity with procedural timelines and inadequate early legal counsel.',
    sources: ['Academy of Medicine Gazette', 'Medical Protection Journal Q3', 'Singapore Medical Forum'],
    target_audience: 'Private Specialists, Clinic Founders, Junior Hospital Consultants',
    suggested_response:
      'Launch a calm, educational carousel addressing the immediate steps a practitioner should take upon receiving notice of inquiry.'
  },
  {
    id: 'trend_003',
    title: 'High-value logistics risk & cross-border freight',
    target_brand: 'jaguar',
    percentage: 58,
    direction: 'up',
    summary: 'Spike in transit delays and pilferage reports along overland ASEAN trade routes.',
    why_it_matters:
      'Supply chain reshoring into Malaysia, Thailand, and Vietnam has overwhelmed secondary border clearance facilities, lengthening transit windows.',
    sources: ['ASEAN Freight Forwarders Council', 'Logistics Risk Monitor', 'Customs Courier Advisory'],
    target_audience: 'Freight Directors, Courier SME Owners, Supply Chain Risk Officers',
    suggested_response:
      'Create tactical operational checklist for fleet managers on digital tamper seal compliance and multi-carrier handoff verifications.'
  },
  {
    id: 'trend_004',
    title: 'AI in insurance underwriting & claim validation',
    target_brand: 'jade',
    percentage: 42,
    direction: 'up',
    summary: 'Industry exploration of automated claim audits and digital appraisal verification.',
    why_it_matters:
      'Insured parties demand faster claim settlement but worry about robotic denials in specialized high-value categories.',
    sources: ['InsurTech Asia Briefing', 'MAS Fintech Innovation Insights'],
    target_audience: 'Enterprise Risk Managers, Luxury Estate Planners',
    suggested_response:
      'Demonstrate how human expertise augmented by machine precision delivers the optimal balance of speed and personalized evaluation.'
  }
];
