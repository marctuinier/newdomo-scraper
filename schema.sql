-- Supabase / PostgreSQL schema for the newdomo scraper.
-- Run this in the Supabase SQL editor (or psql) before the first scrape.

create table if not exists public.apartments (
    id bigint generated always as identity primary key,
    link text not null unique,
    name text,
    price integer,
    m2 integer,
    agency text,
    website text,
    city_scraped_for text,
    first_seen_at timestamptz not null default now(),
    data_json jsonb
);

-- The unique constraint on "link" is what deduplicates listings across runs:
-- re-inserting a known listing fails with error 23505, which the scraper
-- treats as "already seen".

create index if not exists apartments_city_idx on public.apartments (city_scraped_for);
create index if not exists apartments_first_seen_idx on public.apartments (first_seen_at desc);

-- Recommended: enable row level security so the anon key cannot read/write.
-- The scraper uses the service role key, which bypasses RLS.
alter table public.apartments enable row level security;
