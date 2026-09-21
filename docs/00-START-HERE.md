# Start here

Read this page first. Then read `docs/03-CONTRACTS.md` and **your** file in `docs/members/`. Do not read every member doc — only yours plus the shared ones.

## What we are building

AURA is an **AI-powered marketing department with a dashboard**, not a chatbot.

A human picks a brand, a topic, a country, and a campaign goal. The system:

1. Writes **LinkedIn** copy in that brand's voice (Jade ≠ DoctorShield ≠ Jaguar).
2. Runs a compliance check so unsupported insurance claims never reach a reviewer as "fine".
3. Puts every asset in a **Review Queue**. A human approves, edits, or rejects.
4. Saves the correction as a **lesson**.

We have **6–8 hours**. Competitor crawl, leads, reels, localization, X, and blogs are **out**. Seed a FAIL Instagram post so the compliance demo does not depend on Gemini.

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
| **Team Member 3** | Studio + Intelligence UI | Campaign form, brands, insights numbers | [TEAM-MEMBER-3.md](members/TEAM-MEMBER-3.md) |
| **Team Member 4** | Content Engine | Brand-voice LinkedIn generation | [TEAM-MEMBER-4.md](members/TEAM-MEMBER-4.md) |
| **Team Member 5** | Compliance + Learning | Banned-term scanner + lessons write/read | [TEAM-MEMBER-5.md](members/TEAM-MEMBER-5.md) |

Team Member 1 is the only person who edits shared files. Everyone else stays in their folder. That is how we combine at the end without a 4-hour merge fight.

## The three rules

1. **One repo, five disjoint folders.** You never open someone else's files to "just fix" them. Ping Team Member 1.
2. **Contracts freeze at T+1.5h.** After that, `api/schemas.py` and `docs/03-CONTRACTS.md` do not change unless Team Member 1 announces it in the team channel.
3. **Mock-first.** Your module returns realistic fake data from the first hour you code. Other people keep moving.

Full git / conflict rules: [04-WORKFLOW-RULES.md](04-WORKFLOW-RULES.md).

## Repos and accounts you need

You will **not** invent a stack. Use exactly this:

| Piece | What we use | Why |
|---|---|---|
| Frontend | Fork/clone [Kiranism/next-shadcn-dashboard-starter](https://github.com/Kiranism/next-shadcn-dashboard-starter) into `web/` | Next 16 + React 19, working data tables and forms. MIT. Delete its own `AGENTS.md` / `CLAUDE.md` after cloning — ours must win. |
| Backend | New FastAPI app in `api/` (uv) | AURA is a batch pipeline, not a chat service. Do **not** fork agent-service-toolkit. |
| Database | One shared **Supabase** Postgres project | Team Member 1 creates it. Everyone else only needs the URL + anon/service key in `.env`. |
| LLM | **Gemini Flash** via Google AI Studio | Each person uses **their own** free-tier API key. A shared key will die under 5 parallel agents. |
| Scraper / video / leads | **Do not build** | 6–8 hours is not enough |

Reference only (read, do not copy into the repo):

- [JoshuaC215/agent-service-toolkit](https://github.com/JoshuaC215/agent-service-toolkit) — not our backend.
- [gitroomhq/postiz-app](https://github.com/gitroomhq/postiz-app) — **AGPL — do not copy source.**

## What "done" looks like for the demo

Live, on a laptop, in **under 6 minutes**:

1. Open **Brands**. Jade vs DoctorShield — different tones.
2. Open **Review Queue**. Seeded Instagram post. Compliance flags `"guaranteed protection"`.
3. Reject with tag **Unsupported claim**. Lesson appears on **Insights**.
4. **Campaign Studio**: Jade / jewellery theft / Malaysia / LinkedIn → Generate (or show mock if Gemini is slow).
5. Point at Insights numbers: "the system is learning from reviewer feedback."

Regenerate-after-reject is optional. Do not spend the last hour on it. See [05-TIMELINE.md](05-TIMELINE.md).

## Reading order (15 minutes, then you work)

1. This file.
2. [05-TIMELINE.md](05-TIMELINE.md) — what is in vs out.
3. [02-SETUP.md](02-SETUP.md) — install, clone, run.
4. [03-CONTRACTS.md](03-CONTRACTS.md) — the shapes you must not invent.
5. Your `docs/members/TEAM-MEMBER-N.md` — paste the **Must** agent prompts into Cursor.

M2/M3/M4/M5 start **immediately** (mocks from contracts §10). You do not sit idle while M1 scaffolds. Do not invent extra products while you wait.

## Shared docs index

| File | What it is |
|---|---|
| [01-ARCHITECTURE.md](01-ARCHITECTURE.md) | How the pieces fit. Why we skipped some Concept.md ideas. |
| [02-SETUP.md](02-SETUP.md) | Exact commands. |
| [03-CONTRACTS.md](03-CONTRACTS.md) | DB, REST, Pydantic, TypeScript, agent function signatures. |
| [04-WORKFLOW-RULES.md](04-WORKFLOW-RULES.md) | Ownership, git, merge, "I need a shared change". |
| [05-TIMELINE.md](05-TIMELINE.md) | 6–8 hour schedule. Must / out of scope. |
| [06-DEMO-SCRIPT.md](06-DEMO-SCRIPT.md) | Spoken script, seeded data, fallbacks. |
| [troubleshooting.md](troubleshooting.md) | The 15 failures you will actually hit. |
| [../AGENTS.md](../AGENTS.md) | Rules your Cursor agent must follow. |
| [../Concept.md](../Concept.md) | Original product thinking. Specs in `docs/` win if they disagree. |
