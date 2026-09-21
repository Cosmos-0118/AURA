# Team Member 3 — Studio and Intelligence UI

You own how a marketer **starts** work (Campaign Studio, Brands) and how they **see learning** (Insights, Competitors, Leads). You do not own the Review Queue.

You do not call Gemini. You do not edit Python. You consume `web/src/lib/api`.

## Read these first

1. [../00-START-HERE.md](../00-START-HERE.md)
2. [../02-SETUP.md](../02-SETUP.md)
3. [../03-CONTRACTS.md](../03-CONTRACTS.md) — `CampaignCreate`, `Brand`, `Metrics`, `Lesson`, `Lead`
4. [../04-WORKFLOW-RULES.md](../04-WORKFLOW-RULES.md)
5. [../../AGENTS.md](../../AGENTS.md)

Skim Concept.md §20–21 for the sidebar names and the four metrics. Specs in `docs/` win if they disagree.

## Your branch

`feat/m3-studio-ui`

Wait for "contracts are in main". Until then: install, run, read.

## Files you own

```text
web/src/features/studio/**
web/src/features/brands/**
web/src/features/insights/**
web/src/features/competitors/**
web/src/features/leads/**
web/src/app/dashboard/studio/**
web/src/app/dashboard/brands/**
web/src/app/dashboard/insights/**
web/src/app/dashboard/competitors/**
web/src/app/dashboard/leads/**
web/src/components/aura/m3/**
```

Copy form patterns from `web/src/features/products` create-product form. Copy chart patterns from `web/src/features/overview`.

## Never touch

```text
web/src/lib/api/**
web/src/config/nav-config.ts
web/src/components/ui/**
web/src/features/review/**
web/src/features/library/**
web/src/app/dashboard/review/**
web/src/app/dashboard/library/**
api/**
```

---

## Screen spec — Campaign Studio (`/dashboard/studio`)

This is the **start of the demo**.

Form fields (names match `CampaignCreate`):

| Field | Control | Values |
|---|---|---|
| `brand_id` | Select | from `getBrands()` — label is `name`, value is `id` |
| `topic` | Text | e.g. Jewellery theft prevention |
| `country` | Text or select | Malaysia, Singapore, Thailand, Indonesia, Hong Kong |
| `goal` | Select | Awareness, Lead gen, Education, Product |
| `platforms` | Multi-check | linkedin, instagram, x, blog, reel |
| `language` | Select | en, ms, id, th, zh |

Submit → `createCampaign(body)`.

Then show a **run panel** for that campaign id:

- Poll `getCampaign(id)` every 2s while `status` is `queued` or `running`
- Stop on `completed` or `failed`
- On completed: `listAssets({ campaign_id })` and list them with links to `/dashboard/review/{id}` (M2's page — just an `<a>`, do not import M2 components)
- On failed: show `campaign.error`

Do not build a fake progress of 8 agents. Three states are enough: Running / Done / Failed.

Phase 2: a "Localize this asset" is on M2; you may add a language field only on create.

---

## Screen spec — Brands (`/dashboard/brands`)

Three cards from `getBrands()`.

Each card:

- Name
- Tone as chips
- Audience
- Do / Don't lists

Read-only for the hackathon. No edit form unless you have spare time in Phase 3 — and if you add PATCH `/api/brands/{id}`, that is a **contract change**: ask M1 first. Default is read-only.

Demo uses this screen to prove Jade ≠ DoctorShield.

---

## Screen spec — Insights (`/dashboard/insights`)

Two sections.

### Metrics

`getMetrics()`. Four numbers + two counts:

| Label | Field | Format |
|---|---|---|
| Rejection rate | `rejection_rate` | percent |
| Avg human edits / post | `avg_edits_per_post` | 1 decimal |
| First-pass approval | `first_pass_approval` | percent |
| Compliance failure rate | `compliance_failure_rate` | percent |
| Assets total | `assets_total` | int |
| Waiting on review | `assets_pending` | int |

Use the starter's overview cards + one Recharts bar or line. If you only have a single snapshot (no history), show **big numbers**, not a fake time series. Do not invent history.

Caption under the numbers: **The system is learning from reviewer feedback.**

### Lessons

`listLessons()`. Table: brand, platform, reason_tag, note, created_at. Expand row to show original_body vs edited_body if present.

---

## Screen spec — Competitors (`/dashboard/competitors`)

Phase 2.

Table from `getCompetitors()`. Button **Scan** → `scanCompetitor(id)`. Show returned `change_summary` in a toast or a detail row.

If scan is slow, disable the button and show "Scanning…".

---

## Screen spec — Leads (`/dashboard/leads`)

Phase 3. Table from `listLeads()`: name, url, country, fit_score, why. Sort by `fit_score` desc.

If the API returns `[]`, empty state: "Lead agent not run yet." Do not mock fake companies in the frontend.

---

## Optional overview (`/dashboard`)

The starter overview may still show product metrics. If M1 left it, you **may** replace **only** `web/src/features/overview/**` if that folder is not in anyone's table.

Check: overview is **not** listed as M2. It is also not listed as yours. **Do not edit it unless M1 assigns it.** Safer: leave the starter overview alone. Your Insights page is the real metrics surface.

---

## Phases

### Phase 1

| Task | Acceptance |
|---|---|
| Studio form | Submit creates a campaign; run panel shows completed using mocks |
| Asset list after run | Links to `/dashboard/review/{id}` work |
| Brands cards | Three brands, tones visible |

### Phase 2

| Task | Acceptance |
|---|---|
| Insights numbers | Four rates render from API (zeros are OK if no reviews yet) |
| Lessons table | Rejected items from M2 appear after refresh |
| Competitors | List + scan button |

### Phase 3

Leads table. Visual polish. Do not start a calendar.

---

## React Query keys

```ts
["brands"]
["campaign", id]
["campaigns"]
["assets", { campaign_id }]
["metrics"]
["lessons", brandId]
["competitors", brandId]
["leads", brandId]
```

Do not use `["assets"]` without params in a way that fights M2 — including params in the key is enough.

---

## Cursor agent prompts (paste as-is)

### Prompt A — Studio

```text
You are Team Member 3 for AURA. Read AGENTS.md and docs/03-CONTRACTS.md.

Build Campaign Studio at web/src/app/dashboard/studio/page.tsx with implementation in web/src/features/studio/.

Form fields matching CampaignCreate: brand_id (from getBrands), topic, country, goal, platforms (multi), language.

Submit calls createCampaign. Then poll getCampaign(id) every 2s until completed or failed.

On completed, listAssets({ campaign_id: id }) and link each row to /dashboard/review/{asset.id}.

On failed, show campaign.error.

Copy form patterns from web/src/features/products. Use shadcn components via import from @/components/ui/*. Do not edit those ui files.

Only write under web/src/features/studio, web/src/app/dashboard/studio, web/src/components/aura/m3.
```

### Prompt B — Brands

```text
Build /dashboard/brands using getBrands() from @/lib/api/client.

Three cards: name, tone chips, audience, do_list, dont_list.

Read-only. Files only in web/src/features/brands and web/src/app/dashboard/brands.
```

### Prompt C — Insights

```text
Build /dashboard/insights.

Section 1: getMetrics() displayed as four stat cards (rejection_rate, avg_edits_per_post, first_pass_approval, compliance_failure_rate) formatted as specified in docs/members/TEAM-MEMBER-3.md. Also assets_total and assets_pending. Subtitle: "The system is learning from reviewer feedback." Do not fabricate time-series data.

Section 2: listLessons() table with brand_id, platform, reason_tag, note, created_at. Expandable original_body / edited_body.

Use Recharts only if already used in the starter overview. Files in web/src/features/insights and web/src/app/dashboard/insights.

Import types from @/lib/api/types. Do not create parallel types.
```

### Prompt D — Competitors + Leads

```text
Build competitors page: getCompetitors(), scanCompetitor(id) button, show change_summary.

Build leads page: listLeads(), columns name, url, country, fit_score, why, sorted by fit_score desc. Empty state if [].

Stay in web/src/features/competitors, leads, and matching app/dashboard routes. No Python. No review feature files.
```

---

## How you combine with others

- After generate, you **link** to M2's routes. You do not embed the review panel.
- Brands data comes from seed. You do not hardcode Jade's tone in React — render the API.
- If polling forever, M1's pipeline is stuck; show elapsed time and `failed` is M1's job. You just display `status`.

## Done for demo

Speaker can fill the Studio form in 20 seconds, see Running → Done, click into an asset, then later open Insights and point at the four numbers plus a lesson row.
