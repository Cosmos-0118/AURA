import { NavGroup } from '@/types';

/** AURA's four demo screens plus the starter overview route. */
export const navGroups: NavGroup[] = [
  {
    label: 'AURA',
    items: [
      {
        title: 'Overview',
        url: '/dashboard',
        icon: 'dashboard',
        isActive: true,
        items: []
      },
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
        title: 'Review Queue',
        url: '/dashboard/review',
        icon: 'checks',
        items: []
      },
      {
        title: 'Brands',
        url: '/dashboard/brands',
        icon: 'workspace',
        items: []
      },
      {
        title: 'Insights',
        url: '/dashboard/insights',
        icon: 'trendingUp',
        items: []
      },
      {
        title: 'Lead Generation',
        url: '/dashboard/leads',
        icon: 'user',
        items: []
      }
    ]
  }
];
