import { NavGroup } from '@/types';

/** AURA — AI Marketing Operations Desk Navigation */
export const navGroups: NavGroup[] = [
  {
    label: 'OPERATIONS',
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
        title: 'Review Queue',
        url: '/dashboard/review',
        icon: 'checks',
        label: '8',
        items: []
      },
      {
        title: 'Research',
        url: '/dashboard/research',
        icon: 'search',
        items: []
      },
      {
        title: 'Leads',
        url: '/dashboard/leads',
        icon: 'teams',
        label: '34',
        items: []
      },
      {
        title: 'Content Library',
        url: '/dashboard/content',
        icon: 'galleryVerticalEnd',
        items: []
      }
    ]
  },
  {
    label: 'INTELLIGENCE & DELIVERY',
    items: [
      {
        title: 'Brands',
        url: '/dashboard/brands',
        icon: 'workspace',
        items: []
      },
      {
        title: 'Learning & Insights',
        url: '/dashboard/insights',
        icon: 'trendingUp',
        items: []
      },
      {
        title: 'Publishing',
        url: '/dashboard/publishing',
        icon: 'send',
        items: []
      },
      {
        title: 'Settings',
        url: '/dashboard/settings',
        icon: 'settings',
        items: []
      }
    ]
  }
];
