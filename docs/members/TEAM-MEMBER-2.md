# Team Member 2 — Review and Approval UI

You own the screen the judges will remember: the **Review Queue**. A human sees generated copy, sees why compliance flagged it, and can approve, edit, or reject with a reason. That is the product.

You do not call Gemini. You do not edit Python. You consume `web/src/lib/api`.

## Read these first

1. [../00-START-HERE.md](../00-START-HERE.md)
2. [../02-SETUP.md](../02-SETUP.md)
3. [../03-CONTRACTS.md](../03-CONTRACTS.md) — especially `Asset`, `ComplianceResult`, mock payload §10
4. [../04-WORKFLOW-RULES.md](../04-WORKFLOW-RULES.md)
5. [../../AGENTS.md](../../AGENTS.md)

## Your branch

`feat/m2-review-ui`

Wait for M1's "contracts are in main" before you write feature code. Until then: install bun, run the dashboard, read this file.

## Files you own

```text
web/src/features/review/**
web/src/features/library/**
web/src/app/dashboard/review/**
web/src/app/dashboard/library/**
web/src/components/aura/m2/**
```

Copy **patterns** from the starter's product table (`web/src/features/products`) and users table. Do not copy product types.

## Never touch

```text
web/src/lib/api/**              (import only)
web/src/config/nav-config.ts    (M1 already added Review + Library)
web/src/components/ui/**        (import only)
web/src/features/studio/**
web/src/features/brands/**
web/src/features/insights/**
api/**
```

If a type is missing, message M1. Do not invent `interface MyAsset`.

---

## Screen spec — Review Queue (`/dashboard/review`)

### List

Reuse the starter data table.

Columns:

| Column | Field |
|---|---|
| Brand | `brand_id` (show name: Jade / DoctorShield / Jaguar Transit) |
| Platform | `platform` |
| Type | `content_type` + `variant` |
| Language | `language` |
| Risk | `compliance.risk` badge: HIGH red, MEDIUM amber, LOW green, none gray |
| Verdict | `compliance.result` |
| Status | `status` |
| Created | `created_at` relative |

Default filter: `listAssets({ status: "queue" })` so you get `pending_review` + `compliance_failed`.

Row click → detail route `/dashboard/review/[id]`.

Empty state: "No assets waiting. Create a campaign in Studio." Do not show a spinner forever.

### Detail (the star UI)

Layout: two columns on desktop, stacked on mobile.

**Left — asset**

- Header: `{Brand} • {Platform} • {Language}` and a risk badge
- Title if any
- Body as readable text. If `content_type === "carousel"`, `JSON.parse(body)` and show numbered slides. If parse fails, show raw body.
- Hashtags as chips
- Optional `media_url` image

**Right — compliance**

- Result + risk
- Checklist feel: each `issues[]` row shows quoted `text`, `reason`, `rule_id`
- If `issues` empty and PASS: "No issues found"
- `suggested_revision` in a muted box

**Bottom — feedback**

- Select `reason_tag` (the enum from contracts)
- Textarea `note`
- Optional: body is a textarea so the reviewer can edit in place
- Buttons: **Reject** | **Save edit** (PATCH) | **Approve**
- Extra: **Regenerate** (calls `regenerateAsset(id)`, then toast + stay or go back to list)

Approve may send `{ edited_body }` if the textarea differs from original.

Reject should require a `reason_tag`. Disable the button until one is chosen.

After success: toast, go back to the queue (the item should disappear).

Match the wireframe in Concept.md §20 — you do not need pixel-perfect, you need that information architecture.

---

## Screen spec — Library (`/dashboard/library`)

Same table component, different default filters: tabs **Approved** | **Rejected** | **All**.

Row opens a read-only detail (reuse the left+right layout, hide action buttons or show "Already {status}").

Phase 2: show latest lesson note if you want — not required. Prefer linking nowhere; keep it simple.

---

## Phases

### Phase 1 (T+3–T+12) — must have

| Task | Acceptance |
|---|---|
| Queue table | Seeded FAIL Instagram appears without running a campaign |
| Detail page | Body + compliance issues + suggested_revision visible |
| Approve | Status becomes approved; item leaves queue |
| Reject + tag + note | Item leaves queue; no 500 |
| Loading and error | Failed fetch shows retry, not a white screen |

### Phase 2

| Task | Acceptance |
|---|---|
| Edit in place then approve | PATCH or approve with `edited_body` |
| Regenerate button | New asset shows up in queue |
| Library page | Approved/rejected tabs work |
| Highlight flagged span | If `issues[0].text` is a substring of `body`, mark it (simple `<mark>`, not a fancy editor) |

### Phase 3

Polish only: keyboard shortcut for approve, badge counts on the sidebar (sidebar is M1 — ask them to read `assets_pending` from metrics if you want a number). You may pass the count via the review page title `Review Queue (12)` using `getMetrics().assets_pending`.

---

## React Query keys (do not collide with M3)

```ts
["assets", params]
["asset", id]
["metrics"]
```

After approve/reject/regenerate: `invalidateQueries({ queryKey: ["assets"] })` and `["asset", id]`.

---

## Cursor agent prompts (paste as-is)

### Prompt A — queue table

```text
You are Team Member 2 for AURA. Read AGENTS.md and docs/03-CONTRACTS.md.

Build the Review Queue at web/src/app/dashboard/review/page.tsx using a feature module in web/src/features/review/.

Copy the data-table pattern from web/src/features/products (query, columns, pagination) but use Asset from @/lib/api/types and listAssets from @/lib/api/client.

Call listAssets({ status: "queue" }).

Columns: brand_id, platform, content_type, variant, language, compliance.risk, compliance.result, status, created_at.

Row navigates to /dashboard/review/[id].

Do not edit web/src/lib/api, nav-config, or components/ui files. Put extra components in web/src/components/aura/m2/ or web/src/features/review/.

Empty state when the list is [].
```

### Prompt B — detail + actions

```text
Read docs/members/TEAM-MEMBER-2.md screen spec and contracts §10 mock payload.

Build web/src/app/dashboard/review/[id]/page.tsx.

Two columns:
- Left: brand, platform, language, title, body (carousel JSON slides if content_type is carousel), hashtags.
- Right: compliance result, risk, issues list (text, reason, rule_id), suggested_revision.

Bottom: reason_tag select (TOO_SALESY, WRONG_CTA, UNSUPPORTED_CLAIM, WRONG_BRAND_VOICE, BAD_LOCALIZATION, OTHER), note textarea, editable body textarea.

Buttons:
- Reject → rejectAsset(id, { reason_tag, note, edited_body })
- Approve → approveAsset(id, { reason_tag, note, edited_body, approved_by: "reviewer" })
- Save edit → patchAsset(id, { body })
Reject disabled without reason_tag.

Invalidate ["assets"] and ["asset", id] on success. Toast. Navigate back to /dashboard/review.

If issue.text is in body, wrap matches in <mark>.

Only edit files under web/src/features/review, web/src/app/dashboard/review, web/src/components/aura/m2.
```

### Prompt C — library

```text
Add Content Library under web/src/features/library and web/src/app/dashboard/library/page.tsx.

Tabs: Approved (status=approved), Rejected (status=rejected), All (no status).

Reuse the review table columns. Detail can be a sheet or /dashboard/library/[id] read-only (no approve buttons).

Import only from @/lib/api. Do not touch M3 folders or api/.
```

### Prompt D — regenerate

```text
On the review detail page add a Regenerate button that calls regenerateAsset(id) from @/lib/api/client.

On success toast "New draft queued" and invalidate ["assets"].

If the API returns 404/501, toast "Regenerate not wired yet" — do not crash.

Stay in M2 folders.
```

---

## How you combine with others

- M1's client already exists. If `listAssets` is missing, you are before T+3 — wait.
- M3's Studio is what fills the queue. You can develop against seed/demo rows without them.
- You never import M3 feature code.

## Done for demo

A judge can open a FAIL Instagram post, see **"Guaranteed protection"** called out, reject it with **Unsupported claim**, and the queue updates.
