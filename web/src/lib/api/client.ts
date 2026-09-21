import type {
  Asset,
  Brand,
  BrandId,
  Campaign,
  CampaignCreate,
  CampaignMediaItem,
  Competitor,
  Language,
  Lead,
  Lesson,
  Metrics,
  OperationalModeInfo,
  ReviewAction,
  Snapshot,
  StudioCampaignCreate,
  StudioCampaignDetail
} from './types';
import { DEMO_BRANDS, getDemoBrandsList } from '../demo/brands';
import { auraStore } from '../demo/store';
import { COMPETITOR_INTEL } from '../demo/research';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...init?.headers
    }
  });

  if (!response.ok) {
    const error = await response.json().catch(() => null);
    throw new Error(error?.detail ?? `AURA API request failed (${response.status})`);
  }
  return (await response.json()) as T;
}


function jsonBody(body: unknown): RequestInit {
  return { method: 'POST', body: JSON.stringify(body) };
}


export async function getBrands(): Promise<Brand[]> {
  try {
    return await request<Brand[]>('/api/brands');
  } catch {
    return getDemoBrandsList().map((b) => ({
      id: b.id,
      name: b.name,
      tone: b.tone,
      audience: b.audience,
      do_list: b.do_list,
      dont_list: b.dont_list
    }));
  }
}

export async function getBrand(id: string): Promise<Brand> {
  try {
    return await request<Brand>(`/api/brands/${encodeURIComponent(id)}`);
  } catch {
    const brand = DEMO_BRANDS[id as BrandId] || DEMO_BRANDS.jade;
    return {
      id: brand.id,
      name: brand.name,
      tone: brand.tone,
      audience: brand.audience,
      do_list: brand.do_list,
      dont_list: brand.dont_list
    };
  }
}

export async function getCompetitors(brandId?: string): Promise<Competitor[]> {
  try {
    const query = brandId ? `?brand_id=${encodeURIComponent(brandId)}` : '';
    return await request<Competitor[]>(`/api/competitors${query}`);
  } catch {
    return COMPETITOR_INTEL.filter(
      (c) => !brandId || c.target_brand === brandId
    ).map((c) => ({
      id: c.id,
      brand_id: c.target_brand,
      name: c.competitor_name,
      url: c.source_url
    }));
  }
}

export async function scanCompetitor(id: string): Promise<Snapshot> {
  try {
    return await request<Snapshot>(`/api/competitors/${encodeURIComponent(id)}/scan`, {
      method: 'POST'
    });
  } catch {
    return {
      id: `snap_${Date.now()}`,
      competitor_id: id,
      content_hash: 'hash_demo_78f19b2',
      change_summary: 'Updated risk prevention terms and pricing schedule detected.',
      scraped_at: new Date().toISOString()
    };
  }
}

export async function createCampaign(body: CampaignCreate): Promise<Campaign> {
  try {
    return await request<Campaign>('/api/campaigns', jsonBody(body));
  } catch {
    const campaignId = `camp_${Date.now()}`;
    return {
      id: campaignId,
      brand_id: body.brand_id,
      topic: body.topic,
      country: body.country,
      goal: body.goal,
      platforms: body.platforms,
      language: body.language || 'en',
      status: 'completed',
      error: null,
      created_at: new Date().toISOString(),
      completed_at: new Date().toISOString()
    };
  }
}

export async function getCampaign(id: string): Promise<Campaign> {
  try {
    return await request<Campaign>(`/api/campaigns/${encodeURIComponent(id)}`);
  } catch {
    return {
      id,
      brand_id: 'jade',
      topic: 'High-Value Asset Protection',
      country: 'SG',
      goal: 'Education',
      platforms: ['linkedin', 'instagram'],
      language: 'en',
      status: 'completed',
      error: null,
      created_at: new Date().toISOString(),
      completed_at: new Date().toISOString()
    };
  }
}

export async function listCampaigns(brandId?: string): Promise<Campaign[]> {
  try {
    const query = brandId ? `?brand_id=${encodeURIComponent(brandId)}` : '';
    return await request<Campaign[]>(`/api/campaigns${query}`);
  } catch {
    const demoCampaigns: Campaign[] = [
      {
        id: 'camp_jade_001',
        brand_id: 'jade',
        topic: 'How jewellery businesses can reduce transit risk',
        country: 'SG',
        goal: 'Education',
        platforms: ['linkedin', 'instagram', 'blog'],
        language: 'en',
        status: 'completed',
        error: null,
        created_at: new Date(Date.now() - 3600 * 1000).toISOString(),
        completed_at: new Date(Date.now() - 3500 * 1000).toISOString()
      },
      {
        id: 'camp_doc_001',
        brand_id: 'doctorshield',
        topic: 'Inquiry Defense & Medical Council Protocols',
        country: 'SG',
        goal: 'Awareness',
        platforms: ['linkedin', 'instagram'],
        language: 'en',
        status: 'completed',
        error: null,
        created_at: new Date(Date.now() - 7200 * 1000).toISOString(),
        completed_at: new Date(Date.now() - 7100 * 1000).toISOString()
      }
    ];
    return demoCampaigns.filter((c) => !brandId || c.brand_id === brandId);
  }
}

export async function listAssets(
  params: {
    status?: string;
    brand_id?: string;
    platform?: string;
    campaign_id?: string;
  } = {}
): Promise<Asset[]> {
  try {
    const query = new URLSearchParams();
    for (const [key, value] of Object.entries(params)) {
      if (value) query.set(key, value);
    }
    const suffix = query.toString() ? `?${query.toString()}` : '';
    return await request<Asset[]>(`/api/assets${suffix}`);
  } catch {
    let assets = auraStore.getSnapshot().assets;
    if (params.status && params.status !== 'all') {
      assets = assets.filter((a) => a.status === params.status);
    }
    if (params.brand_id && params.brand_id !== 'all') {
      assets = assets.filter((a) => a.brand_id === params.brand_id);
    }
    if (params.platform && params.platform !== 'all') {
      assets = assets.filter((a) => a.platform === params.platform);
    }
    return assets;
  }
}

export async function getAsset(id: string): Promise<Asset> {
  try {
    return await request<Asset>(`/api/assets/${encodeURIComponent(id)}`);
  } catch {
    const asset = auraStore.getSnapshot().assets.find((a) => a.id === id);
    if (!asset) throw new Error('Asset not found');
    return asset;
  }
}

export async function approveAsset(id: string, body: ReviewAction = {}): Promise<Asset> {
  try {
    return await request<Asset>(`/api/assets/${encodeURIComponent(id)}/approve`, jsonBody(body));
  } catch {
    auraStore.approveAsset(id, body.note);
    return getAsset(id);
  }
}

export async function rejectAsset(id: string, body: ReviewAction = {}): Promise<Asset> {
  try {
    return await request<Asset>(`/api/assets/${encodeURIComponent(id)}/reject`, jsonBody(body));
  } catch {
    auraStore.rejectAsset(id, body.reason_tag || 'OTHER', body.note || 'Rejected by reviewer');
    return getAsset(id);
  }
}

export async function patchAsset(
  id: string,
  body: { body?: string; title?: string }
): Promise<Asset> {
  try {
    return await request<Asset>(`/api/assets/${encodeURIComponent(id)}`, {
      method: 'PATCH',
      body: JSON.stringify(body)
    });
  } catch {
    if (body.body) {
      auraStore.editAsset(id, body.body);
    }
    return getAsset(id);
  }
}

export async function regenerateAsset(id: string): Promise<Asset> {
  try {
    return await request<Asset>(`/api/assets/${encodeURIComponent(id)}/regenerate`, {
      method: 'POST'
    });
  } catch {
    return getAsset(id);
  }
}

export async function localizeAsset(
  id: string,
  body: { language: Language; country: string }
): Promise<Asset> {
  try {
    return await request<Asset>(`/api/assets/${encodeURIComponent(id)}/localize`, jsonBody(body));
  } catch {
    return getAsset(id);
  }
}

export async function listLessons(brandId?: string): Promise<Lesson[]> {
  try {
    const query = brandId ? `?brand_id=${encodeURIComponent(brandId)}` : '';
    return await request<Lesson[]>(`/api/lessons${query}`);
  } catch {
    const lessons = auraStore.getSnapshot().lessons;
    return brandId ? lessons.filter((l) => l.brand_id === brandId) : lessons;
  }
}

export async function listLeads(brandId?: string): Promise<Lead[]> {
  try {
    const query = brandId ? `?brand_id=${encodeURIComponent(brandId)}` : '';
    return await request<Lead[]>(`/api/leads${query}`);
  } catch {
    const leads = auraStore.getSnapshot().leads;
    return brandId ? leads.filter((l) => l.brand_id === brandId) : leads;
  }
}

export async function getMetrics(): Promise<Metrics> {
  try {
    return await request<Metrics>('/api/metrics');
  } catch {
    const m = auraStore.getSnapshot().metrics;
    return {
      rejection_rate: m.rejectionRate,
      avg_edits_per_post: 1.2,
      lessons_count: auraStore.getSnapshot().lessons.length,
      compliance_failure_rate: Number((100 - m.compliancePassRate).toFixed(1)),
      assets_total: m.contentGenerated,
      assets_pending: m.awaitingReview
    };
  }
}

// --- Studio Campaign Flow API ---

export async function getOperationalMode(): Promise<OperationalModeInfo> {
  try {
    return await request<OperationalModeInfo>('/api/campaigns/mode');
  } catch {
    return {
      demo_mode: true,
      groq_model: 'llama-3.3-70b-versatile',
      image_model: 'fal-ai/flux/schnell',
      video_model: 'minimax/h3-max-turbo'
    };
  }
}

export async function generateStudioCampaign(
  body: StudioCampaignCreate
): Promise<StudioCampaignDetail> {
  return await request<StudioCampaignDetail>('/api/campaigns/studio/generate', jsonBody(body));
}

export async function getStudioCampaign(id: string): Promise<StudioCampaignDetail> {
  return await request<StudioCampaignDetail>(`/api/campaigns/${encodeURIComponent(id)}/studio`);
}

export async function generateCampaignImage(
  id: string,
  prompt?: string,
  model?: string
): Promise<CampaignMediaItem> {
  return await request<CampaignMediaItem>(
    `/api/campaigns/${encodeURIComponent(id)}/generate-image`,
    jsonBody({ prompt, model })
  );
}

export async function generateCampaignVideo(
  id: string,
  prompt?: string,
  model?: string
): Promise<CampaignMediaItem> {
  return await request<CampaignMediaItem>(
    `/api/campaigns/${encodeURIComponent(id)}/generate-video`,
    jsonBody({ prompt, model })
  );
}

export async function submitCampaignForReview(id: string): Promise<StudioCampaignDetail> {
  return await request<StudioCampaignDetail>(
    `/api/campaigns/${encodeURIComponent(id)}/submit-review`,
    { method: 'POST' }
  );
}

