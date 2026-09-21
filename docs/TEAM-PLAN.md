# AURA 8-hour team plan

This is the single source of truth for the hackathon. The scaffold is already on
`main`; the eight-hour clock below starts when the five feature branches begin.

Each person reads only:

1. `AGENTS.md`
2. this file
3. their file in `docs/members/`
4. the linked sections of `docs/03-CONTRACTS.md`

Do not read every member file. Do not restart the scaffold.

## The product we will demonstrate

AURA is a marketing operations dashboard, not a chatbot.

```text
Campaign Studio
  -> brand-specific content
  -> deterministic compliance check
  -> human review (approve, edit, or reject)
  -> reviewer correction saved as a lesson
  -> metrics and lessons visible in Insights
```

The winning story is **compliance + human review + learning**. Live Gemini is an
enhancement; the product must still work with `AURA_MOCK_AGENTS=true`.

## What already exists on `main`

Do not rebuild these pieces:

- Postgres schema, three brands, and repeatable demo data in `db/`.
- FastAPI app, routes, review writes, metrics, and campaign pipeline in `api/`.
- Frozen Pydantic and TypeScript types.
- Typed frontend client in `web/src/lib/api/`.
- AURA navigation and dashboard shell.
- Safe mock agent implementations in `api/agents/_stubs.py`.

Still missing:

- AURA frontend pages: Review, Studio, Brands, Insights, and an AURA Overview.
- Real M4 modules: `content.py` and its prompts.
- Real M5 modules: `compliance.py`, `lessons.py`, and compliance rules.
- One integrated, rehearsed, end-to-end run on `main`.

The starter Products, Users, and generic chart code is reference material. It is
not an AURA requirement and must not be expanded.

## Scope for these eight hours

### Must ship

- Create a LinkedIn campaign for one of the three brands.
- Generate two usable content variants with visibly different brand voices.
- Flag absolute claims such as `guaranteed` as `FAIL / HIGH`.
- Show queued and compliance-failed assets in Review.
- Approve, edit-and-approve, or reject with a reason tag.
- Save edits/rejections as lessons and show them in Insights.
- Show brand profiles and a small AURA command-center overview.
- Preserve a deterministic mock path for the demo.

### Build only after the must-ship loop works

- M2: approved-content Library.
- M4: Instagram captions using the same generation path.
- M5: a structured Gemini second-pass compliance review.
- M1: extra overview polish or a regenerate endpoint.

### Do not build

Competitor crawling, lead discovery, localization, reels/video, X, blog,
publishing, auth, Docker deployment, LangGraph, Redis, queues, or a second DB.
Existing list endpoints or 501 placeholders for these areas may remain.

## Work split

| Owner | Outcome by T+4.5 | Owned work |
|---|---|---|
| **M1 — integration** | `main` runs the complete mock-backed loop | API/DB/client integration, merges, AURA Overview, smoke checks, demo data |
| **M2 — review** | A reviewer can inspect compliance and approve/edit/reject | Review queue, detail, actions; Library after the loop works |
| **M3 — campaign UI** | A user can create a campaign and see brands/metrics/lessons | Studio, Brands, Insights |
| **M4 — content** | Content differs clearly across Jade, DoctorShield, and Jaguar | `content.py`, content prompts, deterministic fallback, Gemini path |
| **M5 — safety + learning** | Bad claims fail and review feedback is retrievable | `compliance.py`, `lessons.py`, rules, deterministic fallback |

Exact writable paths are in `AGENTS.md` and `docs/04-WORKFLOW-RULES.md`. A member
does not edit another member's file to unblock themselves.

## Dependency map

```text
M4 generate_content ----\
                         -> M1 graph/routes/DB -> M1 typed client -> M2 Review
M5 compliance/lessons --/                              |          -> M3 Studio/Insights
                                                      \----------> M1 Overview
```

The interfaces already exist. M4 and M5 must match the Python signatures in
Contracts section 5. M2 and M3 must import the client and types from
`web/src/lib/api/`; they must never call `fetch()` directly or duplicate types.

## Eight-hour clock

### T+0:00 to T+0:30 — boot and branch

Everyone checks out their assigned branch, merges `origin/main`, installs only
existing dependencies, and proves their local command starts. M1 confirms that
the shared database contains the demo rows.

If setup is still broken at T+0:30, post the exact error. M1 pairs with that
person; the other three keep building.

### T+0:30 to T+2:30 — first working slice

- **M1:** exercise health, brands, queue, review, lessons, and metrics endpoints;
  start the AURA Overview using existing client functions.
- **M2:** queue list, useful loading/error/empty states, asset detail, compliance
  panel.
- **M3:** Studio form and Brands cards; submit through `createCampaign`.
- **M4:** deterministic `generate_content` with A/B LinkedIn variants and all
  three voices; no network required.
- **M5:** deterministic banned-term scanner and DB-backed lesson read/write.

At T+2:30 every branch opens a PR. It may be visually plain, but it must compile
or pass its focused checks.

### T+2:30 to T+4:30 — connect the loop

- **M1:** merge small PRs, run a campaign with real M4/M5 modules, fix integration
  only in M1-owned paths.
- **M2:** wire approve, edit-and-approve, and reject; invalidate/refetch queue data.
- **M3:** add campaign polling, generated-asset links, Insights metrics, and lessons.
- **M4:** add prompt-backed Gemini generation with a deterministic fallback; use
  lessons in the prompt.
- **M5:** add suggested revisions, complete rules, and prove lesson round-trip.

### T+4:30 checkpoint — vertical slice on `main`

This exact path must work before any stretch task:

1. Open the seeded failed asset.
2. See `Guaranteed protection` and `CLAIM_001` as high risk.
3. Reject it with `UNSUPPORTED_CLAIM` and an empty optional note.
4. See the new lesson in Insights.
5. Create a Jade LinkedIn campaign.
6. See generated assets in Review and approve one.

If any step fails, all available work goes to that failure. No one starts a new
feature.

### T+4:30 to T+6:30 — completeness and polish

- **M1:** finish Overview, integration smoke test, empty-data checks, and demo
  reset procedure.
- **M2:** finish edit-and-approve and build the approved Library if stable.
- **M3:** finish responsive states, filters, campaign failure UI, and Insights.
- **M4:** improve output quality, Instagram caption support, and focused tests.
- **M5:** improve explanations and tests; add Gemini second pass only if it cannot
  break the deterministic scanner.

### T+6:30 — feature freeze

No new features. Merge, run checks, reset demo data, and rehearse twice. Gemini
gets 15 seconds during the demo; after that switch to the deterministic path.

## Handoffs and merge order

1. M4 and M5 can merge independently because their files do not overlap.
2. M1 merges M4/M5 and verifies `AURA_MOCK_AGENTS=false` and `true` both remain
   safe; failures must fall back rather than crash a campaign.
3. M2 and M3 merge independently after frontend typecheck/build passes.
4. M1 performs the full click path and fixes integration only in M1-owned files.

Every PR must include:

- user-visible outcome;
- checks run and their results;
- known limitation;
- screenshot for a UI PR, or sample input/output for an agent PR.

## Shared acceptance checks

```bash
# backend import/syntax check
cd api && uv run python -m compileall main.py db.py schemas.py graph.py routes agents

# frontend checks
cd web && bun run typecheck && bun run build
```

M1 also runs the API and frontend together and clicks the T+4:30 path. Passing
builds do not replace that integration check.

## When a contract seems wrong

Do not patch around it. Send M1:

```text
CONTRACT REQUEST
Blocked owner: M2/M3/M4/M5
Existing contract: <type, field, function, or endpoint>
Needed behavior: <one sentence>
Why the existing shape cannot represent it: <one sentence>
```

M1 either updates all shared representations together or points to the existing
field to use. Silence is not permission to invent a local shape.

## Cut order if behind

Keep items 1–5. Cut from the bottom.

1. Review queue and compliance detail.
2. Reject/edit/approve and lesson persistence.
3. Brands and Insights.
4. Deterministic brand-specific generation.
5. Studio campaign creation.
6. AURA Overview polish.
7. Gemini calls.
8. Library, Instagram generation, regenerate, and LLM compliance.
