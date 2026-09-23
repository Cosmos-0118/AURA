# AURA deployment note

The old frontend-template deployment instructions are not authoritative for
AURA. A deployable environment must account for the Next.js frontend, FastAPI
API, database, local or durable media storage, background workers, and optional
competitor collectors as one system.

For the supported local runtime, use the repository-level
[getting started guide](../../docs/getting-started.md), [architecture guide](../../docs/architecture.md),
and [security/scope notes](../../docs/security-and-scope.md). There is
currently no production deployment recipe in this repository.
