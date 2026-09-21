# Team Member 4 — Content Engine Roadmap

> **Branch:** `feat/m4-content`
> **Owned paths:** `api/agents/content.py`, `api/agents/localize.py`, `api/prompts/content/**`, `api/tests/content/**`
> **Do NOT touch:** schemas, routes, graph, dependencies, `.env`, or any M5/M1/M2/M3 files.

---

## Phase 0 — Setup & Branch (T+0:00 → T+0:30)

Goal: Local dev is running; your branch is ready.

- [ ] Checkout the branch:
  ```bash
  git checkout feat/m4-content
  git pull origin main
  ```
- [ ] Install existing dependencies only (no new packages):
  ```bash
  cd api && uv sync
  ```
- [ ] Verify the API starts:
  ```bash
  cd api && uv run uvicorn main:app --reload
  ```
  Confirm `GET /api/health` returns `{ "ok": true }`.
- [ ] Read and internalise these files (don't edit them):
  - `AGENTS.md`
  - `docs/TEAM-PLAN.md`
  - `docs/03-CONTRACTS.md` — sections 1, 4, 5, 9
  - `api/schemas.py` — `ContentRequest`, `GeneratedAsset`
  - `api/agents/_stubs.py` — the mock you're replacing
  - `api/graph.py` — how M1 calls your function

---

## Phase 1 — Scaffold Files & Brand Voice Data (T+0:30 → T+1:00)

Goal: All owned files exist and import correctly. Zero logic yet.

### 1a. Create directory structure

```text
api/
├── agents/
│   ├── content.py          ← main module
│   └── localize.py         ← no-op stub (out of sprint)
├── prompts/
│   └── content/
│       ├── __init__.py
│       └── linkedin.py     ← prompt templates
└── tests/
    └── content/
        ├── __init__.py
        └── test_generate.py
```

### 1b. Create `api/agents/content.py` skeleton

```python
"""Content engine — Team Member 4."""

from schemas import ContentRequest, GeneratedAsset

def generate_content(req: ContentRequest) -> list[GeneratedAsset]:
    """Return deterministic drafts. Real logic added in Phase 2."""
    return []  # placeholder
```

### 1c. Create `api/agents/localize.py` no-op

```python
"""Localization stub — reserved, out of this sprint."""

from schemas import GeneratedAsset

def localize(
    asset: GeneratedAsset,
    language: str,
    country: str,
    brand_id: str,
) -> GeneratedAsset:
    return asset.model_copy()
```

### 1d. Define brand voice constants

Inside `api/prompts/content/linkedin.py` create a `BRAND_VOICES` dict:

| Brand | Tone keywords | Vocabulary themes | Don't say |
|---|---|---|---|
| `jade` | Precise, premium, B2B specialist | jewellery, craft, inventory, discretion | guaranteed, 100% covered, cheapest |
| `doctorshield` | Calm, educational, colleague | clinics, patients, time, paperwork | guaranteed, always covered, claim guaranteed |
| `jaguar` | Operational, technology-led | transit, custody, speed, security | zero risk, guaranteed |

### 1e. Compile check

```bash
cd api && uv run python -m compileall agents/content.py agents/localize.py prompts/content/linkedin.py
```

> **Important:** Must pass before moving on. This confirms `graph.py` can import your functions.

---

## Phase 2 — Deterministic A/B LinkedIn Generation (T+1:00 → T+2:30)

Goal: `generate_content()` returns **two** distinct LinkedIn variants (A and B) per brand, with recognisably different voices, using zero network calls. This is the **must-ship** slice.

### 2a. Build deterministic templates per brand

In `api/prompts/content/linkedin.py`, write template-rendering functions:

```python
def render_jade(topic, country, goal, lessons, variant) -> dict: ...
def render_doctorshield(topic, country, goal, lessons, variant) -> dict: ...
def render_jaguar(topic, country, goal, lessons, variant) -> dict: ...
```

Each returns `{ "title": ..., "body": ..., "hashtags": [...] }`.

**Key rules:**
- Variant `"A"` = direct, headline-driven. Variant `"B"` = storytelling, question-led.
- Use the brand's vocabulary themes and tone (from the voice table above).
- Incorporate `lessons` strings to **guide** the copy — don't paste them verbatim.
- Keep hashtags as a plain list (no `#` prefix in the list items).
- Never include `guaranteed`, `100% covered`, `zero risk`, or invented statistics.

### 2b. Wire `generate_content()` logic

```python
def generate_content(req: ContentRequest) -> list[GeneratedAsset]:
    assets = []
    for platform in req.platforms:
        if platform == "linkedin":
            for variant in ("A", "B"):
                rendered = _render(req.brand_id, req.topic, req.country,
                                   req.goal, req.lessons, variant)
                assets.append(GeneratedAsset(
                    platform="linkedin",
                    content_type="post",
                    variant=variant,
                    title=rendered["title"],
                    body=rendered["body"],
                    hashtags=rendered["hashtags"],
                ))
        # other platforms: skip for now (Phase 5 adds Instagram)
    return assets
```

**Critical contract rules:**
- Return `list[GeneratedAsset]` — never dicts.
- Only return platforms the request asked for.
- LinkedIn always gets two variants (`A` and `B`).

### 2c. Acceptance self-check before committing

| Check | How to verify |
|---|---|
| Jade output reads premium & specialist | Read the body text |
| DoctorShield output reads calm & educational | Read the body text |
| Jaguar output reads operational & tech-led | Read the body text |
| A ≠ B for the same brand | `assert asset_a.body != asset_b.body` |
| A supplied lesson changes the copy | Call with and without lessons, diff output |
| Returns valid Pydantic objects | `GeneratedAsset.model_validate(asset.model_dump())` |
| No banned words in output | grep for `guaranteed`, `100% covered`, `zero risk` |

### 2d. Write focused tests

`api/tests/content/test_generate.py`:

```python
def test_linkedin_returns_two_variants(): ...
def test_brands_produce_different_output(): ...
def test_lessons_influence_copy(): ...
def test_only_requested_platforms(): ...
def test_no_banned_words(): ...
def test_returns_pydantic_objects(): ...
```

### 2e. Compile & run tests

```bash
cd api && uv run python -m compileall agents/content.py
cd api && uv run python -m pytest tests/content/ -v
```

### 2f. Commit & open PR

```bash
git add api/agents/content.py api/agents/localize.py api/prompts/content/ api/tests/content/
git commit -m "Add deterministic A/B LinkedIn generation for all three brand voices"
git push origin feat/m4-content
```

> **Tip:** Include sample output for each brand in the PR description so M1 can verify integration immediately.

---

## Phase 3 — Error-Safe Gemini Path (T+2:30 → T+4:00)

Goal: When `GEMINI_API_KEY` is present, use Gemini to generate richer copy. **Every failure falls back to the deterministic path** — missing key, timeout, 429, invalid JSON, empty response.

### 3a. Create the prompt template

`api/prompts/content/linkedin.py` — add a `build_gemini_prompt()` function:

- System prompt: brand voice description, tone, don'ts, and any lessons.
- User prompt: topic, country, goal, variant label.
- Ask for **structured JSON** output matching `GeneratedAsset` fields.

### 3b. Add Gemini call wrapper

In `api/agents/content.py`:

```python
import os, json, httpx

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

def _call_gemini(prompt: str) -> dict | None:
    """Call Gemini API. Return parsed dict or None on ANY failure."""
    if not GEMINI_API_KEY or GEMINI_API_KEY == "your_personal_gemini_key":
        return None
    try:
        # Use httpx (already in dependencies) to call the Gemini REST API
        resp = httpx.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent",
            params={"key": GEMINI_API_KEY},
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=15.0,
        )
        resp.raise_for_status()
        text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
        return json.loads(text)
    except Exception:
        return None  # fall back to deterministic
```

### 3c. Update `generate_content()` to try Gemini first

```python
for variant in ("A", "B"):
    gemini_result = _call_gemini(build_gemini_prompt(req, variant))
    if gemini_result and _validate_gemini_output(gemini_result, "linkedin"):
        asset = GeneratedAsset(**gemini_result)
    else:
        # deterministic fallback (Phase 2 code)
        asset = _deterministic_variant(req, variant)
    assets.append(asset)
```

### 3d. Validate model output

```python
def _validate_gemini_output(data: dict, expected_platform: str) -> bool:
    """Treat model output as untrusted."""
    required = {"platform", "content_type", "body"}
    if not required.issubset(data.keys()):
        return False
    if data.get("platform") != expected_platform:
        return False
    if not data.get("body") or len(data["body"]) < 20:
        return False
    # Check for banned words
    lower = data["body"].lower()
    if any(w in lower for w in ("guaranteed", "100% covered", "zero risk")):
        return False
    return True
```

> **Important:** If ONE variant's Gemini output is invalid, replace just that variant with the deterministic fallback. Don't fail the whole campaign.

### 3e. Add error-path tests

```python
def test_missing_api_key_returns_deterministic(): ...
def test_invalid_json_falls_back(): ...
def test_wrong_platform_in_response_falls_back(): ...
def test_banned_words_in_gemini_output_falls_back(): ...
def test_network_timeout_falls_back(): ...  # mock httpx
```

### 3f. Compile & test

```bash
cd api && uv run python -m compileall agents/content.py
cd api && uv run python -m pytest tests/content/ -v
```

### 3g. Commit

```bash
git commit -m "Add validated Gemini generation with deterministic fallback on all errors"
git push origin feat/m4-content
```

---

## Phase 4 — Lesson-Aware Generation & Polish (T+4:00 → T+4:30)

Goal: Lessons actively shape the generated content. Ready for the **T+4:30 vertical-slice checkpoint**.

### 4a. Ensure lessons modify deterministic output

When `req.lessons` is non-empty:
- Append a "guided by past feedback" sentence to the body.
- If lessons mention specific corrections (e.g., "avoid mentioning pricing"), reflect that in the template selection.

### 4b. Ensure lessons feed into Gemini prompt

The `build_gemini_prompt()` must inject lesson strings into the system prompt:
```
Previous reviewer feedback to incorporate:
- "Avoid mentioning specific pricing tiers"
- "Use more inclusive language"
```

### 4c. Run the full T+4:30 acceptance flow mentally

1. Deterministic mode (`AURA_MOCK_AGENTS=true`): `graph.py` imports from `_stubs.py` — your code isn't called.
2. Real mode (`AURA_MOCK_AGENTS=false`): `graph.py` imports `content.generate_content` — your code IS called.
3. Without a valid Gemini key → deterministic variants returned.
4. With a valid Gemini key → Gemini output validated, fallback on error.

### 4d. Final commit before checkpoint

```bash
git commit -m "Ensure lessons influence both deterministic and Gemini content paths"
git push origin feat/m4-content
```

> **Caution:** **T+4:30 is the vertical-slice checkpoint.** Your code must be mergeable here. M1 will import `generate_content` and run a campaign end-to-end on `main`. If it fails, all work stops to fix it.

---

## Phase 5 — Stretch: Instagram Captions (T+4:30 → T+6:00)

> Only start this after the T+4:30 checkpoint passes.

Goal: Add Instagram caption support through the **same** `generate_content()` path.

### 5a. Add Instagram templates

In `api/prompts/content/` (create `instagram.py` or extend `linkedin.py`):
- Two short caption variants (A and B) per brand.
- `content_type = "caption"`, `platform = "instagram"`.
- Shorter format: 1-3 sentences + hashtags.

### 5b. Update `generate_content()` platform dispatch

```python
if platform == "linkedin":
    # existing A/B logic
elif platform == "instagram":
    for variant in ("A", "B"):
        # Instagram-specific rendering
        assets.append(GeneratedAsset(
            platform="instagram",
            content_type="caption",
            variant=variant,
            ...
        ))
```

### 5c. Add Instagram tests

```python
def test_instagram_returns_two_caption_variants(): ...
def test_instagram_captions_are_short(): ...
def test_instagram_brand_voices_differ(): ...
```

### 5d. Commit

```bash
git commit -m "Add Instagram caption A/B variants through the same generation path"
git push origin feat/m4-content
```

---

## Phase 6 — Final Polish & Freeze (T+6:00 → T+6:30)

Goal: Code is clean, tested, and ready for final merge.

- [ ] Run full test suite: `cd api && uv run python -m pytest tests/content/ -v`
- [ ] Run compile check: `cd api && uv run python -m compileall agents/content.py agents/localize.py`
- [ ] Review all output for the 3 brands — confirm voices are **recognisably different**
- [ ] Ensure no banned words leak through any path
- [ ] Clean up any debug prints or TODO comments
- [ ] Final commit and push
- [ ] PR description includes:
  - Sample output per brand (LinkedIn A + B)
  - Tests run + results
  - Known limitations (e.g., Instagram is stretch, localize is no-op)

> **Warning:** **T+6:30 is feature freeze.** No new features after this. Only merge and demo rehearsal.

---

## Quick Reference: What NOT to Do

| ❌ Don't | ✅ Do instead |
|---|---|
| Edit `api/schemas.py` | Import `ContentRequest`, `GeneratedAsset` as-is |
| Edit `api/graph.py` or `api/routes/` | Let M1 import your functions |
| Add new dependencies to `pyproject.toml` | Use `httpx` (already installed) for Gemini calls |
| Return dicts from `generate_content` | Always return `list[GeneratedAsset]` |
| Raise exceptions that kill campaigns | Catch everything, return deterministic fallback |
| Add `#` to hashtag strings | `["Jade", "RiskManagement"]` not `["#Jade"]` |
| Use `guaranteed`, `100% covered`, `zero risk` | Use hedged language: "subject to policy terms" |
| Implement X, blog, reel, localization, research | Only LinkedIn (must) and Instagram (stretch) |
| `git rebase` or `--force` push | `git pull origin main` (merge), normal push |

---

## Dependency Summary

```text
You produce → generate_content(ContentRequest) → list[GeneratedAsset]
M1 calls    → graph.py imports your function when AURA_MOCK_AGENTS=false
M5 produces → lessons (via get_relevant_lessons) → fed to you as req.lessons
M1 stores   → your GeneratedAsset into content_assets table
M5 checks   → your asset body via check_compliance (not your concern)
```

Your only integration surface is the **function signature** and the **Pydantic return type**. Get those right, and the build stays smooth.
