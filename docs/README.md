# AURA documentation

This is the implementation-oriented handoff set for AURA. It is based on the
current source tree, launcher scripts, manifests, database code, and tests.

## Read in this order

1. [Getting started and runbook](getting-started.md)
2. [Architecture and request flows](architecture.md)
3. [Configuration](configuration.md)
4. [Data and storage](data-and-storage.md)
5. [API and frontend integration](api.md)
6. [Testing and development](testing.md)
7. [Operations and troubleshooting](operations.md)
8. [Security, scope, and limitations](security-and-scope.md)
9. [Demo walkthrough](demo.md)

## Specialized references

- [Competitor intelligence: how it works](../competitor-intelligence/docs/01-HOW-IT-WORKS.md)
- [Competitor intelligence: how it runs](../competitor-intelligence/docs/02-HOW-IT-RUNS.md)
- [Buffer publishing and public media](buffer-publishing.md)
- [Database folder notes](../db/README.md)

The root README is the short entry point. API behavior is ultimately defined by
the route modules in api/routes, the Pydantic models in api/schemas.py, and the
generated OpenAPI document at /openapi.json when the API is running.

## Documentation maintenance rule

When changing a route, environment variable, launcher command, database table,
background worker, or externally visible workflow, update the corresponding
document in the same change. If a document conflicts with the code, the code
and generated API schema win until the document is corrected.
