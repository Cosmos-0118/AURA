# Timeline — 6 to 8 hours

This is a **sprint**, not a 48-hour hackathon plan. If a task is not in **Must ship**, do not start it.

Assume **T+0 = kickoff**. Use the **8-hour** column. If you only have 6 hours, freeze at T+5 and skip the "if time" column entirely.

## What we will demo (and nothing else)

```text
Studio (Jade, LinkedIn) → Generate
  → Review Queue (seeded Instagram FAIL already sitting there)
  → Compliance flags "Guaranteed protection"
  → Reject + tag TOO_SALESY / UNSUPPORTED_CLAIM
  → Lesson saved
  → Brands page: Jade vs DoctorShield
  → Insights: four numbers + that lesson
```

Live Gemini generate is a bonus on top of the seeded FAIL post. **The seeded post is the demo guarantee.** If Gemini is down, you still have a story.

## Explicitly out of scope (do not build)

- Reel / TTS / FFmpeg / MP4
- Leads
- Competitor live crawl / Crawl4AI
- Localization (Malay etc.)
- X, blog, Instagram carousel (Instagram **seeded** FAIL caption is enough)
- Deploy / Docker / Postiz / OAuth
- Clerk, Sentry, Redis, LangGraph-for-its-own-sake
- Sleep shifts

LangGraph: **skip**. M1 writes `async def run_pipeline(campaign_id)` in `graph.py`. Same file name so docs stay valid.

## Checkpoints (10 minutes, voice on)

`main` must boot at every checkpoint. Merge first, argue later.

| Time | Name | Must be true |
|---|---|---|
| **T+1.5h** | Contracts freeze | Schema + seed + mock API + typed client on `main`. M1 posts "contracts are in main". |
| **T+3h** | First merge | Review queue shows seeded FAIL. Studio form submits. Scanner FAILs "guaranteed". LinkedIn stub exists. |
| **T+5h** | Vertical slice | Generate → queue → approve/reject → lesson row. Two brand cards. Insights numbers (seed OK). **6-hour track freezes here** — no new features past this line. |
| **T+6.5h** | Freeze (8h track) | No new features. `db/demo.sql` applied. Rehearse. |
| **T+6h / T+7.5h** | Demo | One clean run of [06-DEMO-SCRIPT.md](06-DEMO-SCRIPT.md). Screenshots as backup. |

## Hour by hour

### T+0 to T+1.5 — Foundation (M1 codes; others are not idle)

**M1 (only person on shared files)**

1. GitHub repo + add the four collaborators (10 min).
2. Supabase project + `db/schema.sql` + `db/seed.sql` + **`db/demo.sql` now, not at the end** (25 min). Seed the FAIL Instagram here so M2 is unblocked.
3. Clone Kiranism into `web/`, cleanup clerk/sentry/chat/kanban, nav items (20 min).
4. FastAPI: `schemas.py`, `db.py`, `main.py`, stub routes, `_stubs.py`, `GET /api/brands` and `GET /api/assets?status=queue` hitting **real seed** (30 min).
5. `web/src/lib/api` types + client (10 min).
6. Announce freeze.

**Do not** wire Gemini, LangGraph, or deploy in this window.

**M2 / M3 (start immediately — do not wait)**

Install bun/uv, clone (or work from docs if repo is empty for 20 min). Build UI against the **mock payload in [03-CONTRACTS.md](03-CONTRACTS.md) §10** using a local `const MOCK_ASSET`. When M1 merges the client, replace MOCK with `listAssets`. **Same shape.** Do not invent fields.

**M4 / M5 (start immediately)**

Write files in your zone locally. You do not need `api/` on GitHub yet: create `api/agents/content.py` etc. on your branch; M1's first push may not include those files, so merge carefully (your new files will not conflict).

M5: YAML + `check_compliance` is pure Python. You can finish the scanner before M1 is done.

M4: stub `generate_content` returning two LinkedIn posts; then Gemini if the key works.

### T+1.5 to T+3 — Screens and real functions

| Who | Do this | Stop if |
|---|---|---|
| M1 | `run_pipeline` + POST campaigns + approve/reject writing DB. Merge whatever lands. | Anyone blocked on a missing route |
| M2 | Queue table + detail + Approve / Reject | Pixel-perfect styling |
| M3 | Studio form + poll + Brands cards | Insights charts |
| M4 | Gemini LinkedIn A/B, three brand voices, lessons in the prompt | Instagram / X / blog |
| M5 | Scanner FAIL on guaranteed; `record_lesson` / `get_relevant_lessons` | LLM compliance layer, crawl |

### T+3 to T+5 — Make the loop real

- M1: if M4/M5 files exist, switch imports off `_stubs`. `GET /api/metrics` with simple SQL (you write it; do not wait for M5).
- M2: reject requires a reason tag; toast + return to queue.
- M3: Insights four numbers + lessons table (no Recharts required — big numbers).
- M4: prove Jade vs DoctorShield locally with `python -c`.
- M5: prove scanner with `python -c`. If time, add Gemini JSON layer. If not, Layer 1 is enough for the demo.

**6-hour teams freeze here.** Remaining time = demo.sql + one rehearsal + slides (5 bullets).

### T+5 to T+6.5 — Only if 8 hours and slice works

Pick **one**:

1. Edit-in-place then approve (M2) **or**
2. Regenerate endpoint (M1) + button (M2) so "lessons changed the next draft" is live **or**
3. Instagram caption from M4 (not carousel)

Do not pick two. Do not start competitors, leads, localize, reel.

### T+6.5 to T+8 — Freeze and rehearse

- Feature freeze. Bugfixes in your zone only.
- Re-run `seed.sql` + `demo.sql`.
- Run the demo script **twice**. If generate hangs >15s, go straight to the seeded FAIL post.
- M1 takes 4 screenshots: Studio, Review (FAIL), Brands, Insights.

## Cut order if behind at T+3

Drop from the bottom. Never drop 1–4.

1. Review queue + compliance panel (seeded FAIL)
2. Approve / reject + reason tag
3. Lesson insert + Insights list
4. Brands cards (Jade ≠ DoctorShield)
5. Studio live generate (seeded assets can fake "we generated this")
6. Real Gemini (keep mock copy)
7. Metrics that are not hardcoded
8. Edit-in-place / regenerate

## Who is the buffer

If anyone is still on setup at T+1, **M1 sits with them**. A second person with a working Review screen is worth more than a fourth API endpoint.
