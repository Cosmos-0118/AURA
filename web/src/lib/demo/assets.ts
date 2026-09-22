import type { Asset } from '../api/types';

export interface ExtendedAsset extends Asset {
  priority?: 'high' | 'medium' | 'low';
  scheduled_for?: string;
  published_post_id?: string;
  published_at?: string;
  rejection_reason?: string;
  rejection_note?: string;
  history?: Array<{
    timestamp: string;
    action: string;
    actor: string;
    note?: string;
  }>;
}

export const INITIAL_ASSETS: ExtendedAsset[] = [];
