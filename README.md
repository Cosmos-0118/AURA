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

The interactive launcher offers **Build only**, **Build + run**, and **Just run**:

```bash
./scripts/start.sh
```

For direct commands:

```bash
# clean generated output, install locked dependencies, typecheck, and build
./scripts/build.sh

# start both apps from the existing production build without rebuilding
./scripts/aura.sh start

# start both apps in development mode with hot reload
./scripts/aura.sh dev

# clean, build, and start the production frontend plus API
./scripts/up.sh

# stop only processes started by the runner
./scripts/stop.sh
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
