# Demo script

Target: **5–6 minutes**. One laptop. Rehearse **twice** after freeze (you do not have time for three).

The **seeded FAIL Instagram post** is the demo. Live generate is extra. Never wait more than 15 seconds on a spinner.

## Roles

| Who | Job |
|---|---|
| Speaker A (M1) | Narrative. Clicks Review and Studio. |
| Speaker B (M2 or M5) | Compliance panel + lessons. Questions. |
| Everyone else | Silent. Do not open Cursor on the demo machine. |

## Seed (M1, at T+1.5 — not at the end)

`db/demo.sql` must exist before M2 starts. It plants:

1. Jade Instagram, status **`compliance_failed`** (not `pending_review` — pick one and stay with it), body contains **"Guaranteed protection for your jewellery business"**, check `FAIL` / `HIGH` / `CLAIM_001`.
2. One `lessons` row for Jade: `TOO_SALESY`, note `Never describe coverage as guaranteed. Prefer "coverage subject to policy terms".`
3. One **approved** DoctorShield LinkedIn post, educational tone.
4. A couple of `reviews` so metrics are not all zero.

## Click path (sticky note)

```text
Brands → Jade vs DoctorShield
Review → FAIL Instagram → Reject + Unsupported claim
Insights → lesson row + four numbers
Studio → Jade / jewellery theft / LinkedIn → Generate
  (if spinner >15s, skip and say the queue item was produced by the same pipeline)
```

## Minute-by-minute

### 0:00

> "This is not a chatbot. It is a marketing desk: write, compliance, human review, and it remembers corrections."

Sidebar: Studio, Review Queue, Brands, Insights.

### 0:30 — Brands

Jade: authoritative, premium, specialist. DoctorShield: reassuring, educational.

> "Brand voice lives in the database, not one giant prompt."

### 1:00 — Review (star screen)

Open the seeded Instagram item.

Left: copy with "Guaranteed protection".  
Right: CLAIM_001, HIGH, suggested revision.

> "Hard rules catch this before a human hunts for it. The human still decides."

Reject. Tag: **Unsupported claim**. Short note — and rehearse it once with the note left **empty**, because that is the path most likely to 500.

### 2:30 — Insights

Lesson row is there. Four numbers (even from seed).

> "The system is learning from reviewer feedback."

### 3:20 — Studio (optional live)

Jade, jewellery theft prevention, Malaysia, Awareness, **LinkedIn only**. Generate.

If it completes: open the new LinkedIn item, approve it.  
If not: "Same pipeline; the review item is the recorded run." Move on.

### 4:30 — What we did not fake

> "Approved posts sit in Postgres. Publishing is a later worker on `status=approved`. We did not burn the clock on Instagram OAuth."

Stop talking. Take questions. Prefer showing `banned_terms.yaml` or the two brand cards again.

## Fallback

| Failure | Do this |
|---|---|
| API down | Restart uvicorn. Then screenshots M1 took at freeze. |
| Gemini 429 | `AURA_MOCK_AGENTS=true`. Same UI. |
| Empty queue | Re-run `seed.sql` + `demo.sql`. Hard refresh. |
| Live generate hangs | Seeded FAIL post. 15 second rule. |

## Do not say

- "We also have eight agents / video / leads / Malay, we just ran out of time."
- "Compliance is an LLM yes/no."

Say: **pipeline, human in the loop, lessons, brand profiles in the DB.**
