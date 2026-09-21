# Team Member 4 — Content engine owner

## Mission

Produce safe, useful marketing drafts whose brand voices are unmistakably
different. The function must work deterministically without Gemini and may use
Gemini to improve quality when configured.

Read `AGENTS.md`, `docs/TEAM-PLAN.md`, Contracts sections 1, 4, 5, and 9, then
this card.

## Branch and owned paths

Branch: `feat/m4-content`

```text
api/agents/content.py
api/agents/localize.py
api/prompts/content/**
api/tests/content/**
```

Do not edit schemas, routes, graph, dependencies, M5 files, or `.env`.
Localization is reserved but out of this sprint; a contract-compatible no-op is
enough if the file is required.

## Frozen public functions

```python
def generate_content(req: ContentRequest) -> list[GeneratedAsset]: ...

def localize(
    asset: GeneratedAsset,
    language: str,
    country: str,
    brand_id: str,
) -> GeneratedAsset: ...
```

Import `ContentRequest` and `GeneratedAsset` from `api/schemas.py`. Never return a
dict where the contract requires a model.

## Required behavior

- Return two LinkedIn variants (`A` and `B`) for a LinkedIn request.
- Return only requested platforms.
- Use the request's topic, country, goal, research summary when present, and
  lesson strings.
- Keep hashtags as a list without `#`-stuffing the body.
- Avoid claims such as `guaranteed`, `100% covered`, `zero risk`, or invented
  statistics.
- Never let a missing key, timeout, 429, invalid JSON, or empty model response
  escape from `generate_content`; return deterministic variants instead.

Brand voices:

| Brand | Voice |
|---|---|
| Jade | Precise, premium B2B specialist; jewellery, craft, inventory, discretion |
| DoctorShield | Calm, educational colleague; clinics, patients, time, paperwork |
| Jaguar Transit | Operational and technology-led; transit, custody, speed, security |

The deterministic fallback is production behavior for the demo, not a temporary
TODO. Build it first and test it directly. Then add a prompt-backed Gemini path
using existing dependencies and environment variables.

## Prompt/output rules

- Keep prompt templates under `api/prompts/content/`.
- Ask for structured output that can be validated into `GeneratedAsset`.
- Treat model output as untrusted: validate fields, requested platform, and body.
- If one variant is invalid, use a deterministic replacement rather than failing
  the whole campaign.
- Lessons guide the copy; they are not pasted verbatim into the final post.

## Stretch after the checkpoint

Add two short Instagram caption variants through the same path. Do not implement
X, blog, reel, localization, research, or media generation.

## Acceptance

- A local call for each brand returns valid Pydantic objects.
- The three brand outputs are recognizably different without reading the brand ID.
- LinkedIn returns A and B, and variants are not identical.
- A supplied lesson changes or constrains the copy.
- Mock/missing-key/network-failure paths all return usable output.
- Focused tests under `api/tests/content/` and the targeted backend compile check pass.

## Give your coding agent this task

```text
Read AGENTS.md, docs/TEAM-PLAN.md, docs/members/TEAM-MEMBER-4.md, and the linked
contract sections. Work only in M4-owned paths. Implement deterministic A/B
LinkedIn generation for all three voices first, with exact Pydantic return types
and lesson-aware output. Then add a validated Gemini path that always falls back
on missing keys, timeouts, 429s, malformed output, or any provider error. Add
focused tests. Do not change contracts, routes, graph, or dependencies.
```
