# Testing and development workflow

## Focused checks

Run backend tests from api/:

~~~bash
cd api
uv sync --frozen
uv run pytest
~~~

The backend suite covers compliance rules, lessons, content generation,
campaign/review behavior, video, leads, Buffer/media publishing, and API
contracts. Tests that invoke external providers should mock the provider or
require explicit local credentials; do not run real publishing tests against a
production account.

Run the competitor intelligence tests from its package directory:

~~~bash
cd competitor-intelligence
PYTHONPATH=. uv run --with pytest pytest
~~~

The collector package has no runtime dependencies in its pyproject and its
package is a source tree rather than an installed wheel, so PYTHONPATH=. is
intentional. The explicit --with pytest keeps the test runner isolated.

Run frontend checks from web/:

~~~bash
cd web
bun install --frozen-lockfile
bun run typecheck
bun run lint
bun run build
~~~

The launcher build command performs the backend dependency sync and compile,
frontend lockfile install, typecheck, and production build. It does not run
pytest or frontend lint, so run those separately before handoff.

## Integration checks

The MySQL/media acceptance script requires a running MySQL database with the
schema and suitable local provider/demo configuration:

~~~bash
cd api
uv run python ../scripts/test_mysql_persistence.py
~~~

It writes campaign/media/review state. Run it only against a disposable
database and storage directory.

For a live stack smoke test:

~~~bash
./scripts/macos/aura.sh dev
curl --fail http://localhost:8000/api/health
curl --fail http://localhost:8000/api/media/config
~~~

Then load the dashboard and exercise the demo path in demo.md.

## Test isolation

Prefer a temporary AURA_INTELLIGENCE_DB and a disposable storage directory for
collector/integration work. PYTEST_CURRENT_TEST disables startup refresh
workers, but it does not make external provider calls safe. Set
AURA_MOCK_AGENTS=true and DEMO_MODE=true for deterministic local generation.

The repository currently has no obvious repository-level CI workflow. A
complete pre-handoff validation should therefore include backend pytest,
competitor pytest, frontend typecheck/lint/build, and a live API health check.
