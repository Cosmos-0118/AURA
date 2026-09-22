import { NavGroup } from '@/types';

/** AURA — AI Marketing Operations Desk Navigation */
export const navGroups: NavGroup[] = [
  {
    label: 'MARKETING OPERATIONS',
    items: [
      {
        title: 'Campaign Studio',
        url: '/dashboard/studio',
        icon: 'sparkles',
        items: []
      },
      {
        title: 'Video Studio',
        url: '/dashboard/video',
        icon: 'video',
        items: []
      },
      {
        title: 'Publish',
        url: '/dashboard/publish',
        icon: 'send',
        items: []
      },
      {
        title: 'Lead Intelligence',
        url: '/dashboard/leads',
        icon: 'search',
        items: []
      },
      {
        title: 'Review Queue',
        url: '/dashboard/review',
        icon: 'checks',
        items: []
      }
    ]
  },
  {
    label: 'INTELLIGENCE',
    items: [
      {
        title: 'Competitor Intelligence',
        url: '/dashboard/competitor-intelligence',
        icon: 'search',
        items: []
      }
    ]
  }
];
