# Start here

Read this page first. Then read `docs/03-CONTRACTS.md` and **your** file in `docs/members/`. Do not read every member doc — only yours plus the shared ones.

## What we are building

AURA is an **AI-powered marketing department with a dashboard**, not a chatbot.

A human picks a brand, a topic, a country, and a campaign goal. The system:

1. Looks at competitor public pages (optional, later).
2. Writes LinkedIn / Instagram / X / blog / reel-script content in that brand's voice.
3. Runs a compliance check so unsupported insurance claims never reach a reviewer as "fine".
4. Puts every asset in a **Review Queue**. A human approves, edits, or rejects.
5. Saves the correction as a **lesson**. The next generation for that brand is better.

That loop — **compliance + human review + learning from feedback** — is the product. Generating posts is table stakes.

Three JA Assure brands must sound different:

| Brand | Voice |
|---|---|
| **Jade** | Authoritative, premium, specialist, B2B. Jewellery / gold / watches / high-value risks. |
| **DoctorShield** | Reassuring, professional, educational, human. Doctors and clinics. |
| **Jaguar Transit** | Fast, technological, security-focused, operational. Cash / jewellery / valuables in transit. |

## The team (5 people, 5 zones)

| Person | Role | One-line job | Your doc |
|---|---|---|---|
| **Team Member 1** | Platform + Integration Lead | Repo, database, API, orchestrator, merges, demo | [TEAM-MEMBER-1.md](members/TEAM-MEMBER-1.md) |
| **Team Member 2** | Review UI | The screen judges will stare at: queue, approve/edit/reject | [TEAM-MEMBER-2.md](members/TEAM-MEMBER-2.md) |
| **Team Member 3** | Studio + Intelligence UI | Campaign form, brands, competitors, leads, charts | [TEAM-MEMBER-3.md](members/TEAM-MEMBER-3.md) |
| **Team Member 4** | Content Engine | Brand-voice generation + localization | [TEAM-MEMBER-4.md](members/TEAM-MEMBER-4.md) |
| **Team Member 5** | Compliance + Learning | Rules scanner, LLM reviewer, lessons, competitor snapshots | [TEAM-MEMBER-5.md](members/TEAM-MEMBER-5.md) |

Team Member 1 is the only person who edits shared files. Everyone else stays in their folder. That is how we combine at the end without a 4-hour merge fight.

## The three rules

1. **One repo, five disjoint folders.** You never open someone else's files to "just fix" them. Ping Team Member 1.
2. **Contracts freeze at Hour 3.** After that, `api/schemas.py` and `docs/03-CONTRACTS.md` do not change unless Team Member 1 announces it in the team channel.
3. **Mock-first.** Your module returns realistic fake data from the first hour you code. Other people keep moving.

Full git / conflict rules: [04-WORKFLOW-RULES.md](04-WORKFLOW-RULES.md).

## Repos and accounts you need

You will **not** invent a stack. Use exactly this:

| Piece | What we use | Why |
|---|---|---|
| Frontend | Fork/clone [Kiranism/next-shadcn-dashboard-starter](https://github.com/Kiranism/next-shadcn-dashboard-starter) into `web/` | Working tables, forms, charts. Has `AGENTS.md` for Cursor. MIT. |
| Backend | New FastAPI app in `api/` (uv) | AURA is a batch pipeline, not a chat service. Do **not** fork agent-service-toolkit. |
| Database | One shared **Supabase** Postgres project | Team Member 1 creates it. Everyone else only needs the URL + anon/service key in `.env`. |
| LLM | **Gemini Flash** via Google AI Studio | Each person uses **their own** free-tier API key. A shared key will die under 5 parallel agents. |
| Scraper (Phase 3 only) | `httpx` + `trafilatura`. Crawl4AI is optional later. | Playwright browsers eat hours. |
| Video (Phase 3 only) | Script + TTS + stills. FFmpeg MP4 if time. | Cinematic AI video is out of scope. |

Reference only (read, do not copy into the repo):

- [JoshuaC215/agent-service-toolkit](https://github.com/JoshuaC215/agent-service-toolkit) — LangGraph `interrupt()` ideas. Not our backend.
- [gitroomhq/postiz-app](https://github.com/gitroomhq/postiz-app) — publishing ideas. **AGPL — do not copy source.**
- [unclecode/crawl4ai](https://github.com/unclecode/crawl4ai) — scraper upgrade if Phase 3 has spare time.

## What "done" looks like for the demo

Live, on a laptop, in under 8 minutes:

1. Open Campaign Studio. Pick **Jade**, topic "Jewellery theft prevention", country Malaysia, goal Awareness.
2. Hit Generate. Pipeline progress appears.
3. Review Queue fills. Open an Instagram post. Compliance panel flags `"guaranteed protection"`.
4. Reviewer edits the copy, tags **Too salesy**, hits Reject (or Approve after edit).
5. Regenerate. The new draft is clearly less salesy. Approve.
6. Switch brand to **DoctorShield**, same topic type. Tone is educational, not premium-B2B.
7. Insights page shows: rejection rate, first-pass approval, "the system is learning".

If we only have 24 hours, steps 1–5 with two brands is enough. Everything else is bonus. See [05-TIMELINE.md](05-TIMELINE.md).

## Reading order (30 minutes, then you work)

1. This file.
2. [02-SETUP.md](02-SETUP.md) — install, clone, run.
3. [03-CONTRACTS.md](03-CONTRACTS.md) — the shapes you must not invent.
4. [04-WORKFLOW-RULES.md](04-WORKFLOW-RULES.md) — git and folders.
5. Your `docs/members/TEAM-MEMBER-N.md` — paste the agent prompts from there into Cursor.
6. Skim [05-TIMELINE.md](05-TIMELINE.md) so you know when to stop adding features.
7. Keep [troubleshooting.md](troubleshooting.md) open.

Do not start coding until Team Member 1 posts "contracts are in `main`" in the team channel. Until then: install tools, get a Gemini key, read your member doc.

## Shared docs index

| File | What it is |
|---|---|
| [01-ARCHITECTURE.md](01-ARCHITECTURE.md) | How the pieces fit. Why we skipped some Concept.md ideas. |
| [02-SETUP.md](02-SETUP.md) | Exact commands. |
| [03-CONTRACTS.md](03-CONTRACTS.md) | DB, REST, Pydantic, TypeScript, agent function signatures. |
| [04-WORKFLOW-RULES.md](04-WORKFLOW-RULES.md) | Ownership, git, merge, "I need a shared change". |
| [05-TIMELINE.md](05-TIMELINE.md) | Hour-by-hour, checkpoints, 24h cut line. |
| [06-DEMO-SCRIPT.md](06-DEMO-SCRIPT.md) | Spoken script, seeded data, fallbacks. |
| [troubleshooting.md](troubleshooting.md) | The 15 failures you will actually hit. |
| [../AGENTS.md](../AGENTS.md) | Rules your Cursor agent must follow. |
| [../Concept.md](../Concept.md) | Original product thinking. Specs in `docs/` win if they disagree. |
