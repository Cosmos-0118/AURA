export interface PublishedPerformance {
  platform: string;
  reach: string;
  engagement: string;
  clicks?: string;
  topPost: string;
}

export const DEMO_ENGAGEMENT_ANALYTICS: PublishedPerformance[] = [
  {
    platform: 'LinkedIn',
    reach: '12.4K Impressions',
    engagement: '6.8% Engagement Rate',
    clicks: '3.2% CTR (396 Clicks)',
    topPost: 'Cross-Border Cargo Chain of Custody in ASEAN'
  },
  {
    platform: 'Instagram',
    reach: '18.2K Accounts Reached',
    engagement: '8.1% Engagement Rate',
    clicks: '1.9% Profile Visits',
    topPost: 'Three Things Doctors Should Know About Inquiries'
  },
  {
    platform: 'X (Twitter)',
    reach: '9.7K Impressions',
    engagement: '4.6% Engagement Rate',
    clicks: '2.1% Link Clicks',
    topPost: 'Border Clearance Telemetry and Digital Custody'
  }
];

export interface PublishSimulationStep {
  label: string;
  delayMs: number;
}

export const PUBLISH_STEPS: PublishSimulationStep[] = [
  { label: 'Validated human reviewer approval signature', delayMs: 600 },
  { label: 'Prepared rich media assets & aspect ratio optimization', delayMs: 700 },
  { label: 'Dispatched to Project 2 (The Hands) publishing endpoint', delayMs: 800 },
  { label: 'Received verified provider post ID: demo_ja_28491', delayMs: 500 }
];
