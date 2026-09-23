# AURA

AURA is an AI-assisted marketing operations dashboard for turning brand-aware
campaign briefs into reviewable, compliant content packages.

    brief -> brand voice -> generated content -> compliance checks -> human review
          -> saved lesson -> optional approved publication

The repository also contains an evidence-first competitor intelligence lane,
lead discovery, image/video generation, watermarking, and Buffer publishing.
It is an internal/hackathon MVP: there is no authentication or authorization
layer, and the local runtime is the reference deployment.

## Start here

The authoritative project documentation is in [docs/README.md](docs/README.md):

- [Getting started and runbook](docs/getting-started.md)
- [Architecture and request flows](docs/architecture.md)
- [Configuration and environment variables](docs/configuration.md)
- [Data, storage, and database setup](docs/data-and-storage.md)
- [API and frontend integration](docs/api.md)
- [Testing and development workflow](docs/testing.md)
- [Operations and troubleshooting](docs/operations.md)
- [Security, scope, and known limitations](docs/security-and-scope.md)
- [Reliable demo walkthrough](docs/demo.md)

Specialized guides:

- [Competitor intelligence: how it works](competitor-intelligence/docs/01-HOW-IT-WORKS.md)
- [Competitor intelligence: how it runs](competitor-intelligence/docs/02-HOW-IT-RUNS.md)
- [Buffer publishing and public media](docs/buffer-publishing.md)

Concept.md is the historical product/design brief. It contains ideas that are
not the current implementation, such as LangGraph and Supabase. Use the code
and the docs above as the source of truth.

## Quick start

Prerequisites: Python 3.12+, uv, Bun, and Docker Compose when competitor
collectors are enabled.

    cp .env.example .env
    cp web/env.example.txt web/.env.local
    ./scripts/macos/aura.sh up

Then open:

- Dashboard: http://localhost:3000
- FastAPI Swagger UI: http://localhost:8000/docs
- API health: http://localhost:8000/api/health

The default local configuration uses deterministic/demo generation and a local
SQLite database. See the configuration guide before adding provider keys or
enabling external publishing.

> Buffer cannot fetch images or videos from localhost. Before any Buffer
> publish, start the reserved tunnel in a separate terminal and keep it
> running for the entire publish session:
>
>     ngrok http --url=perceptually-homocentric-lindy.ngrok-free.dev 8000
>
> Set MEDIA_PUBLIC_BASE_URL to
> https://perceptually-homocentric-lindy.ngrok-free.dev and verify
> /api/media/config. ngrok forwards the API port, while AURA restricts that
> public host to media reads and health. Use demo/test credentials and stop it
> immediately after the publish test. Full details are in
> docs/buffer-publishing.md.

## Common commands

    ./scripts/macos/aura.sh dev    # API + Next.js with hot reload
    ./scripts/macos/aura.sh build  # clean, install locked deps, typecheck, build
    ./scripts/macos/aura.sh start  # run an existing production frontend build
    ./scripts/macos/aura.sh stop   # stop tracked processes and collector services

Windows equivalents are under scripts/windows/; for example,
.\scripts\windows\aura.ps1 dev and .\scripts\windows\up.ps1. The complete
command matrix and manual two-terminal fallback are in the runbook.

## Demo path

For a deterministic walkthrough, create or load a campaign, inspect the
compliance/review evidence, reject it with a reason such as TOO_SALESY, and
confirm that the reviewer correction appears as a saved lesson. The exact
fresh-database and MySQL demo options are documented in docs/demo.md.
