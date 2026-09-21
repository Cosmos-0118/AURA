# Team Member 4 — Content Engine

You are the writer. You turn a `ContentRequest` into platform-ready copy that sounds like **Jade**, **DoctorShield**, or **Jaguar Transit** — not like generic ChatGPT insurance.

You also localize (adapt, not translate). You do **not** run compliance. You do **not** create HTTP routes. M1 calls your functions from `graph.py`.

## Read these first

1. [../00-START-HERE.md](../00-START-HERE.md)
2. [../02-SETUP.md](../02-SETUP.md)
3. [../03-CONTRACTS.md](../03-CONTRACTS.md) — `ContentRequest`, `GeneratedAsset`, function signatures §5
4. [../04-WORKFLOW-RULES.md](../04-WORKFLOW-RULES.md)
5. [../../AGENTS.md](../../AGENTS.md)

## Your branch

`feat/m4-content`

You can start **stubs** after you clone, even before T+3, as long as the function signatures match the contracts. Real Gemini waits until `api/schemas.py` exists on `main` so you import it.

## Files you own

```text
api/agents/content.py
api/agents/localize.py
api/prompts/content/
```

Suggested prompt files (you may add more **in this folder only**):

```text
api/prompts/content/system.md
api/prompts/content/linkedin.md
api/prompts/content/instagram.md
api/prompts/content/x.md
api/prompts/content/blog.md
api/prompts/content/reel_script.md
api/prompts/content/localize.md
```

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

`req.lessons` is a list of strings from Team Member 5. **Put them in the prompt every time** under a heading `RELEVANT PAST LESSONS`. If you ignore them, the demo's "regenerate after reject" will not work.

`req.research_summary` is optional competitor context. One short paragraph in the prompt. Do not quote it as fact if it is empty.

---

## Per-platform output (Phase 2; Phase 1 is LinkedIn only)

Return `GeneratedAsset` objects. JSON from Gemini should parse into this list.

### LinkedIn (Phase 1)

- Two items, `platform="linkedin"`, `content_type="post"`, `variant="A"` and `"B"`.
- ~80–150 words. No hashtag walls. `hashtags` max 3.

### Instagram

- Caption: `content_type="caption"`, `variant="A"`, body = caption text, hashtags 5–8 in the field not dumped only in body.
- Carousel: `content_type="carousel"`, `body` is a JSON string array of 4–6 short slide texts (see contracts).

### X

- `content_type="thread"`, `body` = tweets separated by `\n---\n` (2–5 parts).
- Optional second variant `B` as a single `post`.

### Blog

- `content_type="article"`, `title` set, `body` ~500–800 words markdown-ish plain text. No 4000-word essays.

### Reel (Phase 3)

- `content_type="script"`, `platform="reel"`.
- Body format:

```text
HOOK: ...
BEATS:
1. ...
2. ...
CTA: ...
DURATION: 25s
```

Do not generate MP4 here. If you still have time, a separate script `api/agents/content.py` helper is **not** allowed to call FFmpeg unless M1 agrees — keep video in a function `_maybe_render_reel` that is unused by default.

---

## Gemini usage

- Model: env `GEMINI_MODEL` default `gemini-2.0-flash`.
- Key: `GEMINI_API_KEY` from `.env` (your personal key).
- Temperature ~0.7 for copy, ~0.3 for localization.
- Demand **JSON only**:

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

`localize.md` prompt must include: brand voice, country, audience, **keep meaning**, adapt CTA and examples (Malaysia jewellery SMEs ≠ US consumers), do not introduce new insurance promises.

Return the same `platform` and `content_type`, new `language` is not on `GeneratedAsset` — M1 sets language on the DB row. You set `variant` to `loc-{language}`.

---

## Phases

### Phase 1

| Task | Acceptance |
|---|---|
| Stub `generate_content` | Returns 2 LinkedIn assets, valid Pydantic |
| Real LinkedIn for all 3 brands | Running the function with Jade vs DoctorShield produces obviously different tone |
| Lessons in prompt | If `lessons=["Never say guaranteed"]` the mock-or-real output avoids "guaranteed" |
| JSON retry | Broken model output does not raise |

How to test without the full app:

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

### Phase 2

Instagram caption + carousel, X thread, blog, `localize()` to `ms` for Malaysia.

### Phase 3

Reel script. Optional TTS later — not required.

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
Write api/prompts/content/system.md and linkedin.md, instagram.md, x.md, blog.md, localize.md.

system.md must include:
- You are a marketing writer for JA Assure brands
- Brand block will be injected
- RELEVANT PAST LESSONS must be obeyed
- No unsupported insurance claims: never guaranteed, 100% covered, always covered, zero risk, cheapest
- Return JSON only

Each platform file specifies length and the GeneratedAsset fields.

Do not put API keys in prompts. Do not edit files outside api/prompts/content and api/agents/content.py / localize.py.
```

### Prompt C — multi-platform

```text
Update generate_content so for each platform in req.platforms it produces the assets defined in docs/members/TEAM-MEMBER-4.md (LinkedIn A+B, Instagram caption+carousel, X thread, blog article).

Carousel body MUST be a JSON string of an array of strings, not a Python list in the field.

Keep one Gemini call per campaign (all platforms in one JSON) to save rate limits, unless the payload is too big — then one call per platform.

Still never raise. Still mock fallback.
```

### Prompt D — localize

```text
Create api/agents/localize.py:

def localize(asset, language, country, brand_id) -> GeneratedAsset

Adapt, do not literally translate. Use api/prompts/content/localize.md. New variant loc-{language}. Same platform and content_type. On failure return the original body prefixed with [MOCK-LOCALE {language}] rather than raising.

Do not add routes. Do not write to the database.
```

---

## Combining

M1 will `from agents.content import generate_content`. Same path as the stub. When your file exists on `main`, the pipeline starts writing real copy with **zero** frontend changes.

Do not rename the function. Do not make it `async` unless M1 agrees (if you need async, provide a sync wrapper `def generate_content` that `asyncio.run`s internally — ugly but keeps the contract).

## Done for demo

Same topic, two brands, visibly different posts. After a TOO_SALESY lesson, regenerate is less salesy. Malay localization of one Instagram caption if Phase 2 landed.
