# Troubleshooting

Try these before asking the team. If you are still stuck after **15 minutes**, ping Team Member 1 with the **exact command and the exact error**. In a 6–8 hour sprint, a silent hour is a lost feature — M1's job description includes sitting with you.

## 1. `bun: command not found`

Install failed or the terminal was not restarted.

```bash
curl -fsSL https://bun.sh/install | bash
source ~/.zshrc
bun -v
```

## 2. `uv: command not found`

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.zshrc
uv --version
```

## 3. Frontend runs but API calls fail (CORS / Network Error)

- API not running. Start `cd api && uv run uvicorn main:app --reload --port 8000`.
- `NEXT_PUBLIC_API_URL` missing. Must be `http://localhost:8000` in `web/.env.local`. Restart `bun run dev` after changing env.
- CORS: M1 must allow `http://localhost:3000` in FastAPI. If you are not M1, do not patch `main.py` — ping M1.

## 4. `GET /api/brands` is empty or 500

- Schema not applied. M1: run `db/schema.sql` in Supabase SQL editor.
- Seed not applied. Run `db/seed.sql`.
- `DATABASE_URL` wrong (password special characters need URL encoding).
- SSL: append `?sslmode=require` to the URL.

## 5. `password authentication failed` / could not connect to Supabase

Use the connection string from **Project Settings → Database**. Prefer port **5432** direct, or the pooler on **6543** with `?sslmode=require`. Do not mix them. IPv6-only networks: use the pooler host.

## 6. Gemini `429` / `RESOURCE_EXHAUSTED`

You are sharing a key or looping. Use **your** key. Set `AURA_MOCK_AGENTS=true` while iterating on UI. M4/M5: add a 1-retry with 2s sleep, then return a mock on failure so the pipeline still completes.

## 7. Gemini returns markdown fences around JSON

```text
```json
{ ... }
```
```

Strip fences before `json.loads`. Retry once with "Return JSON only, no markdown." If still bad, return the mock. Never crash the request.

## 8. `ModuleNotFoundError: agents` or wrong imports

Run uvicorn from **`api/`**:

```bash
cd api
uv run uvicorn main:app --reload --port 8000
```

Not from the repo root unless `PYTHONPATH` is set. Do not add sys.path hacks in every file.

## 9. Merge conflict in `bun.lock` or `uv.lock`

```bash
git checkout origin/main -- web/bun.lock
cd web && bun install && bun add <the package you needed>
```

Same idea for `api/uv.lock` with `uv lock`. Do not hand-edit lockfiles.

## 10. You edited a file you do not own

```bash
git checkout origin/main -- path/to/file
```

If you already committed, `git revert` that file in a new commit. Do not rebase.

## 11. Next.js 404 on `/dashboard/review`

M2 must add `web/src/app/dashboard/review/page.tsx`. M1 adds the nav item only. If nav is missing, ping M1 — do not edit `nav-config.ts`.

## 12. Hydration / React Query errors after copying the product table

Copy the **pattern** from `web/src/features/products`, not the product types. Your query keys must be `["assets", status]` etc., matching `web/src/lib/api`. Do not import `Product` types into review.

## 13. `check_compliance` always PASS

Banned terms file not loaded. Path is `api/rules/banned_terms.yaml` relative to the `api/` working directory. Print `issues` in a temporary test:

```bash
cd api && uv run python -c "from agents.compliance import check_compliance; print(check_compliance('Guaranteed protection', 'jade', 'instagram'))"
```

Expect FAIL. If the function does not exist yet, you are calling the stub — that is OK until M5 lands.

## 14. Campaign stays `running` forever

Background task crashed. Watch the uvicorn terminal. Typical: Gemini exception not caught. M1 wraps `graph.py` in try/except and sets `campaigns.status=failed` with `error`. M4/M5 must not raise past a mock fallback.

## 15. Port 3000 or 8000 already in use

```bash
lsof -i :8000
kill <pid>
```

Do not switch ports unless you also change `NEXT_PUBLIC_API_URL` and CORS. Prefer killing the old process.

## 16. Clerk still in the dashboard

Cleanup was skipped. M1 re-runs `bun run cleanup --list` and removes clerk. Members: do not add `@clerk` back.

## 17. "My agent refactored schemas.py"

Stop. Revert. Paste `AGENTS.md` into the chat and say "you may only edit files in my ownership table." Then continue.

## 18. Someone started crawl / FFmpeg / leads

Stop. Those are out of scope for 6–8 hours. Revert the files. Go back to your Must list in `docs/05-TIMELINE.md`.

## 19. Demo laptop has old seed

```text
Re-run db/seed.sql then db/demo.sql in Supabase SQL editor.
Hard refresh the browser.
```

## 20. Reject returns 500 (`null value in column "note"`)

`lessons.note` is `NOT NULL` and the reviewer left the note box empty. M1 passes `note or reason_tag` into `record_lesson`; M5 coalesces again inside it. Rehearse the reject **with an empty note** so this cannot surprise you on stage.

## 21. Insights is blank or `/api/metrics` 500s

Division by zero on an empty database. Every rate returns `0.0` when its denominator is 0. M1 owns this SQL — M3 must not paper over it with fake numbers.

## 22. Your agent suggests Clerk, Sentry, or Recharts dashboards out of nowhere

The Kiranism starter ships its own `AGENTS.md` and `CLAUDE.md`. If they were not deleted after the clone, they are sitting at `web/AGENTS.md` and Cursor applies them to every file under `web/`. Delete them, then re-open the chat.
