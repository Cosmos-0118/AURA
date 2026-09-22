# AURA

AURA is an AI-assisted marketing operations dashboard:

```text
campaign -> brand-specific draft -> compliance -> human review -> saved lesson
```

It is a five-person, eight-hour hackathon build. It is not a chatbot, autonomous
agent swarm, publisher, or full marketing suite.

## Start here

- Competitor intelligence: [how it works](competitor-intelligence/docs/01-HOW-IT-WORKS.md)
- Runtime and launcher: [how it runs](competitor-intelligence/docs/02-HOW-IT-RUNS.md)

The dashboard and competitor-intelligence collector now run as one AURA
application. The collector package supplies monitoring and classification
logic; the AURA API owns the native dashboard and lifecycle.

## Run locally

The interactive launcher offers **Build only**, **Build + run**, and **Just run**:

```bash
./scripts/macos/start.sh
```

For direct commands:

```bash
# clean generated output, install locked dependencies, typecheck, and build
./scripts/macos/build.sh

# start both apps from the existing production build without rebuilding
./scripts/macos/aura.sh start

# start both apps in development mode with hot reload
./scripts/macos/aura.sh dev

# clean, build, and start the production frontend plus API
./scripts/macos/up.sh

# stop only processes started by the runner
./scripts/macos/stop.sh
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
