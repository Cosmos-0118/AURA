# Public Media URLs & Buffer Publishing Guide

This document describes how to configure and run AURA's Buffer publishing system during local development and production.

---

## 1. Overview

Buffer requires all media attachments (images and videos) to be accessible over the public internet via **HTTPS** so that Buffer's scrapers can download and process them prior to posting to LinkedIn, Instagram, or X.

AURA generates and watermarks media locally under `storage/`:
```text
storage/campaigns/{campaign_id}/image/final_v1.png
storage/campaigns/{campaign_id}/video/final_v1.mp4
```

AURA's FastAPI backend serves the `storage/` directory statically on the `/media` route:
```text
/media/campaigns/{campaign_id}/image/final_v1.png
/media/campaigns/{campaign_id}/video/final_v1.mp4
```

By setting `MEDIA_PUBLIC_BASE_URL`, AURA combines your public domain/tunnel with `/media/...` to construct publicly accessible URLs for Buffer:
```text
https://<public-domain-or-tunnel>/media/campaigns/{campaign_id}/image/final_v1.png
```

---

## 2. Prerequisites & Environment Setup

In the project root `.env` file, configure your Buffer API credentials and public media base URL:

```env
# Buffer API Key (obtained from Buffer -> Settings -> API -> Create API Key)
BUFFER_API_KEY=your_buffer_api_key_here

# (Optional) Specific Buffer Channel IDs if you wish to override dynamic discovery:
BUFFER_ORGANIZATION_ID=
BUFFER_LINKEDIN_CHANNEL_ID=
BUFFER_INSTAGRAM_CHANNEL_ID=
BUFFER_X_CHANNEL_ID=
BUFFER_PUBLISH_MODE=addToQueue

# Public HTTPS URL exposing AURA's /media route
MEDIA_PUBLIC_BASE_URL=https://abc123.ngrok-free.app
```

> [!IMPORTANT]
> - Buffer **rejects** `localhost`, `127.0.0.1`, and `file://` URLs.
> - `MEDIA_PUBLIC_BASE_URL` **must** be an external HTTPS URL (e.g. ngrok tunnel or live domain).
> - If `MEDIA_PUBLIC_BASE_URL` is omitted or set to localhost, publishing will fail immediately with a clear error:
>   `"MEDIA_PUBLIC_BASE_URL is not configured. Buffer requires a publicly accessible HTTPS media URL."`

---

## 3. Starting AURA for Local Development

### Option A: Using the AURA Launcher Script (Recommended)
From the repository root:
```bash
./scripts/macos/aura.sh
```
Choose `3) Just run` or `2) Build + run`. This starts:
- **Backend API**: `http://0.0.0.0:8000`
- **Frontend App**: `http://localhost:3000`

### Option B: Starting Services Manually

1. **Start the FastAPI Backend**:
   ```bash
   cd api
   uv run uvicorn main:app --host 0.0.0.0 --port 8000
   ```

2. **Start the Next.js Frontend** (in a separate terminal):
   ```bash
   cd web
   bun dev
   ```

---

## 4. Setting up a Public Tunnel (ngrok)

To expose local media storage to Buffer while developing locally:

1. In a new terminal, launch ngrok pointing to port `8000`:
   ```bash
   ngrok http 8000
   ```

2. ngrok displays your forwarding URL, for example:
   ```text
   Forwarding   https://abc123.ngrok-free.app -> http://localhost:8000
   ```

3. Update your `.env` in the project root:
   ```env
   MEDIA_PUBLIC_BASE_URL=https://abc123.ngrok-free.app
   ```

4. Restart the backend API (or launcher) so the new environment variable is loaded.

---

## 5. Verifying Media Accessibility

### Check Media Diagnostics Endpoint
Open in your browser or run:
```bash
curl http://localhost:8000/api/media/config
```
Expected response:
```json
{
  "configured": true,
  "base_url": "https://abc123.ngrok-free.app",
  "media_endpoint_available": true
}
```

### Test Public Media in Browser
Open the public URL in any browser (or on your mobile phone without local WiFi):
```text
https://abc123.ngrok-free.app/media/campaigns/{campaign_id}/image/final_v1.png
```
You should see the final watermarked campaign image or video directly.

---

## 6. End-to-End Publishing Flow in Review Queue

1. Open `http://localhost:3000/dashboard/review`.
2. Select a campaign awaiting review.
3. Review copy, image, compliance checks, and watermark.
4. Click **Approve Campaign**:
   - The campaign transitions to `approved`.
   - The platform publishing deck unlocks (**LinkedIn**, **Instagram**, **X**).
5. Click **Post to LinkedIn** (or Instagram / X):
   - A confirmation dialog opens with a full preview of the final watermarked media, approved copy, and pre-publish checklist.
6. Click **Confirm**:
   - AURA verifies that final watermarked media exists (`media_stage = 'final'`, `watermarked = 1`).
   - AURA generates the public media URL: `https://abc123.ngrok-free.app/media/...`.
   - AURA performs a pre-flight reachability check on the URL.
   - AURA sends the post with public media URL to Buffer's GraphQL API.
   - The publication record is saved in `campaign_publications` with `media_id` referencing the exact final media.
   - The card updates to `✓ Published` and duplicate protection prevents accidental double-posting.
