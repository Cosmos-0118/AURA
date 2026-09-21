# AURA

AURA is an AI-assisted marketing operations dashboard:

```text
campaign -> brand-specific draft -> compliance -> human review -> saved lesson
```

It is a five-person, eight-hour hackathon build. It is not a chatbot, autonomous
agent swarm, publisher, or full marketing suite.

## Start here

- Everyone: [8-hour team plan](docs/TEAM-PLAN.md)
- Your coding agent: [repository rules](AGENTS.md)
- Your exact assignment: [member role cards](docs/members/)
- Frozen integration shapes: [contracts](docs/03-CONTRACTS.md)
- Local environment: [setup](docs/02-SETUP.md)

The platform scaffold is already complete on `main`. Do not recreate the API,
database, typed client, or navigation. Start the feature work assigned in the
team plan.

## Run locally

```bash
# terminal 1, from repo root
cd api
uv sync
uv run uvicorn main:app --reload --port 8000

# terminal 2, from repo root
cd web
bun install
bun run dev
```

- Dashboard: http://localhost:3000
- API docs: http://localhost:8000/docs
- Health: http://localhost:8000/api/health

Copy `.env.example` to `.env` and `web/env.example.txt` to `web/.env.local`.
Never commit real keys. Keep `AURA_MOCK_AGENTS=true` until the deterministic
end-to-end path works.

## Demo promise

The reliable demo is the seeded failed post: inspect its compliance evidence,
reject it, and show the saved lesson in Insights. Live content generation is the
second half of the story, not a dependency for the first half.
