# Team Member 4 — Content Engine

You are the writer. You turn a `ContentRequest` into **LinkedIn** copy that sounds like **Jade**, **DoctorShield**, or **Jaguar Transit** — not like generic ChatGPT insurance.

You do **not** localize, do **not** make reels, do **not** run compliance, do **not** create HTTP routes. M1 calls `generate_content` from `run_pipeline`.

**Time: 6–8 hours. Must = LinkedIn A+B for 3 brands, lessons in the prompt, never raise. Skip Instagram/X/blog/localize/reel.**

## Read these first

1. [../00-START-HERE.md](../00-START-HERE.md)
2. [../02-SETUP.md](../02-SETUP.md)
3. [../03-CONTRACTS.md](../03-CONTRACTS.md) — `ContentRequest`, `GeneratedAsset`, function signatures §5
4. [../04-WORKFLOW-RULES.md](../04-WORKFLOW-RULES.md)
5. [../../AGENTS.md](../../AGENTS.md)

## Your branch

`feat/m4-content`

You can start **stubs** immediately, even before T+1.5h, as long as the function signatures match the contracts.

## Files you own

```text
api/agents/content.py
api/prompts/content/system.md
api/prompts/content/linkedin.md
```

Also create `api/agents/localize.py` as a **5-line stub** that returns the input asset unchanged (`variant` prefixed `loc-`). Do not implement real localization.

Do not add instagram.md, x.md, blog.md, reel, or localize.md.

## Never touch

```text
api/schemas.py
api/graph.py
api/routes/**
api/main.py
api/agents/compliance.py
api/agents/lessons.py
api/agents/research.py
api/rules/**
web/**
```

If you need a Python package (`google-genai`, etc.), ask M1 to add it to `pyproject.toml`. In an emergency, append one dep at the **end** and tell M1.

You may read `brands` from the DB **or** receive everything via `ContentRequest`. Prefer: a tiny helper in `content.py` that SELECTs from `brands` using the same `DATABASE_URL`. If you cannot import `db.py` cleanly, hardcode the three brand profiles as a dict that **matches seed.sql**. Do not invent a fourth brand.

---

## Function signatures (copy exactly)

```python
# api/agents/content.py
from schemas import ContentRequest, GeneratedAsset

def generate_content(req: ContentRequest) -> list[GeneratedAsset]:
    """Return 1+ assets covering req.platforms. LinkedIn must include variants A and B."""

# api/agents/localize.py
def localize(
    asset: GeneratedAsset,
    language: str,
    country: str,
    brand_id: str,
) -> GeneratedAsset:
    """Return a new GeneratedAsset; do not mutate the input. variant e.g. loc-ms."""
```

Never raise out of these functions. On Gemini failure: return a clearly labelled mock so the pipeline completes.

```python
GeneratedAsset(
    platform="linkedin",
    content_type="post",
    variant="A",
    title=None,
    body="[MOCK] Specialist cover for jewellery houses in Malaysia — subject to policy terms.",
    hashtags=["#Jade"],
)
```

---

## Brand voices (must be audible in the demo)

Load from DB when possible. Fallback:

| `brand_id` | Sound like | Never |
|---|---|---|
| `jade` | Senior specialist. Short confident sentences. Inventory, craft, discretion, high-value risk. | Casual slang, "guaranteed", "cheapest" |
| `doctorshield` | Calm colleague. Educational. Clinics, time, paperwork, patients. | Fear-mongering, "always covered" |
| `jaguar` | Ops + tech. Transit, chain of custody, speed, security. | Luxury-jewellery tone, "zero risk" |

`req.lessons` is a list of strings from Team Member 5. **Put them in the prompt every time** under `RELEVANT PAST LESSONS`. If a lesson says not to use "guaranteed", do not use that word.

`req.research_summary` may be empty. Ignore it if so.

---

## Output (LinkedIn only)

Return two `GeneratedAsset` objects:

- `platform="linkedin"`, `content_type="post"`, `variant="A"` and `"B"`
- ~80–150 words. `hashtags` max 3.

Always return those two, **even if `req.platforms` does not contain `linkedin`**. Returning an empty list makes a campaign complete with zero assets, which looks like a broken pipeline on stage. Ignore every other platform value; do not start Instagram/X/blog/reel.

---

## Gemini usage

- Model: env `GEMINI_MODEL` default `gemini-2.0-flash`.
- Key: `GEMINI_API_KEY` from `.env` (your personal key).
- Temperature ~0.7.
- Demand **JSON only**.

```json
{
  "assets": [
    {
      "platform": "linkedin",
      "content_type": "post",
      "variant": "A",
      "title": null,
      "body": "...",
      "hashtags": ["#Jade"]
    }
  ]
}
```

Strip markdown fences. Validate with Pydantic `GeneratedAsset`. Retry **once** if parse fails. Then mock.

If `AURA_MOCK_AGENTS=true`, skip the API (M1 may not even call you — still respect the env inside your function).

---

## Localization

Out of scope. Stub only:

```python
def localize(asset, language, country, brand_id):
    return asset.model_copy(update={"variant": f"loc-{language}"})
```

---

## Must vs skip

### Must

| Task | Acceptance |
|---|---|
| Stub `generate_content` | Returns 2 LinkedIn assets, valid Pydantic |
| Real LinkedIn for all 3 brands | Jade vs DoctorShield is obviously different |
| Lessons in prompt | `lessons=["Never say guaranteed"]` → output avoids "guaranteed" |
| JSON retry | Broken model output does not raise |

```bash
cd api
uv run python -c "
from agents.content import generate_content
from schemas import ContentRequest
r = generate_content(ContentRequest(
  brand_id='jade', topic='Jewellery theft prevention', country='Malaysia',
  goal='Awareness', platforms=['linkedin'], language='en',
  lessons=['Never describe coverage as guaranteed.']))
print(r)
"
```

### Do not build

Instagram, carousel, X, blog, reel, FFmpeg, real `localize()`.

---

## Cursor agent prompts (paste as-is)

### Prompt A — stub + LinkedIn

```text
You are Team Member 4 for AURA. Read AGENTS.md and docs/03-CONTRACTS.md §4–5.

Create api/agents/content.py with:

def generate_content(req: ContentRequest) -> list[GeneratedAsset]:

If env AURA_MOCK_AGENTS is true, or GEMINI_API_KEY is missing, return hardcoded LinkedIn A and B posts for req.brand_id that still respect req.lessons (if a lesson contains "guaranteed", do not use that word).

Otherwise call Gemini Flash (GEMINI_MODEL, GEMINI_API_KEY) with a system prompt from api/prompts/content/system.md plus a linkedin prompt. Require JSON {"assets":[...]} matching GeneratedAsset. Strip markdown fences. Pydantic-validate. Retry once. On failure return the mock, never raise.

Brand voices are in docs/members/TEAM-MEMBER-4.md. Load brands from Postgres if api/db.py is importable; else use the fallback dict in that doc.

Do not create FastAPI routes. Do not edit schemas.py, graph.py, compliance.py, or anything under web/.
```

### Prompt B — prompts on disk

```text
Write api/prompts/content/system.md and linkedin.md only.

system.md must include:
- You are a marketing writer for JA Assure brands
- Brand block will be injected
- RELEVANT PAST LESSONS must be obeyed
- No unsupported insurance claims: never guaranteed, 100% covered, always covered, zero risk, cheapest
- Return JSON only

Each file specifies length and the GeneratedAsset fields for LinkedIn only.

Do not put API keys in prompts. Do not edit files outside api/prompts/content and api/agents/content.py / localize.py.
```

### Prompt C — multi-platform

```text
Do not run this prompt. LinkedIn only for the 6–8 hour sprint.
```

### Prompt D — localize

```text
Create api/agents/localize.py as a stub that returns asset.model_copy(update={"variant": f"loc-{language}"}) and does not call Gemini. Do not add routes.
```

---

## Combining

M1 will `from agents.content import generate_content`. Same path as the stub. When your file exists on `main`, the pipeline starts writing real copy with **zero** frontend changes.

Do not rename the function. Do not make it `async` unless M1 agrees (if you need async, provide a sync wrapper `def generate_content` that `asyncio.run`s internally — ugly but keeps the contract).

## Done for demo

Same topic, two brands, visibly different LinkedIn posts. Lessons in the prompt so "guaranteed" disappears when told not to use it.
