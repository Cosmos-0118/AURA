# AURA

AI-powered marketing department dashboard for the JA Assure hackathon: research → generate → compliance → human review → learn from corrections.

**This is not a chatbot.**

## Team: start here

| You are | Open this |
|---|---|
| Anyone, first 30 minutes | [docs/00-START-HERE.md](docs/00-START-HERE.md) |
| Your Cursor agent | [AGENTS.md](AGENTS.md) then your member doc |
| Team Member 1 | [docs/members/TEAM-MEMBER-1.md](docs/members/TEAM-MEMBER-1.md) |
| Team Member 2 | [docs/members/TEAM-MEMBER-2.md](docs/members/TEAM-MEMBER-2.md) |
| Team Member 3 | [docs/members/TEAM-MEMBER-3.md](docs/members/TEAM-MEMBER-3.md) |
| Team Member 4 | [docs/members/TEAM-MEMBER-4.md](docs/members/TEAM-MEMBER-4.md) |
| Team Member 5 | [docs/members/TEAM-MEMBER-5.md](docs/members/TEAM-MEMBER-5.md) |

Install and run: [docs/02-SETUP.md](docs/02-SETUP.md)  
Frozen API/DB shapes: [docs/03-CONTRACTS.md](docs/03-CONTRACTS.md)  
Git and folders: [docs/04-WORKFLOW-RULES.md](docs/04-WORKFLOW-RULES.md)

Do not write feature code until Team Member 1 posts **contracts are in main**.

## Stack (do not replace)

- Frontend: Next.js dashboard cloned from [Kiranism/next-shadcn-dashboard-starter](https://github.com/Kiranism/next-shadcn-dashboard-starter) into `web/`
- Backend: new FastAPI app in `api/` (not a fork of agent-service-toolkit)
- DB: one shared Supabase Postgres
- LLM: Gemini Flash, **one API key per person**

## Local run (after scaffold exists)

```bash
# terminal A
cd api && uv run uvicorn main:app --reload --port 8000

# terminal B
cd web && bun run dev
```

Dashboard: http://localhost:3000  
API docs: http://localhost:8000/docs
