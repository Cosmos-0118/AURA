import type { Lead } from '../api/types';

export type LeadStatus = 'qualified' | 'review' | 'contacted' | 'rejected';

export interface ExtendedLead extends Lead {
  industry: string;
  location: string;
  status: LeadStatus;
  employee_count: string;
  estimated_exposure: string;
  reasons: string[];
  suggested_outreach: {
    subject: string;
    body: string;
    recipient_role: string;
    approved: boolean;
  };
}

export const INITIAL_LEADS: ExtendedLead[] = [
  {
    id: 'lead_001',
    brand_id: 'jade',
    name: 'ABC Jewellers',
    industry: 'Jewellery & Luxury Retail',
    country: 'Singapore',
    location: 'Orchard Road, Singapore',
    fit_score: 87,
    status: 'qualified',
    employee_count: '25-50',
    estimated_exposure: 'SGD 18M - 25M',
    why: 'High-value diamond and bespoke gemstone inventory distributed across flagship boutiques in Singapore and Kuala Lumpur.',
    url: 'https://abcjewellers.example.com',
    reasons: [
      'High-value inventory exceeding typical commercial retail thresholds',
      'Multiple regional showroom locations requiring multi-custody underwriting',
      'Active participant in international jewellery exhibitions with transit exposures',
      'Expanding bespoke private commissions with off-site client viewings'
    ],
    suggested_outreach: {
      subject: 'Structuring High-Value Jewellers Block & Transit Risk | Jade by JA Assure',
      recipient_role: 'Managing Director / Head of Security',
      approved: false,
      body: `Hi [Name],\n\nWe noticed ABC Jewellers continues to expand its bespoke gemstone showcase across Orchard Road and Pavilion KL.\n\nAs bespoke inventory values scale, conventional retail insurance often introduces sub-limit constraints on off-premises viewings and multi-custody vault handovers. Jade specializes in custom jewellers block underwriting with full exhibition and transit extensions designed specifically for ASEAN luxury houses.\n\nWould you be open to a brief 15-minute consultation with our specialist jewellery underwriting desk next Tuesday?\n\nWarm regards,\nMarcus Chen\nHigh-Value Asset Underwriting | Jade by JA Assure`
    }
  },
  {
    id: 'lead_002',
    brand_id: 'doctorshield',
    name: 'Prime Medical Clinic Group',
    industry: 'Healthcare & Multi-Disciplinary Clinics',
    country: 'Singapore',
    location: 'Novena & Raffles Place, Singapore',
    fit_score: 91,
    status: 'qualified',
    employee_count: '40-80',
    estimated_exposure: '18 Resident Specialists',
    why: 'Rapidly expanding day-surgery and aesthetic medicine group with multi-specialist clinical liability requirements.',
    url: 'https://primemedical.example.sg',
    reasons: [
      'Multi-disciplinary clinical group introducing higher surgical exposure',
      'Recent addition of tele-consultation channels requiring digital consent governance',
      'Requires retroactive continuity cover across newly onboarded resident specialists',
      'Proactive leadership team seeking risk reduction continuing education'
    ],
    suggested_outreach: {
      subject: 'Comprehensive Medical Indemnity & Group Entity Defense | DoctorShield',
      recipient_role: 'Medical Director / Clinic Operations Lead',
      approved: false,
      body: `Dear Dr. [Name],\n\nCongratulations on the recent launch of Prime Medical's Novena surgical wing.\n\nWith multi-specialist groups, standard individual practitioner policies often leave entity-level and vicarious staff liability exposed during formal inquiries. DoctorShield provides seamless group entity protection combined with dedicated peer-guided legal defense led by senior medical practitioners.\n\nWe would welcome the opportunity to share our clinical risk audit checklist with your practice management team.\n\nWarmly,\nDr. Sarah Lim\nMedical Advisory Lead | DoctorShield by JA Assure`
    }
  },
  {
    id: 'lead_003',
    brand_id: 'jaguar',
    name: 'Swift Logistics ASEAN',
    industry: 'Specialized Cargo & Bonded Freight',
    country: 'Malaysia',
    location: 'Port Klang & Shah Alam, Malaysia',
    fit_score: 78,
    status: 'review',
    employee_count: '150-300',
    estimated_exposure: 'MYR 40M Monthly Bonded Volume',
    why: 'Cross-border bonded freight carrier operating high-frequency Singapore-Malaysia-Thailand land bridge corridors.',
    url: 'https://swiftlogistics-asean.example.my',
    reasons: [
      'High-volume cross-border transit through busy customs bonded corridors',
      'Carrying high-tech electronics, pharmaceuticals, and luxury retail consignments',
      'Seeking digital telemetry-linked cargo warranty to reduce shipper deductibles',
      'Recent route expansion into Eastern Seaboard industrial clusters'
    ],
    suggested_outreach: {
      subject: 'Digital Telemetry & Bonded Transit Risk Shield | Jaguar Transit',
      recipient_role: 'Chief Operating Officer / Fleet Risk Manager',
      approved: false,
      body: `Hi [Name],\n\nOperating daily bonded runs along the North-South Expressway demands precise chain-of-custody documentation—especially at border clearance checkpoints.\n\nJaguar Transit offers automated corridor underwriting integrated with GPS and electronic tamper seals, allowing freight forwarders to provide immediate certificate generation and expedited claim settlement for premium shippers.\n\nLet's connect for 10 minutes to discuss how we can lower your cargo deductible on key ASEAN corridors.\n\nBest regards,\nDaniel Wong\nHead of Logistics Underwriting | Jaguar Transit by JA Assure`
    }
  },
  {
    id: 'lead_004',
    brand_id: 'jade',
    name: 'Aurelia Fine Art Gallery',
    industry: 'Fine Art & Gallery Exhibitions',
    country: 'Singapore',
    location: 'Tanjong Pagar Distripark, Singapore',
    fit_score: 94,
    status: 'qualified',
    employee_count: '10-20',
    estimated_exposure: 'SGD 32M Curated Collection',
    why: 'Premier Southeast Asian contemporary art gallery preparing for upcoming international art fairs in Singapore and Hong Kong.',
    url: 'https://aurelia-art.example.com',
    reasons: [
      'Upcoming multi-million dollar exhibition loans from European private estates',
      'High seasonal vulnerability during international museum transit and art fair installations',
      'Requires institutional nail-to-nail indemnity with zero restoration depreciation deductions'
    ],
    suggested_outreach: {
      subject: 'Nail-to-Nail Fine Art Exhibition Indemnity | Jade Specialist Protection',
      recipient_role: 'Chief Curator / Director of Collections',
      approved: false,
      body: `Dear [Name],\n\nWe have been admiring Aurelia's upcoming modern Southeast Asian retrospective.\n\nAs you coordinate international loans and complex multi-carrier crating, Jade provides comprehensive nail-to-nail coverage including depreciation protection and climate-controlled transit warranties recognized by major institutional lenders worldwide.\n\nWe would be honored to provide an underwriting review for your upcoming fair consignment.\n\nSincerely,\nElena Tan\nFine Art Insurance Specialist | Jade by JA Assure`
    }
  },
  {
    id: 'lead_005',
    brand_id: 'doctorshield',
    name: 'Novena Aesthetic & Dermatology Centre',
    industry: 'Aesthetic Medicine & Dermatology',
    country: 'Singapore',
    location: 'Novena Medical Center, Singapore',
    fit_score: 89,
    status: 'qualified',
    employee_count: '20-35',
    estimated_exposure: '8 Aesthetic Doctors',
    why: 'High procedure volume aesthetic clinic with advanced laser, energy devices, and minimally invasive treatments.',
    url: 'https://novena-aesthetic.example.sg',
    reasons: [
      'Aesthetic and procedural medicine carries elevated patient expectation disputes',
      'Requires tailored consent documentation protocols that satisfy SMC inquiry standards',
      'Strong candidate for proactive medico-legal workshops'
    ],
    suggested_outreach: {
      subject: 'Procedural Indemnity & Medico-Legal Risk Advisory | DoctorShield',
      recipient_role: 'Founder & Medical Director',
      approved: false,
      body: `Dear Dr. [Name],\n\nAesthetic medicine requires a delicate balance between exceptional procedural outcomes and clear patient communication.\n\nDoctorShield's dedicated aesthetic malpractice indemnity includes specialized consent documentation reviews and immediate access to senior legal counsel before minor disputes escalate.\n\nMay we arrange a brief introductory call with our clinical advisory committee?\n\nWith respect,\nDr. Sarah Lim\nDoctorShield by JA Assure`
    }
  },
  {
    id: 'lead_006',
    brand_id: 'jaguar',
    name: 'Apex Precision Freight Services',
    industry: 'Logistics & Secure Express',
    country: 'Thailand',
    location: 'Bangkok / Suvarnabhumi Airport Cargo Zone',
    fit_score: 83,
    status: 'qualified',
    employee_count: '80-120',
    estimated_exposure: 'USD 8M Weekly Air Cargo',
    why: 'High-value air freight consolidation specialist handling electronics, medical devices, and luxury consignments.',
    url: 'https://apex-cargo.example.th',
    reasons: [
      'High-value airport bonded warehouse transfers with short staging windows',
      'Multi-currency coverage requirements across Thai Baht, SGD, and USD',
      'Desires unified automated cargo certification API'
    ],
    suggested_outreach: {
      subject: 'Automated High-Value Air Cargo Coverage | Jaguar Transit',
      recipient_role: 'General Manager - Air Freight',
      approved: false,
      body: `Sawadee [Name],\n\nHandling secure tarmac transfers at Suvarnabhumi requires both speed and ironclad insurance warranties.\n\nJaguar Transit provides instant digital policy binding for high-value air cargo consignments, minimizing dwell time while providing comprehensive door-to-destination indemnity.\n\nLet's discuss how our platform connects with your dispatch systems.\n\nKind regards,\nDaniel Wong\nJaguar Transit by JA Assure`
    }
  }
];
