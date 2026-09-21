# Current architecture

This describes the scaffold already on `main`. For assignments and timing, use
[TEAM-PLAN.md](TEAM-PLAN.md). For exact shapes, use
[03-CONTRACTS.md](03-CONTRACTS.md).

## Runtime

```text
Next.js dashboard
  M1 Overview | M2 Review | M3 Studio/Brands/Insights
                  |
             typed REST client
                  |
              FastAPI routes (M1)
                  |
              run_pipeline (M1)
              /              \
     generate_content (M4)   compliance + lessons (M5)
              \              /
               Supabase Postgres
```

There is one frontend, one FastAPI process, and one database. Background campaign
work uses FastAPI `BackgroundTasks`. There is no LangGraph, Redis, Celery, Kafka,
auth service, or second datastore.

## Campaign flow

1. M3 posts `CampaignCreate` to `/api/campaigns`.
2. M1 inserts a campaign with status `running` and schedules `run_pipeline`.
3. The pipeline retrieves recent M5 lessons.
4. M4 returns requested `GeneratedAsset` objects.
5. M5 checks every body; M1 stores the asset and compliance result.
6. A failed check gives the asset status `compliance_failed`; otherwise it becomes
   `pending_review`. Both appear in M2's queue.
7. The campaign becomes `completed`, or `failed` with an error.

`queued` exists in the database contract but the current create route inserts
`running` immediately.

## Review and learning flow

```text
GET queue -> inspect asset + compliance
          -> approve
          -> edit and approve -> review row + lesson
          -> reject           -> review row + lesson
```

Humans are the final authority. A compliance failure is visible and reviewable;
it is never published automatically. Approved rows are the output boundary for a
future publisher, but publishing is not in this sprint.

## Reliability path

`AURA_MOCK_AGENTS=true` makes `graph.py` use `api/agents/_stubs.py`. With the flag
off, `graph.py` imports M4/M5 modules and falls back to stubs if those imports are
absent. M4/M5 also keep deterministic behavior for provider failures. The demo is
therefore not dependent on Gemini availability.

## Ownership boundaries

- M1 owns persistence, orchestration, REST, shared frontend client/types, nav,
  Overview, and integration.
- M2 owns Review and Library UI.
- M3 owns Studio, Brands, and Insights UI.
- M4 owns content generation and content prompts.
- M5 owns compliance, lessons, rules, and compliance prompts.

Only M1 changes shared contracts. M2/M3 communicate through shared client types;
they do not import each other's components. M4/M5 expose plain functions and do
not import FastAPI or write content assets.

## Deliberate placeholders

Competitor scan, regenerate, and localize currently return 501. Leads and
competitor list routes may return seeded database rows, but their active agent
workflows and screens are out of scope. The generic starter Products, Users, and
chart code is reference material, not product architecture.
