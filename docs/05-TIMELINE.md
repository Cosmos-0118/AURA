# Eight-hour timeline

The scaffold is complete. T+0 is when feature work begins, not repository setup.

The authoritative schedule, assignments, checkpoints, merge order, and cut order
are in [TEAM-PLAN.md](TEAM-PLAN.md).

## Checkpoints

| Time | Required result |
|---|---|
| T+0:30 | All five branches boot; setup blockers are posted with exact errors |
| T+2:30 | First PR from every member; each lane is usable locally |
| T+4:30 | Full seeded reject-to-lesson and campaign-to-review loop works on `main` |
| T+6:30 | Feature freeze; build checks pass; demo data reset |
| T+8:00 | Two rehearsals and fallback screenshots complete |

## Work by phase

- **0:00–0:30:** branch, environment, boot.
- **0:30–2:30:** M1 integration/Overview, M2 Review reads, M3 Studio/Brands,
  M4 deterministic content, M5 deterministic compliance/lessons.
- **2:30–4:30:** wire writes, polling, Insights, real module integration, and
  safe Gemini paths.
- **4:30–6:30:** finish acceptance checks, errors, responsive behavior, tests,
  then at most one owned stretch item.
- **6:30–8:00:** no features; merge, reset, rehearse, screenshots, bug fixes.

If behind, preserve Review, decisions, lessons, Brands/Insights, deterministic
generation, and Studio—in that order. Cut Gemini and every stretch feature first.
