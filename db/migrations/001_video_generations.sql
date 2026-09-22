-- Migration 001: Video Generation History
-- Idempotent — safe to run multiple times.
-- Run with: psql $DATABASE_URL -f db/migrations/001_video_generations.sql

create table if not exists video_generations (
  id            uuid        primary key default gen_random_uuid(),
  brand_id      text        references brands(id) on delete set null,
  asset_id      uuid        references content_assets(id) on delete set null,
  prompt        text        not null,
  aspect_ratio  text        not null default '9:16',
  resolution    text        not null default '768P',
  duration_secs int         not null default 5,
  model         text        not null default 'minimax/h3-max-turbo/text-to-video',
  video_url     text,
  file_name     text,
  file_size     bigint,
  status        text        not null default 'COMPLETED'
                check (status in ('COMPLETED', 'FAILED', 'IN_PROGRESS')),
  error_msg     text,
  request_id    text,
  created_at    timestamptz not null default now()
);

create index if not exists idx_video_gen_created on video_generations(created_at desc);
create index if not exists idx_video_gen_brand   on video_generations(brand_id);
