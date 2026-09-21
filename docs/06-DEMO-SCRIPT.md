# Demo script

Target: **7–8 minutes** talking, **one laptop**, two browser tabs (dashboard + optional Swagger). Rehearse this three times after code freeze.

## Roles during the talk

| Who | Job |
|---|---|
| Speaker A (usually M1) | Narrative + clicks Studio and Review |
| Speaker B (usually M2 or M5) | Points at compliance panel and lessons; handles questions |
| Everyone else | Silent. Fix Wi-Fi. Do not open Cursor on the demo machine. |

If Gemini hangs, Speaker B says "this is the queued item we generated this morning" and opens the seeded FAIL asset. Never stare at a spinner for more than 15 seconds.

## Seeded backup (M1, T+42)

`db/demo.sql` must plant:

1. Jade Instagram asset, status `pending_review`, body contains **"Guaranteed protection for your jewellery business"**, compliance `FAIL` / risk `HIGH` / rule `CLAIM_001`.
2. One `lessons` row for Jade: tag `TOO_SALESY`, note `Never describe coverage as guaranteed. Prefer "coverage subject to policy terms".`
3. DoctorShield LinkedIn asset already `approved`, educational tone, so brand switch is visible even without a live generate.
4. Metrics that are not all zero (rejection_rate, first_pass_approval, etc. can be computed from seed reviews).

Live generate is the *wow*. Seed is the *guarantee*.

## Minute-by-minute

### 0:00 — One sentence

> "This is not a chatbot. It is a marketing department: research, write, compliance, human review, and it learns from corrections."

Show the sidebar. Names: Campaign Studio, Review Queue (badge), Insights, Brands.

### 0:40 — Brand intelligence

Open **Brands**. Three cards: Jade, DoctorShield, Jaguar Transit. Read Jade's tone out loud (authoritative, premium, specialist).

> "Same pipeline, three voices. Jade is not DoctorShield."

### 1:20 — Campaign Studio (live path)

Form:

- Brand: **Jade**
- Topic: **Jewellery theft prevention**
- Country: **Malaysia**
- Goal: **Awareness**
- Platforms: **LinkedIn** and **Instagram**
- Language: **English**

Click **Generate campaign**. Show the progress states: `running` → assets appearing.

If >15s with no assets: switch to Review Queue and open the seeded FAIL post. Say you will come back to live output.

### 2:30 — Review Queue (the star screen)

Open the Instagram item.

Left: generated post.  
Right: compliance.

Call out the flagged span: **"Guaranteed protection"** → unsupported absolute claim.

> "The model is not the safety officer. Hard rules plus a structured reviewer catch this before a human would have to hunt for it. The human still decides."

Buttons: Reject / Edit / Approve.

### 3:40 — Feedback loop

Click **Reject**. Tag: **Unsupported claim**. Note: `Never say guaranteed. Use subject to policy terms.`

Then **Regenerate** (or generate a sibling variant). Open the new draft.

> "Relevant past lessons were injected into the writer. You should see the wording change."

If the new draft is still bad, do not apologise — open the lesson in **Insights → Lessons learned** and show the stored original vs note. The loop existing is the point.

Approve a clean LinkedIn variant so the queue badge drops.

### 5:00 — Brand switch

Studio again: Brand **DoctorShield**, topic **Professional indemnity for clinics**, LinkedIn.

Open the result (or the seeded approved DoctorShield post).

> "Educational, reassuring — not premium jewellery tone. Brand config lives in the database, not one giant prompt."

### 5:50 — Insights

Show the four numbers (even if from seed):

- Rejection rate
- Average human edits
- First-pass approval
- Compliance failure rate

One line:

> "The system is learning from reviewer feedback."

Optional: Competitors page with a snapshot diff ("page hash changed, here's the summary"). Skip if it is empty.

### 6:40 — What we would ship next (do not demo)

Approved queue is already in Postgres (`status=approved`). Publisher is Project 2 on purpose. We did not burn the hackathon on Instagram OAuth.

### 7:10 — Stop talking

Ask for questions. Prefer: "Show me Malay" (localization), "Show me the YAML banned terms", "Show the graph".

## Click path (cheat sheet on a sticky note)

```text
Brands → Jade card
Studio → fill form → Generate
Review → Instagram FAIL → Reject + tag
Review → Regenerate or new item → Approve LinkedIn
Studio → DoctorShield → Generate or open library
Insights → metrics + lessons
```

## Fallback matrix

| Failure | What you do |
|---|---|
| API down | Restart `uvicorn` from a prepared terminal. If still down, screenshots in the slides (M1 takes them at T+44). |
| Gemini 429 | `AURA_MOCK_AGENTS=true` restart. Say "offline mode uses the same pipeline with recorded outputs". |
| Empty queue | Run `seed.sql` + `demo.sql`. Refresh. |
| CORS | M1 already set `localhost:3000`. Hard refresh. |
| Wrong brand voice | Do not improvise. Open seeded DoctorShield vs Jade side by side in Library. |
| Laptop sleep killed servers | Two terminals documented in setup. Re-run. 30 seconds. |

## What not to say

- "It's just GPT wrapping."
- "Compliance is an LLM yes/no."
- "We also have eight agents talking to each other."
- "The publisher almost works."

Say: **pipeline, human in the loop, lessons, brand profiles in the DB.**
