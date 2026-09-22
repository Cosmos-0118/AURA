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
        title: 'History',
        url: '/dashboard/history',
        icon: 'history',
        items: []
      },
      {
        title: 'Review Queue',
        url: '/dashboard/review',
        icon: 'checks',
        items: []
      },
      {
        title: 'Lead Intelligence',
        url: '/dashboard/leads',
        icon: 'teams',
        items: []
      },
      {
        title: 'Competitor Intelligence',
        url: '/dashboard/competitor-intelligence',
        icon: 'trendingUp',
        items: []
      }
    ]
  }
];

