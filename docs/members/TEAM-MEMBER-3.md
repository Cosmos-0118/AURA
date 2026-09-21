# Team Member 3 — Campaign, brands, and insights owner

## Mission

Build the three screens around the review loop: create work in Studio, explain
why each brand sounds different, and show that reviewer feedback becomes learning.

Read `AGENTS.md`, `docs/TEAM-PLAN.md`, Contracts sections 1, 6, 7, and 10, then
this card.

## Branch and owned paths

Branch: `feat/m3-studio-ui`

```text
web/src/features/studio/**
web/src/features/brands/**
web/src/features/insights/**
web/src/app/dashboard/studio/**
web/src/app/dashboard/brands/**
web/src/app/dashboard/insights/**
web/src/components/aura/m3/**
```

Competitors and Leads folders are reserved but out of this sprint. Import only
from `web/src/lib/api/`; do not duplicate types or use raw `fetch()`.

## Required routes

### `/dashboard/studio`

Fields:

- brand from `getBrands()`;
- topic;
- country;
- campaign goal;
- LinkedIn selected by default;
- English only in the must-ship path.

Call `createCampaign`, poll `getCampaign` while status is `running`, and stop on
`completed` or `failed`. When complete, call
`listAssets({ campaign_id: campaign.id })` and link results to M2's
`/dashboard/review/[id]`. Stop polling on unmount and enforce a reasonable timeout.

The UI must make the three states clear: generating, completed, failed. Do not
invent a fake multi-agent progress animation.

### `/dashboard/brands`

Use `getBrands()` and show all three profiles with:

- name and audience;
- tone chips;
- do and don't guidance;
- one short example or visual cue that makes each voice easy to compare.

### `/dashboard/insights`

Use `getMetrics()` and `listLessons()`. Show:

- rejection rate;
- average edits per reviewed post;
- lesson count;
- compliance failure rate;
- total and pending assets as supporting context;
- a recent lessons table with brand, platform, reason, note, and time.

Use readable number cards first. Charts are optional and must not replace exact
values. Handle a completely empty database without division or rendering errors.

## Work order

1. Studio and Brands shells.
2. Wire Studio create/poll/results.
3. Wire Brands.
4. Build and wire Insights.
5. Add loading, empty, failure, timeout, and responsive states.
6. Improve visuals only after the full path works.

## Acceptance

- A valid Studio submission cannot be double-submitted.
- Polling stops after completed, failed, timeout, or navigation away.
- Completed campaigns show links to their generated assets.
- Jade, DoctorShield, and Jaguar visibly communicate different voices.
- Seeded metrics and lessons render, and empty results also render.
- No M2 component is imported; integration is through URLs and shared client types.
- `bun run typecheck` and `bun run build` pass.

## Give your coding agent this task

```text
Read AGENTS.md, docs/TEAM-PLAN.md, docs/members/TEAM-MEMBER-3.md, and the linked
contract sections. Work only in M3-owned paths. Build Studio, Brands, and Insights
with the existing typed API client. Finish create/poll/results and all error/empty
states before optional charts or polish. Link generated assets to M2 by URL; do
not import M2 files or edit shared API/nav/types/components.
```
