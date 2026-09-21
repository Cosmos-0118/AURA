# Team Member 2 — Review workflow owner

## Mission

Build the strongest demo screen: a reviewer sees the asset and its compliance
evidence, then approves, edits, or rejects it. After that loop is reliable, add a
small approved-content Library.

Read `AGENTS.md`, `docs/TEAM-PLAN.md`, Contracts sections 1, 6, 7, and 10, then
this card.

## Branch and owned paths

Branch: `feat/m2-review-ui`

```text
web/src/features/review/**
web/src/features/library/**
web/src/app/dashboard/review/**
web/src/app/dashboard/library/**
web/src/components/aura/m2/**
```

Import types and functions from `web/src/lib/api/`. Do not edit that folder,
duplicate its interfaces, or call `fetch()` directly.

## Required routes

### `/dashboard/review`

Use `listAssets({ status: "queue" })`. Show:

- brand, platform, variant, short copy preview, compliance result/risk, and age;
- filters for brand, platform, and compliance result;
- obvious high-risk styling without relying only on color;
- loading skeleton, useful API error with retry, and a real empty state;
- a link to `/dashboard/review/[id]` for every item.

### `/dashboard/review/[id]`

Use `getAsset(id)`. The page needs three clear areas:

1. Full title/body/hashtags and brand/platform metadata.
2. Compliance verdict, risk, each issue's text/reason/rule, and suggested revision.
3. Human decision controls.

Decision behavior:

- **Approve:** `approveAsset(id)`.
- **Edit and approve:** editable copy, then
  `approveAsset(id, { edited_body, reason_tag, note })`.
- **Reject:** require a `reason_tag`; `note` stays optional; call `rejectAsset`.
- On success, show a toast and return to or refresh the queue.
- Disable repeated submissions and surface API failures without losing edits.

`compliance_failed` assets are reviewable. Do not hide or auto-reject them.

## Stretch after the checkpoint

Create `/dashboard/library` using `listAssets({ status: "approved" })`. A simple
filterable list/detail link is enough. Ask M1 to add the nav item; do not edit nav
yourself.

Do not implement regenerate unless M1 explicitly says the endpoint is no longer
501. Do not build competitors, publishing, scheduling, or analytics.

## Work order

1. Queue and detail with contract-shaped data.
2. Wire read calls to the existing client.
3. Wire approve and reject.
4. Add edit-and-approve and robust mutation states.
5. Test against the seeded failed asset.
6. Only then build Library and visual polish.

## Acceptance

- The seeded Instagram asset displays `FAIL`, `HIGH`, and `CLAIM_001`.
- Reject cannot submit without a reason tag, but can submit with an empty note.
- Reject removes the item from the queue after success.
- Edit-and-approve sends `edited_body` and preserves text on an API error.
- All screens handle loading, empty, success, and error states.
- `bun run typecheck` and `bun run build` pass.

## Give your coding agent this task

```text
Read AGENTS.md, docs/TEAM-PLAN.md, docs/members/TEAM-MEMBER-2.md, and the linked
contract sections. Work only in M2-owned paths. Build Review list and detail,
then approve/edit/reject using the existing typed client. Include loading, empty,
error, and duplicate-submit states. Prove the seeded FAIL workflow before doing
Library or polish. Never edit shared API, nav, types, or shadcn primitives.
```
