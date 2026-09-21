-- AURA database schema. Owner: Team Member 1.

create extension if not exists "pgcrypto";

create table if not exists brands (
  id            text primary key,
  name          text not null,
  tone          jsonb not null,
  audience      text not null,
  do_list       jsonb not null default '[]',
  dont_list     jsonb not null default '[]',
  created_at    timestamptz not null default now()
);

create table if not exists competitors (
  id            uuid primary key default gen_random_uuid(),
  brand_id      text not null references brands(id),
  name          text not null,
  url           text not null,
  created_at    timestamptz not null default now()
);

create table if not exists research_snapshots (
  id             uuid primary key default gen_random_uuid(),
  competitor_id  uuid not null references competitors(id) on delete cascade,
  content_hash   text not null,
  content        text not null,
  change_summary text,
  scraped_at     timestamptz not null default now()
);

create table if not exists campaigns (
  id           uuid primary key default gen_random_uuid(),
  brand_id     text not null references brands(id),
  topic        text not null,
  country      text not null,
  goal         text not null,
  platforms    jsonb not null,
  language     text not null default 'en',
  status       text not null default 'queued'
               check (status in ('queued', 'running', 'completed', 'failed')),
  error        text,
  created_at   timestamptz not null default now(),
  completed_at timestamptz
);

create table if not exists content_assets (
  id           uuid primary key default gen_random_uuid(),
  campaign_id  uuid references campaigns(id) on delete set null,
  brand_id     text not null references brands(id),
  platform     text not null,
  content_type text not null,
  variant      text not null default 'A',
  language     text not null default 'en',
  title        text,
  body         text not null,
  hashtags     jsonb not null default '[]',
  media_url    text,
  status       text not null default 'pending_review'
               check (status in (
                 'draft', 'pending_review', 'compliance_failed',
                 'approved', 'rejected', 'scheduled', 'published'
               )),
  created_at   timestamptz not null default now(),
  approved_at  timestamptz,
  approved_by  text
);

create table if not exists compliance_checks (
  id                 uuid primary key default gen_random_uuid(),
  asset_id           uuid not null references content_assets(id) on delete cascade,
  result             text not null check (result in ('PASS', 'REVIEW', 'FAIL')),
  risk               text not null check (risk in ('LOW', 'MEDIUM', 'HIGH')),
  rules              jsonb not null default '[]',
  issues             jsonb not null default '[]',
  suggested_revision text,
  created_at         timestamptz not null default now()
);

create table if not exists reviews (
  id            uuid primary key default gen_random_uuid(),
  asset_id      uuid not null references content_assets(id) on delete cascade,
  action        text not null check (action in ('approve', 'reject', 'edit')),
  reason_tag    text,
  note          text,
  original_body text,
  edited_body   text,
  created_at    timestamptz not null default now()
);

create table if not exists lessons (
  id            uuid primary key default gen_random_uuid(),
  brand_id      text not null references brands(id),
  platform      text,
  reason_tag    text not null,
  note          text not null,
  original_body text,
  edited_body   text,
  asset_id      uuid references content_assets(id) on delete set null,
  created_at    timestamptz not null default now()
);

create table if not exists leads (
  id         uuid primary key default gen_random_uuid(),
  brand_id   text not null references brands(id),
  name       text not null,
  url        text,
  country    text,
  fit_score  int not null default 0,
  why        text,
  created_at timestamptz not null default now()
);

create index if not exists idx_assets_status on content_assets(status);
create index if not exists idx_assets_brand on content_assets(brand_id);
create index if not exists idx_lessons_brand on lessons(brand_id);
create index if not exists idx_checks_asset on compliance_checks(asset_id);
