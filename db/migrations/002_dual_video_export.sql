-- Migration 002: Dual Video Export Support (Original AI vs Branded Export)
-- Idempotent — safe to run multiple times.

alter table video_generations
  add column if not exists branded_video_url text,
  add column if not exists branded_file_name text;

create index if not exists idx_video_gen_branded on video_generations(branded_video_url)
  where branded_video_url is not null;
