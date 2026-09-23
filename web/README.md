# AURA web application

The web directory contains the Next.js dashboard for AURA. It is not the
upstream dashboard template anymore; use the repository-level documentation:

- [Getting started](../docs/getting-started.md)
- [Architecture](../docs/architecture.md)
- [API and frontend integration](../docs/api.md)
- [Testing](../docs/testing.md)

Useful local commands from this directory:

~~~bash
bun install --frozen-lockfile
bun run dev
bun run typecheck
bun run lint
bun run build
~~~

The browser calls the FastAPI service through NEXT_PUBLIC_API_URL. The web
application does not own the database, provider credentials, or publishing
integrations.
