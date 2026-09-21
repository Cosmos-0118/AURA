# Five-minute demo

Use one laptop. Reset with `db/demo.sql`, open the four target pages in tabs, and
capture fallback screenshots before presenting.

## Click path

```text
Overview -> Brands -> Review failed asset -> reject -> Insights -> Studio
```

## Script

### 0:00 — Overview

> AURA is not a chatbot. It is a marketing operations loop: create, check,
> review, and learn from the human decision.

Point to pending work and the Create Campaign action. Do not narrate the stack.

### 0:40 — Brands

Compare Jade and DoctorShield.

> Brand voice is structured data. Jade speaks like a specialist for high-value
> businesses; DoctorShield speaks like a calm colleague for doctors and clinics.

### 1:20 — Review

Open the seeded Jade Instagram asset. Point to `Guaranteed protection`, `FAIL`,
`HIGH`, `CLAIM_001`, and the suggested revision.

> Deterministic rules catch an unsupported absolute claim. The system explains
> the problem, but the human still makes the decision.

Reject it with `UNSUPPORTED_CLAIM`. Leave the optional note empty during at least
one rehearsal because this proves the safe fallback.

### 2:40 — Insights

Show the new lesson and the exact metric cards.

> That review is now reusable guidance for the next campaign. This is the
> feedback loop, not just another content generator.

### 3:30 — Studio

Create a Jade, Malaysia, LinkedIn awareness campaign about jewellery theft
prevention. If it completes, show the two variants and open one in Review.

If generation takes more than 15 seconds:

> The live provider is slow, so I will use the recorded deterministic path. The
> same pipeline produced the review item you just saw.

Do not wait on a spinner.

### 4:40 — Close

> AURA keeps compliance evidence, human decisions, approved content, and lessons
> in one controlled workflow. Publishing can consume approved rows later; it
> cannot bypass review.

Stop and take questions.

## Fallbacks

| Failure | Response |
|---|---|
| Gemini timeout/429 | Set `AURA_MOCK_AGENTS=true`; use deterministic generation |
| Empty queue | Reapply `db/demo.sql` and refresh |
| API unavailable | Restart FastAPI once, then use screenshots |
| Studio still running after 15 seconds | Return to the seeded review/lesson path |
| A stretch page fails | Do not open it; the core demo does not depend on it |

Do not claim that competitor crawling, leads, localization, publishing, or video
are implemented. Do not call compliance an LLM yes/no check; lead with the hard
rule and human decision.
