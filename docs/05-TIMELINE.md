# Timeline

Assume **T+0 = kickoff** (when M1 starts the repo, not when you first read this). Two tracks: **48 hours** (default) and **24-hour cut**.

If you only have 24 hours: complete Phase 1 + the vertical slice, then jump to **Polish** at T+12. Do not start Phase 3.

## Checkpoints (non-negotiable)

At each checkpoint **every branch is merged to `main`**, then M1 runs:

```bash
cd api && uv run uvicorn main:app --port 8000
# other terminal
cd web && bun run dev
```

`main` must boot. If it does not, the checkpoint owner (M1) and the last merger fix it before anyone writes new features.

| Time | Name | What must be true |
|---|---|---|
| **T+3** | Contracts freeze | Schema, seed, stub routes, typed frontend client on `main`. M1 posts "contracts are in main". |
| **T+6** | First merge | M2 queue page renders seed assets. M3 studio form exists (can submit to mock). M4 stub `generate_content`. M5 stub `check_compliance`. |
| **T+14** | Vertical slice | Jade + LinkedIn, real Gemini: generate → compliance flag or pass → review → approve. |
| **T+24** | 24h cut / breadth check | All four platforms for one brand **or** two brands for LinkedIn+Instagram. Lessons write on reject. Insights page shows numbers (even if some are computed from seed). |
| **T+34** | Stretch decision | M1 says which Phase 3 items are still in. Everything else is cut. |
| **T+42** | Code freeze | No new features. Seed demo data. Rehearse. |
| **T+46** | Demo ready | Three clean run-throughs of [06-DEMO-SCRIPT.md](06-DEMO-SCRIPT.md). |

## Phase 0 — Foundation (T+0 to T+3)

**M1 only codes.** Everyone else installs tools ([02-SETUP.md](02-SETUP.md)), gets a Gemini key, reads their member doc, and waits.

M1 delivers:

- GitHub repo, collaborators, `main` protection optional
- `web/` from Kiranism + cleanup
- `api/` FastAPI skeleton + `schemas.py` matching [03-CONTRACTS.md](03-CONTRACTS.md)
- `db/schema.sql` + `db/seed.sql` applied on Supabase
- Stub routes returning seed data
- `web/src/lib/api` client
- Nav items for all pages (pages can 404 until M2/M3 add them — **or** M1 adds empty placeholder `page.tsx` files so nav does not 404)

**Rule:** nobody writes feature logic before M1's "contracts are in main" message.

## Phase 1 — Vertical slice (T+3 to T+12)

One path, real:

```text
Studio: Jade / "Jewellery theft prevention" / Malaysia / Awareness / LinkedIn
  → Generate
  → Review queue shows 2 variants
  → Open one, see compliance panel
  → Approve or reject with a tag
```

| Who | Phase 1 outcome |
|---|---|
| M1 | `POST /api/campaigns` runs `graph.py` in background. Status polling works. Approve/reject endpoints write DB and call `record_lesson`. |
| M2 | Review table + detail page with Approve / Reject / Edit. Reason tags. |
| M3 | Campaign Studio form + a simple "pipeline running" state. Brands page can be read-only cards from `GET /api/brands`. |
| M4 | `generate_content` for **LinkedIn only**, both variants, Jade voice. JSON parse with retry. Mock still used if Gemini is down (`AURA_MOCK_AGENTS`). |
| M5 | Hard-rule scanner + LLM JSON pass. `check_compliance` returns FAIL on "guaranteed". `record_lesson` + `get_relevant_lessons` against `lessons` table. |

**24h cut line is the end of Phase 1.** If the clock says 24h total, skip Phase 2 breadth. Polish the slice. Seed a FAIL asset so the demo always has a compliance catch.

## Phase 1.5 — Sleep (T+12 to T+18) — 48h track only

M1 and M2 sleep first (review UI and glue must be fresh for judges). M3/M4/M5 keep going on Phase 2 items that do not need M1 merges, or they merge what they have and continue.

## Phase 2 — Breadth (T+18 to T+30)

| Who | Add |
|---|---|
| M4 | Instagram (caption, carousel slides as JSON in `body`, hashtags), X (thread), blog (~700 words). `localize()` to Malay for one asset type. |
| M5 | Lessons actually injected (M1 already passes `lessons` into `ContentRequest` — M4 must use them). Competitor snapshot + hash. `GET /api/metrics` SQL. |
| M2 | Content library (approved/rejected filters). Regenerate button. Diff-friendly "original vs edited" on the detail page. |
| M3 | Competitors page, Insights charts (the four metrics in Concept.md §21), localization trigger in Studio. |
| M1 | `POST /api/assets/{id}/regenerate` and `/localize`. Keep `main` green. Help whoever is behind. |

Success: regenerate after a "too salesy" reject and the new copy is visibly different. Switch Jade → DoctorShield and the tone changes.

## Phase 3 — Stretch (T+30 to T+40) — only what M1 keeps at T+34

Pick **at most two**:

1. Reel storyboard: script + TTS audio URL + 3 stills. MP4 via FFmpeg only if it already works in 60 minutes.
2. Leads table + scoring for Jade jewellers (public web search + crawl, no LinkedIn scrape).
3. Deploy (Vercel for `web/`, Render/Fly for `api/`) so the demo is not localhost-only.
4. UI polish: empty states, loading skeletons, brand color tokens.

Do **not** start Instagram OAuth / Postiz / auto-publish.

## Phase 4 — Freeze and rehearse (T+40 to T+46)

- T+42: feature freeze. Only bugfixes in your own zone.
- M1 re-runs `seed.sql` plus a small `db/demo.sql` that plants: one FAIL asset, one approved lesson, two brands' sample posts.
- Run [06-DEMO-SCRIPT.md](06-DEMO-SCRIPT.md) **three times**. If a Gemini call is slow, have the seeded FAIL asset already in the queue as backup.
- Slides: 5 max. Architecture picture, review screenshot, metrics "system is learning", brand-voice switch.

## Cut list (drop in this order if behind)

1. Leads
2. FFmpeg MP4 (keep script)
3. Competitor live crawl (keep seeded snapshots)
4. Blog + X (keep LinkedIn + Instagram)
5. Localization (keep English)
6. Deploy (demo localhost)
7. Insights charts (keep a numbers table)
8. **Never cut:** Review queue, compliance panel, approve/reject + one lesson, two brand voices

## Who is the buffer

If anyone is stuck at T+10, **M1 drops new platform work** and sits with them. The vertical slice on `main` is more important than a fourth platform.
