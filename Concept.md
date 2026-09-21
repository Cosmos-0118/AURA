Bae, I went through the brief and checked the current open-source options. The simplest way to understand the assignment is:

> **They do not want an AI chatbot. They want an AI-powered marketing department with a dashboard.**

It should research → create content → check compliance → let a human review → learn from corrections → optionally publish.

## 1. What they actually need you to build

| Part | In simple terms | What your app should do |
|---|---|---|
| Competitor Intelligence | Watch competitors | Scan websites/public sources periodically, detect changes and produce a short report |
| Content Agent | Marketing writer | Generate LinkedIn, Instagram, X, blogs, captions, carousel copy, A/B variants |
| Brand Voice | Don't make every brand sound identical | Jade ≠ Jaguar Transit ≠ DoctorShield |
| Video Agent | Make Reels automatically | Script → voice → captions → visuals → MP4 |
| Localization | Rewrite for each country/language | English → Malay / Indonesian / Thai / Chinese, but adapted culturally rather than literally translated |
| Lead Agent | Find potential customers | Find jewellers, doctors, clinics, couriers, SMEs; enrich and score them |
| Compliance Agent | Marketing safety officer | Detect unsupported insurance claims before humans even see them |
| Human Review | Final authority | Approve / edit / reject every generated asset |
| Feedback Memory | Learn from mistakes | Remember things like "too salesy", "wrong CTA", "unsupported claim" |
| Approved Queue | Bridge between projects | Store approved posts in the DB |
| Auto Publisher | Bonus | Publish only approved items |
| Analytics | Feedback from the real world | Likes/clicks/etc. → future content strategy |

The key differentiator is **not content generation**.

It's:

**Compliance + Human Review + Feedback Learning.**

That is what I'd make extremely polished.

---

# 2. Architecture I'd use

Don't build some giant autonomous swarm where eight agents randomly talk to each other.

Use a **controlled LangGraph workflow**:

```text
                     ┌─────────────────────┐
                     │   Next.js Dashboard │
                     │     Human Team      │
                     └──────────┬──────────┘
                                │
                           FastAPI API
                                │
                     ┌──────────▼──────────┐
                     │      LangGraph      │
                     │     Orchestrator    │
                     └──────────┬──────────┘
                                │
        ┌────────────┬──────────┼───────────┬────────────┐
        ▼            ▼          ▼           ▼            ▼
     Research     Content   Localization  Video        Leads
      Agent        Agent       Agent       Agent        Agent
        │            │          │           │            │
        └────────────┴─────┬────┴───────────┘            │
                           ▼                             │
                    Compliance Agent                    │
                           │                             │
                    PASS / FAIL                         │
                           │                             │
                           ▼                             ▼
                     Human Review                   Lead CRM
                  Approve/Edit/Reject
                           │
                    ┌──────▼──────┐
                    │  PostgreSQL │
                    │  Supabase   │
                    └──────┬──────┘
                           │
                       approved
                           │
                           ▼
                  Publisher Worker
                   [BONUS PROJECT]
                           │
                  Social Platforms
                           │
                           ▼
                      Analytics
                           │
                           └──────► Content Agent
```

LangGraph is particularly appropriate because it supports persistent state, memory, long-running workflows and human-in-the-loop interruptions natively. :chatgpt-content-reference{index="0"}

---

# 3. Best GitHub UI repo for this

## 🥇 My pick: Kiranism Next Shadcn Dashboard

[Kiranism/next-shadcn-dashboard-starter on GitHub](https://github.com/Kiranism/next-shadcn-dashboard-starter)

This is the one I would actually fork.

It's currently a Next.js 16 + TypeScript + Tailwind + shadcn/ui dashboard, MIT licensed, with about 7k stars. More importantly, its tables, filtering, pagination, forms and mutations are **functional**, rather than being screenshots disguised as an admin template. :chatgpt-content-reference{index="2"}

That matches this project ridiculously well.

You can turn its pages into:

| Existing dashboard concept | JA Assure version |
|---|---|
| Dashboard | Marketing Command Center |
| Products/Table | Content Queue |
| Tasks | Human Reviews |
| Analytics | Content Performance |
| Users | Leads |
| Forms | Create Campaign |
| Settings | Brand Profiles + Compliance Rules |

### Another excellent UI

[satnaing/shadcn-admin](https://github.com/satnaing/shadcn-admin?utm_source=chatgpt.com)

This one is even more popular, around 14.3k stars, MIT licensed, very polished and includes responsive layouts, advanced tables, search, accessibility and RTL support. :chatgpt-content-reference{index="4"}

But it's Vite + TanStack Router rather than Next.js. For **this particular hackathon**, I'd take Kiranism because connecting a Next.js dashboard to the rest of your stack will be cleaner.

So:

**Best-looking generic UI:** satnaing/shadcn-admin  
**Best UI to actually build this project on:** **Kiranism/next-shadcn-dashboard-starter**

---

# 4. Best backend repo I found

## 🥇 Agent Service Toolkit

[JoshuaC215/agent-service-toolkit](https://github.com/JoshuaC215/agent-service-toolkit)

This is almost suspiciously close to what your problem statement asks for.

It already has:

| Requirement | Already present |
|---|---:|
| Python | ✅ |
| FastAPI | ✅ |
| LangGraph | ✅ |
| Multiple agents | ✅ |
| Human-in-the-loop | ✅ |
| Long-term memory | ✅ |
| PostgreSQL | ✅ |
| Async processing | ✅ |
| Streaming API | ✅ |
| Docker | ✅ |
| Tests | ✅ |
| Feedback mechanism | ✅ |
| MIT licence | ✅ |

It has around 4.5k stars and specifically includes LangGraph `interrupt()`, long-term memory, multiple agents, FastAPI endpoints and a Postgres-based Docker setup. :chatgpt-content-reference{index="6"}

### What I'd do

Fork it.

Remove its Streamlit UI.

Keep:

```text
FastAPI
LangGraph
Postgres integration
agent structure
configuration
Docker
tests
```

Then connect your **Next.js shadcn dashboard** to the FastAPI service.

That's a very strong starting point.

---

# 5. Research / scraping

## Use Crawl4AI

[unclecode/crawl4ai](https://github.com/unclecode/crawl4ai)

This is what I'd choose instead of trying to write your own scraper.

It can handle dynamic JavaScript pages, browser sessions, structured extraction, screenshots, caching, links, clean Markdown output and Docker deployment. The project describes a 50k+ star community and is Apache-2.0 licensed. :chatgpt-content-reference{index="8"}

Your Research Agent basically does:

```text
competitors
      ↓
Crawl4AI
      ↓
clean text
      ↓
compare against last snapshot
      ↓
what changed?
      ↓
Gemini
      ↓
Competitor Intelligence Report
```

### Important trick

Don't ask the LLM:

> "What's new with competitor X?"

Actually store snapshots.

For example:

```text
competitor_id
url
content_hash
content
scraped_at
```

Tomorrow:

```python
if current_hash != previous_hash:
    analyse_change()
```

Now your system is genuinely **monitoring competitors** rather than pretending to.

---

# 6. Your best database

I'd use **Supabase PostgreSQL**.

It gives you:

**Postgres + authentication + file storage + APIs** in one service.

The current free plan includes a 500 MB Postgres database, 1 GB file storage and up to two free active projects, which is easily enough for a hackathon prototype. :chatgpt-content-reference{index="9"}

Use it for:

```text
content
reviews
feedback
brands
competitors
research results
leads
compliance results
publish queue
analytics
```

And use Supabase Storage for:

```text
images
video
voiceover
generated reels
```

You definitely do **not** need Redis + Kafka + MongoDB + five databases for this.

---

# 7. The database tables I'd make

Keep this clean:

```text
brands
competitors
research_snapshots
content_assets
compliance_checks
reviews
lessons
leads
publish_jobs
analytics
```

The most important one is:

```text
content_assets

id
brand_id
platform
content_type
language
title
content
media_url

status
-------
draft
compliance_failed
pending_review
approved
rejected
scheduled
published

created_at
approved_at
approved_by
```

That `status` field is essentially the heart of the entire project.

---

# 8. Feedback memory — this can win you marks

Suppose the AI generates:

> Get guaranteed protection for your clinic today!

Reviewer rejects it:

```text
reason_tag: UNSUPPORTED_CLAIM

note:
Never describe coverage as guaranteed.
Use language such as "coverage subject to policy terms".
```

Save that.

Next time DoctorShield content is generated:

```text
BRAND:
DoctorShield

PLATFORM:
LinkedIn

RELEVANT PAST LESSONS:

1. Avoid "guaranteed protection".
2. Don't imply every medical claim is covered.
3. Reviewer prefers educational rather than aggressive sales CTAs.
```

Then generate the post.

That satisfies the brief's closed feedback loop perfectly.

### Even better

Save the **edit diff**.

AI:

```text
Guaranteed complete protection for your medical practice.
```

Human changes to:

```text
Professional indemnity solutions designed for medical practitioners.
```

Store both versions.

That is incredibly valuable few-shot data.

You don't need fine-tuning for the hackathon.

---

# 9. How I'd make the compliance system

Do **not** make this:

```text
LLM:
"Does this seem compliant?"

YES
```

That's weak.

Make three checks.

```text
CONTENT
   ↓
Hard-rule scanner
   ↓
Claim evidence checker
   ↓
LLM compliance reviewer
   ↓
PASS / REVIEW / FAIL
```

Hard rules could catch things like:

```text
guaranteed
100% covered
always covered
zero risk
best insurance
cheapest insurance
claim guaranteed
```

Then require factual insurance claims to have an approved source.

Finally, Gemini examines the complete text against your written rubric and returns structured JSON:

```json
{
  "result": "FAIL",
  "risk": "HIGH",
  "rules": [
    "CLAIM_004"
  ],
  "issues": [
    {
      "text": "Guaranteed coverage",
      "reason": "Unsupported absolute insurance claim"
    }
  ],
  "suggested_revision": "..."
}
```

For a real deployment, JA's compliance/legal team would need to provide the jurisdiction-specific rules. Don't invent Singapore/Malaysia/Hong Kong insurance regulations yourselves.

---

# 10. Brand personalities

This isn't hypothetical either. JA's current public material already gives you enough to create initial brand profiles.

**Jade** focuses on jewellers, gold, watches, cash and other complex/high-value risks and emphasizes specialist insurance and underwriting technology. :chatgpt-content-reference{index="10"}

**Jaguar Transit** focuses on transporting cash, jewellery, gold and valuable goods, combining transit insurance with security technology. :chatgpt-content-reference{index="11"}

**DoctorShield** is positioned around professional indemnity for doctors/clinics with a strongly digital, quick, low-paperwork experience. :chatgpt-content-reference{index="12"}

So your brand configuration might be:

```text
JADE
tone:
  authoritative
  premium
  specialist
  B2B

DOCTORSHIELD
tone:
  reassuring
  professional
  educational
  human

JAGUAR
tone:
  fast
  technological
  security-focused
  operational
```

Store these in the database rather than hardcoding them into one giant prompt.

---

# 11. Content generation

The user selects:

```text
Brand: Jade
Topic: Jewellery theft prevention
Country: Malaysia
Campaign goal: Awareness
```

The AI generates:

```text
LinkedIn
   ├─ Variant A
   └─ Variant B

Instagram
   ├─ Caption
   ├─ Carousel slides
   └─ hashtags

X
   ├─ Tweet A
   ├─ Tweet B
   └─ thread

Blog
   └─ 700-word article

Reel
   ├─ script
   ├─ narration
   └─ video
```

That's exactly what the judges mean by a **multi-format content engine**.

---

# 12. Video / Reel generation

Don't waste hackathon time trying to generate cinematic AI video.

You can satisfy this requirement far more reliably with:

```text
Gemini
   ↓
20–30 sec script
   ↓
TTS
   ↓
voice.wav

Gemini / image provider
   ↓
3–5 visuals

Script
   ↓
subtitle timings

FFmpeg
   ↓
1080x1920 reel.mp4
```

Add:

```text
transitions
animated text
logo
background music
captions
CTA
```

Now you genuinely generated a Reel entirely in code.

Use **FFmpeg** as the final renderer. It's much more predictable than depending completely on an expensive video-generation model.

---

# 13. Lead Agent

Example:

```text
Find potential Jade customers
       ↓
Search:
"jewellery stores Singapore"
"luxury watch dealers Malaysia"
"gold dealers Kuala Lumpur"
       ↓
business websites
       ↓
Crawl4AI
       ↓
company information
       ↓
optional email enrichment
       ↓
AI scoring
```

Output:

| Lead | Fit | Why |
|---|---:|---|
| ABC Jewellery | 92 | Jewellery + high-value inventory |
| Luxury Watch Co | 87 | Premium watches |
| Small Fashion Shop | 20 | Weak fit |

Then:

```text
AI drafts outreach
       ↓
Human reviews
       ↓
Send manually / later integrate email
```

Don't scrape LinkedIn aggressively. Use public business sites, permitted search APIs and official APIs where available.

---

# 14. Multilingual

You want:

```text
translate(text, "Malay")
```

❌ Not enough.

Instead:

```text
localize(
    content,
    language="Malay",
    country="Malaysia",
    audience="jewellery business owners",
    brand="Jade"
)
```

The localization agent receives:

```text
brand voice
target customer
country
platform
original meaning
compliance rules
CTA conventions
```

Much better.

---

# 15. Gemini

Using a current Flash-class Gemini model through AI Studio is a sensible default for this hackathon because Google still provides free-tier Gemini API access to certain models. :chatgpt-content-reference{index="13"}

Use the LLM for:

```text
research summarization
content generation
localization
lead scoring
compliance reasoning
feedback-learning prompts
scripts
```

But **not** for everything.

Normal Python should handle:

```text
status transitions
DB writes
hash comparisons
scheduling
permissions
queue processing
hard compliance rules
metrics
```

That distinction will make your system far more reliable.

One important caveat: Google's current documentation distinguishes paid-tier data treatment from free-tier usage; for a hackathon, stick to public/synthetic data unless you've reviewed the terms for real customer information. :chatgpt-content-reference{index="14"}

---

# 16. Project 2 — easiest good implementation

You have an `assets` row:

```text
status = approved
```

A Python worker runs periodically:

```python
SELECT *
FROM content_assets
WHERE status = 'approved'
AND scheduled_at <= NOW()
```

Then:

```text
publish()
     ↓
social API
     ↓
post_id
     ↓
status = published
```

Use **APScheduler** initially.

Don't bring in Celery + Redis unless you genuinely need it.

---

# 17. Very useful repo for Project 2

## Postiz

[gitroomhq/postiz-app](https://github.com/gitroomhq/postiz-app)

This is probably the most useful open-source social-media project I found for understanding the publishing side.

As of now it has about 36k stars and uses:

```text
Next.js
NestJS
Prisma
PostgreSQL
Temporal
```

It handles scheduling, analytics, team workflows and API-based automation. :chatgpt-content-reference{index="16"}

There's one catch:

**Postiz is AGPL-3.0 licensed.** :chatgpt-content-reference{index="17"}

So I would **not copy huge parts of its source into your MIT/proprietary project**.

Instead:

```text
your JA app
      ↓
Postiz as separate service/API
```

or simply study its architecture and write your small Project 2 publisher yourself.

---

# 18. Repos I would actually use

| Purpose | Repository | Verdict |
|---|---|---|
| **Frontend** | [Kiranism/next-shadcn-dashboard-starter](https://github.com/Kiranism/next-shadcn-dashboard-starter) | ⭐ **Use this** |
| Alternative frontend | [satnaing/shadcn-admin](https://github.com/satnaing/shadcn-admin?utm_source=chatgpt.com) | Excellent UI reference |
| **Agent backend** | [JoshuaC215/agent-service-toolkit](https://github.com/JoshuaC215/agent-service-toolkit) | ⭐ **Use this** |
| Agent orchestration | [langchain-ai/langgraph](https://github.com/langchain-ai/langgraph) | ⭐ Core dependency |
| **Scraping** | [unclecode/crawl4ai](https://github.com/unclecode/crawl4ai) | ⭐ **Use this** |
| Managed scraping alternative | [Firecrawl](https://github.com/firecrawl/firecrawl) | Good, but AGPL / cloud-oriented |
| Social publishing reference | [Postiz](https://github.com/gitroomhq/postiz-app) | ⭐ Great Project 2 reference |
| Deep research example | [LangChain Open Deep Research](https://github.com/langchain-ai/open_deep_research?utm_source=chatgpt.com) | Reference only |

One current gotcha: LangChain's old `open_deep_research` repo was archived on **August 21, 2026**, so I wouldn't make it the foundation of a new hackathon project. :chatgpt-content-reference{index="26"}

---

# 19. Final stack I'd choose

```text
FRONTEND
Next.js 16
TypeScript
shadcn/ui
Tailwind
TanStack Query
Recharts

        │ REST/SSE

BACKEND
Python
FastAPI
LangGraph
Pydantic

        │

AI
Gemini Flash-class model

        │

RESEARCH
Crawl4AI
Tavily / Serper

        │

DATABASE
Supabase PostgreSQL
pgvector optional
Supabase Storage
Supabase Auth

        │

VIDEO
FFmpeg
TTS API

        │

SCHEDULING
APScheduler

        │

BONUS PUBLISHING
Postiz API
OR
direct official platform APIs
```

That's a **very sane hackathon stack**.

---

# 20. Dashboard I would design

Your sidebar:

```text
JA Marketing AI

⌂ Overview

AI WORKSPACE
  ◉ Campaign Studio
  ◉ Research
  ◉ Competitors

CONTENT
  ◉ Review Queue      [12]
  ◉ Content Library
  ◉ Calendar

SALES
  ◉ Leads             [48]

INTELLIGENCE
  ◉ Lessons Learned
  ◉ Analytics

CONFIGURATION
  ◉ Brands
  ◉ Compliance Rules
  ◉ Integrations
```

### Review screen

This should be your star UI.

```text
┌───────────────────────────────────────────────────────────┐
│ DoctorShield • Instagram • Malay                    HIGH │
├────────────────────────────┬──────────────────────────────┤
│                            │ COMPLIANCE                   │
│ Generated Instagram Post   │                              │
│                            │ ✓ Tone                       │
│ Protect your practice...   │ ✓ Brand voice                │
│                            │ ⚠ Coverage claim             │
│ [IMAGE PREVIEW]            │                              │
│                            │ "Guaranteed protection"      │
│                            │ unsupported                  │
├────────────────────────────┴──────────────────────────────┤
│ Feedback                                                   │
│ [Too salesy ▼] [____________________________________]     │
│                                                           │
│ [Reject]           [Edit]                   [Approve]      │
└───────────────────────────────────────────────────────────┘
```

That's where judges will immediately understand what you've built.

---

# 21. Metrics worth showing

Don't just show:

```text
100 posts generated
```

Show:

```text
Rejection rate
32% → 14%

Average human edits/post
8.2 → 3.1

First-pass approval
49% → 78%

Compliance failure rate
18% → 7%
```

Then put:

> **"The system is learning from reviewer feedback."**

That directly proves their requested differentiator.

---

# 22. Build order

1. **Fork Kiranism dashboard + agent-service-toolkit**, connect Next.js → FastAPI → Supabase.
2. Implement `brands`, `assets`, `reviews`, `lessons` and the approval queue.
3. Build LangGraph: `Research → Content → Compliance → Human Review`.
4. Add feedback retrieval so rejected/edited posts affect the next generation.
5. Add Crawl4AI competitor monitoring and content snapshots.
6. Add Lead Agent and scoring.
7. Add localization.
8. Add FFmpeg Reel generation.
9. Add analytics dashboard.
10. **Only after Project 1 is excellent**, add Project 2 publishing.

Don't spend half the hackathon fighting Instagram OAuth while your actual required project is unfinished.

---