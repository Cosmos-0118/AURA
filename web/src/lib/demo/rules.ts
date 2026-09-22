export interface ComplianceRuleDefinition {
  id: string;
  name: string;
  category: 'claims' | 'brand' | 'legal' | 'tone';
  description: string;
  riskLevel: 'LOW' | 'MEDIUM' | 'HIGH';
  remedyHint: string;
}

export const COMPLIANCE_RULES: ComplianceRuleDefinition[] = [
  {
    id: 'CLAIM_001',
    name: 'No guaranteed outcomes',
    category: 'claims',
    description: 'Prohibits promising 100% loss prevention, absolute recovery, or unconditional payout guarantees.',
    riskLevel: 'HIGH',
    remedyHint: 'Frame as risk mitigation and advisory partnership rather than guaranteed protection.'
  },
  {
    id: 'STAT_002',
    name: 'No unsupported statistics',
    category: 'claims',
    description: 'All cited loss statistics, recovery percentages, or crime figures must cite verified industry sources.',
    riskLevel: 'MEDIUM',
    remedyHint: 'Provide source attribution or rephrase to general industry observations.'
  },
  {
    id: 'COMP_003',
    name: 'No misleading competitor comparisons',
    category: 'claims',
    description: 'Cannot name competitors disparagingly or assert qualitative superiority without substantiation.',
    riskLevel: 'MEDIUM',
    remedyHint: 'Focus on JA Assure brand strengths rather than negative competitor comparison.'
  },
  {
    id: 'ABS_004',
    name: 'No absolute protection claims',
    category: 'claims',
    description: 'Words like "bulletproof", "foolproof", "entirely immune", or "complete peace of mind" trigger flags.',
    riskLevel: 'HIGH',
    remedyHint: 'Replace absolute assertions with measured risk management terminology.'
  },
  {
    id: 'TONE_005',
    name: 'Brand tone acceptable',
    category: 'brand',
    description: 'Copy must adhere to specific brand guidelines (e.g. Jade must remain dignified, DoctorShield calm).',
    riskLevel: 'LOW',
    remedyHint: 'Remove aggressive exclamation marks, urgency hype, and clickbait hooks.'
  },
  {
    id: 'CTA_006',
    name: 'CTA acceptable',
    category: 'brand',
    description: 'Call-to-action must be consultative (e.g. "Speak with our specialist") rather than transactional ("Buy Now").',
    riskLevel: 'LOW',
    remedyHint: 'Convert hard sell buttons into advisory consultations.'
  },
  {
    id: 'PROD_007',
    name: 'Product description acceptable',
    category: 'legal',
    description: 'Product names, underwriting classes, and coverage terms must align with official underwriting schedules.',
    riskLevel: 'MEDIUM',
    remedyHint: 'Use verified policy schedule naming conventions.'
  },
  {
    id: 'COV_008',
    name: 'Coverage wording requires review',
    category: 'legal',
    description: 'Exclusions, deductibles, transit clauses, or medical board limitations must not be obscured.',
    riskLevel: 'LOW',
    remedyHint: 'Include standard statutory insurance policy wording note.'
  },
  {
    id: 'PRIV_009',
    name: 'Data privacy & client confidentiality',
    category: 'legal',
    description: 'Never disclose identifiable client case studies, gallery addresses, or vault locations.',
    riskLevel: 'HIGH',
    remedyHint: 'Anonymize client examples and geographical details.'
  },
  {
    id: 'REG_010',
    name: 'Regulatory compliance disclaimer',
    category: 'legal',
    description: 'Assets referencing insurance products must state underwriter identity and regulated entity notices.',
    riskLevel: 'LOW',
    remedyHint: 'Ensure footer includes registered entity disclosure.'
  },
  {
    id: 'JUR_011',
    name: 'Clear ASEAN jurisdiction applicability',
    category: 'legal',
    description: 'Clarifies coverage territories (Singapore, Malaysia, Thailand, Indonesia).',
    riskLevel: 'LOW',
    remedyHint: 'Specify target underwriting market in post disclaimer.'
  },
  {
    id: 'RUN_012',
    name: 'Retroactive & run-off clarity',
    category: 'claims',
    description: 'DoctorShield content referencing medical indemnity must clarify claims-made policy terms.',
    riskLevel: 'MEDIUM',
    remedyHint: 'Add note regarding policy inception dates and retroactive coverage continuity.'
  }
];
