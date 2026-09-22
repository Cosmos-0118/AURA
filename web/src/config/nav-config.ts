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
        title: 'Review Queue',
        url: '/dashboard/review',
        icon: 'checks',
        items: []
      }
    ]
  }
];
