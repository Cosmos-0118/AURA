# Workflow rules

These rules exist so five Cursor agents do not rewrite the same file. Follow them even when it feels slower. Merge fights cost more than waiting 10 minutes for Team Member 1.

## Ownership (absolute)

Copy of the table in `AGENTS.md`. If you need a file that is not in your row, you do not edit it.

| Who | Allowed paths | Branch |
|---|---|---|
| **M1** | `db/**`, `api/main.py`, `api/db.py`, `api/schemas.py`, `api/graph.py`, `api/routes/**`, `api/agents/_stubs.py`, `api/pyproject.toml`, `api/uv.lock`, `web/src/lib/api/**`, `web/src/config/nav-config.ts`, `web/src/app/dashboard/layout.tsx`, `docker-compose.yml`, `.env.example`, `README.md` | `feat/m1-platform` |
| **M2** | `web/src/features/review/**`, `web/src/features/library/**`, `web/src/app/dashboard/review/**`, `web/src/app/dashboard/library/**`, `web/src/components/aura/m2/**` | `feat/m2-review-ui` |
| **M3** | `web/src/features/studio/**`, `web/src/features/brands/**`, `web/src/features/insights/**`, `web/src/features/competitors/**`, `web/src/features/leads/**`, `web/src/app/dashboard/studio/**`, `web/src/app/dashboard/brands/**`, `web/src/app/dashboard/insights/**`, `web/src/app/dashboard/competitors/**`, `web/src/app/dashboard/leads/**`, `web/src/components/aura/m3/**` | `feat/m3-studio-ui` |
| **M4** | `api/agents/content.py`, `api/agents/localize.py`, `api/prompts/content/**` | `feat/m4-content` |
| **M5** | `api/agents/compliance.py`, `api/agents/lessons.py`, `api/agents/research.py`, `api/agents/leads.py`, `api/rules/**`, `api/prompts/compliance/**` | `feat/m5-compliance` |

**Nobody except M1** edits: `api/schemas.py`, `api/routes/**`, `web/src/components/ui/**`, `web/src/lib/api/**`, `docs/03-CONTRACTS.md`.

Frontend: if you need a helper used by two of *your* screens, put it in `web/src/components/aura/m2/` or `m3/`. Do not put it in `components/ui`.

## How to ask for a shared change

In the team channel, one message:

```text
CONTRACT CHANGE REQUEST
Need: <field or endpoint>
Why: <one sentence>
Who is blocked: M2 / M3 / M4 / M5
Suggested shape: { "foo": "string" }
```

M1 either:

- adds it to `schemas.py` + `docs/03-CONTRACTS.md` + `web/src/lib/api/types.ts` in one commit on `main`, or
- replies **no**, with the existing field you should use.

You do **not** add a local extra field "just for now". That is how the UI and API diverge.

## Git, every day

```bash
# start of a session
git checkout feat/mN-...
git fetch origin
git merge origin/main          # merge, never rebase

# ... work only in your folders ...

git add <your files only>
git commit -m "Add review reject dialog with reason tags"
git push -u origin HEAD
```

Then open a PR into `main`. **M1 merges all PRs.** Other members do not hit Merge.

### PR rules

- Title: `[M2] Review queue table`
- Body: what a reviewer can click, not a file list.
- If GitHub shows files you do not own, you accidentally edited someone else's zone. Revert those files before asking for merge.
- PRs should be mergeable at every checkpoint (T+6, T+14, T+24, T+34, T+42). Small PRs, often.

### Forbidden

- `git rebase`
- `git push --force`
- `git commit --no-verify`
- committing on `main`
- editing files in a teammate's PR "to help"

### Lockfile conflicts

**Frontend:** if `web/bun.lock` conflicts, take `main`'s lockfile, re-run `bun add <pkg>` on your branch, commit.

**Backend:** if `api/uv.lock` conflicts, take `main`, re-run `uv add <pkg>` (M4/M5: only if M1 agreed). Prefer asking M1 to add the dependency on `main` so only one person touches `pyproject.toml`.

**M4 / M5 extra Python packages:** message M1: `Need package: trafilatura — for research.py`. M1 adds it. You do not edit `pyproject.toml` unless M1 is asleep and you append **one line at the end** of the deps list, then tell M1.

## Mock-first protocol

Every public function / page ships in this order:

1. **Stub** — returns hardcoded data matching `docs/03-CONTRACTS.md`.
2. **Wired** — M1 routes or M2/M3 pages call it. Demo can already click.
3. **Real** — Gemini / SQL / crawl. Same return type.

Never skip (1). Never change the return type between (1) and (3).

M1 ships `api/agents/_stubs.py` at Hour 3 so `graph.py` runs even if M4/M5 have not pushed. When the real file exists, M1 deletes the stub import (one-line change in `graph.py`). M4/M5 still own the real file.

## Combining (why this is easy)

| Interface | Provider | Consumer |
|---|---|---|
| Pydantic models | M1 `schemas.py` | M4, M5, M1 routes |
| REST JSON | M1 `routes/` | M2, M3 via `web/src/lib/api` |
| Agent functions | M4, M5 | M1 `graph.py` only |
| Nav items | M1 `nav-config.ts` | Next.js layout |

No shared React context. No shared Python package besides `schemas.py`. No EventEmitter. If you think you need one, you are overcomplicating it.

## Communication defaults

- Team channel for contract requests and "I am blocked".
- Voice call at each checkpoint (15 min): merge, boot `main`, assign leftover.
- If someone is stuck > 45 minutes on env/install, they pair with M1. Do not silently rewrite the stack.

## Sleep (48h track)

Stagger so the repo is never empty:

| Window | Who sleeps | Who is awake |
|---|---|---|
| T+12 to T+18 | M1, M2 | M3, M4, M5 |
| T+20 to T+26 | M4, M5 | M1, M2, M3 |

If you only have 24 hours, skip staggered sleep. Take 90 minutes each around T+12 and keep M1 available.
