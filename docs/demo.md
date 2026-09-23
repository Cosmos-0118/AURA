# Reliable demo walkthrough

## Deterministic local path

Use the default template values:

~~~dotenv
DEMO_MODE=true
AURA_MOCK_AGENTS=true
AURA_COMPETITOR_INTELLIGENCE=false
~~~

Start the core application:

~~~bash
cp .env.example .env
cp web/env.example.txt web/.env.local
./scripts/macos/aura.sh dev
~~~

Open http://localhost:3000/dashboard/studio.

1. Choose a seeded brand such as Jade, DoctorShield, or Jaguar Transit.
2. Enter a concrete objective, thesis, audience, and one or more platforms.
3. Generate the campaign and inspect the returned platform package.
4. If media is needed, generate an image or local/demo video, then apply the
   brand watermark.
5. Submit the package to the Review Queue.
6. In /dashboard/review, reject it with a reason such as TOO_SALESY and a
   specific note.
7. Open History and confirm the `lesson_created` audit event. For the saved
   lesson record itself, call `GET /api/lessons?brand_id=...` (or inspect the
   lesson in the API response).
8. Resubmit after editing, or approve it to demonstrate the publication-ready
   state. Do not click publish unless Buffer and public media are configured.

The key product demonstration is the closed loop:

~~~text
generated copy -> human correction -> lesson saved -> future generation guidance
~~~

## SQL-backed fixture

For a MySQL demonstration with richer historic campaign/review/media data,
apply db/schema.sql, then load db/demo.sql in a disposable aura database. The
fixture includes approved/rejected examples, events, review entries, and
lessons. It is not automatically loaded into a fresh SQLite database.

## Live-provider demo

Set DEMO_MODE=false and configure GROQ_API_KEY for real text generation. Add
FAL_KEY for real image/video generation. Keep the review step mandatory. For
publishing, follow buffer-publishing.md and verify /api/media/config before
using a real Buffer channel.
