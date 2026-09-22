export interface AgentActivityItem {
  id: string;
  time: string;
  agent: string;
  agentType: 'content' | 'compliance' | 'research' | 'learning' | 'lead';
  description: string;
  status: 'completed' | 'flagged' | 'detected' | 'learned';
}

export interface RejectionReasonStat {
  reason: string;
  percentage: number;
  count: number;
}

export interface LearningTrendPoint {
  week: string;
  editRate: number;
  rejectionRate: number;
  passRate: number;
}

export const INITIAL_AGENT_ACTIVITY: AgentActivityItem[] = [
  {
    id: 'act_1',
    time: '10:42 PM',
    agent: 'Content Agent',
    agentType: 'content',
    description: 'Generated 4 Jade LinkedIn variants with tone matching',
    status: 'completed'
  },
  {
    id: 'act_2',
    time: '10:39 PM',
    agent: 'Compliance Agent',
    agentType: 'compliance',
    description: 'Flagged 1 asset for unsupported absolute claim (CLAIM_001)',
    status: 'flagged'
  },
  {
    id: 'act_3',
    time: '10:31 PM',
    agent: 'Research Agent',
    agentType: 'research',
    description: 'Detected competitor campaign change (Transit Risk Co.)',
    status: 'detected'
  },
  {
    id: 'act_4',
    time: '10:24 PM',
    agent: 'Learning Agent',
    agentType: 'learning',
    description: 'Stored lesson: TOO_SALESY applied to Jade prompt memory',
    status: 'learned'
  },
  {
    id: 'act_5',
    time: '10:18 PM',
    agent: 'Lead Agent',
    agentType: 'lead',
    description: 'Qualified 7 new high-fit prospects across SG & MY',
    status: 'completed'
  }
];

export const REJECTION_REASONS_DATA: RejectionReasonStat[] = [
  { reason: 'Too Salesy', percentage: 31, count: 13 },
  { reason: 'Unsupported Claim', percentage: 24, count: 10 },
  { reason: 'Wrong CTA', percentage: 18, count: 8 },
  { reason: 'Off Brand Voice', percentage: 14, count: 6 },
  { reason: 'Too Long / Dense', percentage: 8, count: 3 },
  { reason: 'Other', percentage: 5, count: 2 }
];

export const LEARNING_TREND_DATA: LearningTrendPoint[] = [
  { week: 'Week 1', editRate: 42, rejectionRate: 26, passRate: 74 },
  { week: 'Week 2', editRate: 34, rejectionRate: 21, passRate: 81 },
  { week: 'Week 3', editRate: 27, rejectionRate: 17, passRate: 86 },
  { week: 'Week 4', editRate: 18.7, rejectionRate: 14.2, passRate: 91.4 }
];
