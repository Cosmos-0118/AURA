# Security, scope, and known limitations

## Current security boundary

AURA is an internal MVP, not a production multi-tenant service:

- There is no authentication, authorization, tenant isolation, or user audit
  identity layer.
- The local FastAPI origin serves storage through unauthenticated /media and
  /storage mounts.
- CORS is configured for local origins with broad methods and headers.
- Provider credentials are backend environment variables, but publishing and
  email are real external side effects when configured.
- Lead records may contain public contact information and email workflow data.
- Lead review routes record a reviewer name but do not authenticate that
  identity. Approval is a local workflow guard, not role-based access control.

Do not expose the default API, changedetection UI, or static media routes to
the public internet without adding an access-control and deployment layer.
The documented local Buffer tunnel forwards the FastAPI port, but AURA now
recognizes the configured `MEDIA_PUBLIC_BASE_URL` host and only allows
read-only `/media/*` requests plus `GET /api/health` on that public origin.
The local origin remains an unauthenticated development API. Treat the tunnel
as a short-lived development exposure, use demo/test credentials, keep Buffer
and Gmail provider keys unset unless the side effect is intentional, never use
it on a shared or sensitive machine, and stop it immediately after the publish
test. Production still requires a real access-control and deployment layer.

## Secrets

Never commit .env, web/.env.local, API keys, Gmail app passwords, Buffer
credentials, or public tunnel credentials. Do not put secrets in
NEXT_PUBLIC_* variables. Review logs before sharing them because provider
errors and lead/email failures can contain operational context.

## External side effects

Treat these as approval-gated operations:

- Buffer can queue/publish to LinkedIn, Instagram, or X.
- Gmail configuration can send messages to lead addresses.
- FAL/Groq/Gemini/Hunter calls can incur provider cost and transmit prompt or
  public-source data.
- Competitor collectors make repeated requests to third-party sites.
- Lead discovery can query Overture and, when configured, Hunter; website
  verification requests only public HTTP(S) pages and honors robots.txt.

The app validates final watermarked media and public reachability before Buffer
publication, but that is not a replacement for provider-side permissions,
legal review, or human approval.

## Compliance disclaimer

The insurance compliance gate is a deterministic product rubric for catching
known risky marketing language. A PASS is not legal advice, regulatory
approval, policy coverage confirmation, or a guarantee that copy is safe.
Human review remains required.

## Scope boundaries

The current repository does not provide:

- production deployment orchestration for API, frontend, workers, database, and
  media as one managed service;
- authentication or role-based review permissions;
- durable object storage for media;
- guaranteed delivery semantics for external provider calls;
- a repository-level CI workflow;
- LangGraph/Supabase/PostgreSQL as the active architecture.

These are architectural follow-ups, not undocumented capabilities.
