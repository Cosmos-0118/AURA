# AURA database files

The canonical database and storage guide is
[docs/data-and-storage.md](../docs/data-and-storage.md). This file is a short
reference for the SQL artifacts in this directory.

## Runtime behavior

The API supports SQLite and MySQL. DB_ENGINE=auto tries MySQL only when
MYSQL_HOST is configured and reachable, then falls back to storage/aura.db.
DB_ENGINE=sqlite forces SQLite; DB_ENGINE=mysql requires MySQL. Regardless of
the database engine, media binaries remain on the local filesystem under
storage/campaigns/{campaign_id}/.

## MySQL setup

Ensure MySQL 8+ is running locally and create the aura database. Set these
values in the repository root .env:

~~~dotenv
DB_ENGINE=mysql
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_DATABASE=aura
MYSQL_USER=root
MYSQL_PASSWORD=your_mysql_password
~~~

Apply the schema and baseline data:

~~~bash
mysql -u root -p < db/schema.sql
mysql -u root -p aura < db/seed.sql
~~~

Start the API and frontend through the root launcher:

~~~bash
./scripts/macos/aura.sh dev
~~~

The API also creates missing tables and applies compatibility columns when it
connects, but applying db/schema.sql makes the intended starting schema
explicit. db/schema_mysql.sql and db/CampaignStudio.sql are additional
historical/export artifacts; they are not the runtime migration mechanism.

For the complete launcher, manual fallback, SQLite behavior, reset guard,
backup guidance, and schema caveats, use the canonical guide linked above.
