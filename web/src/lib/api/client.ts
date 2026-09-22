import type {
  Asset,
  Brand,
  Campaign,
  CampaignCreate,
  Competitor,
  Language,
  Lead,
  Lesson,
  Metrics,
  Platform,
  ReviewAction,
  Snapshot,
} from "./types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => null);
    throw new Error(error?.detail ?? `AURA API request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

function jsonBody(body: unknown): RequestInit {
  return { method: "POST", body: JSON.stringify(body) };
}

export function getBrands(): Promise<Brand[]> {
  return request<Brand[]>("/api/brands");
}

export function getBrand(id: string): Promise<Brand> {
  return request<Brand>(`/api/brands/${encodeURIComponent(id)}`);
}

export function getCompetitors(brandId?: string): Promise<Competitor[]> {
  const query = brandId ? `?brand_id=${encodeURIComponent(brandId)}` : "";
  return request<Competitor[]>(`/api/competitors${query}`);
}

export function scanCompetitor(id: string): Promise<Snapshot> {
  return request<Snapshot>(`/api/competitors/${encodeURIComponent(id)}/scan`, {
    method: "POST",
  });
}

export function createCampaign(body: CampaignCreate): Promise<Campaign> {
  return request<Campaign>("/api/campaigns", jsonBody(body));
}

export function getCampaign(id: string): Promise<Campaign> {
  return request<Campaign>(`/api/campaigns/${encodeURIComponent(id)}`);
}

export function listCampaigns(brandId?: string): Promise<Campaign[]> {
  const query = brandId ? `?brand_id=${encodeURIComponent(brandId)}` : "";
  return request<Campaign[]>(`/api/campaigns${query}`);
}

export function listAssets(params: {
  status?: string;
  brand_id?: string;
  platform?: string;
  campaign_id?: string;
} = {}): Promise<Asset[]> {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value) query.set(key, value);
  }
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return request<Asset[]>(`/api/assets${suffix}`);
}

export function getAsset(id: string): Promise<Asset> {
  return request<Asset>(`/api/assets/${encodeURIComponent(id)}`);
}

export function approveAsset(id: string, body: ReviewAction = {}): Promise<Asset> {
  return request<Asset>(`/api/assets/${encodeURIComponent(id)}/approve`, jsonBody(body));
}

export function rejectAsset(id: string, body: ReviewAction = {}): Promise<Asset> {
  return request<Asset>(`/api/assets/${encodeURIComponent(id)}/reject`, jsonBody(body));
}

export function patchAsset(
  id: string,
  body: { body?: string; title?: string },
): Promise<Asset> {
  return request<Asset>(`/api/assets/${encodeURIComponent(id)}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export function regenerateAsset(id: string): Promise<Asset> {
  return request<Asset>(`/api/assets/${encodeURIComponent(id)}/regenerate`, {
    method: "POST",
  });
}

export function localizeAsset(
  id: string,
  body: { language: Language; country: string },
): Promise<Asset> {
  return request<Asset>(`/api/assets/${encodeURIComponent(id)}/localize`, jsonBody(body));
}

export function listLessons(brandId?: string): Promise<Lesson[]> {
  const query = brandId ? `?brand_id=${encodeURIComponent(brandId)}` : "";
  return request<Lesson[]>(`/api/lessons${query}`);
}

export function listLeads(brandId?: string): Promise<Lead[]> {
  const query = brandId ? `?brand_id=${encodeURIComponent(brandId)}` : "";
  return request<Lead[]>(`/api/leads${query}`);
}

export function getMetrics(): Promise<Metrics> {
  return request<Metrics>("/api/metrics");
}

export function generateVideo(body: import("./types").VideoGenerateRequest): Promise<import("./types").VideoGenerateResponse> {
  return request<import("./types").VideoGenerateResponse>("/api/video/generate", jsonBody(body));
}

export function getVideoConfig(): Promise<import("./types").VideoConfig> {
  return request<import("./types").VideoConfig>("/api/video/config");
}

export function attachVideoToAsset(body: import("./types").VideoAttachRequest): Promise<{ ok: boolean; asset_id: string; media_url: string }> {
  return request<{ ok: boolean; asset_id: string; media_url: string }>("/api/video/attach", jsonBody(body));
}

export function getBufferStatus(): Promise<import("./types").BufferStatus> {
  return request<import("./types").BufferStatus>("/api/buffer/status");
}

export function listBufferChannels(): Promise<{ channels: import("./types").BufferChannel[] }> {
  return request<{ channels: import("./types").BufferChannel[] }>("/api/buffer/channels");
}

export function publishToBuffer(
  body: import("./types").BufferPublishRequest,
): Promise<import("./types").BufferPublishResult> {
  return request<import("./types").BufferPublishResult>("/api/buffer/publish", jsonBody(body));
}
