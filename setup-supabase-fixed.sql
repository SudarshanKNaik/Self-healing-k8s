-- ============================================================================
-- UPDATED Supabase Schema Setup with RLS Policies
-- ============================================================================
-- Run this in: https://app.supabase.com → SQL Editor → New Query
-- Project: fsuzgaghajovfzbykwjx
-- ============================================================================

-- 1. Create pgcrypto extension
create extension if not exists "pgcrypto";

-- ============================================================================
-- Core Observability Tables with RLS
-- ============================================================================

-- 2. Endpoints table - stores ngrok URLs
create table if not exists public.endpoints (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  name text not null,
  ngrok_url text not null,
  created_at timestamptz not null default now()
);

create index if not exists endpoints_user_id_idx on public.endpoints (user_id);
create index if not exists endpoints_created_at_idx on public.endpoints (created_at desc);

-- Enable RLS on endpoints
ALTER TABLE public.endpoints ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if they exist
DROP POLICY IF EXISTS "Users can view their own endpoints" ON public.endpoints;
DROP POLICY IF EXISTS "Users can insert their own endpoints" ON public.endpoints;
DROP POLICY IF EXISTS "Users can delete their own endpoints" ON public.endpoints;
DROP POLICY IF EXISTS "Users can update their own endpoints" ON public.endpoints;

-- Create RLS policies for endpoints
CREATE POLICY "Users can view their own endpoints" 
  ON public.endpoints FOR SELECT 
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own endpoints"
  ON public.endpoints FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete their own endpoints"
  ON public.endpoints FOR DELETE
  USING (auth.uid() = user_id);

CREATE POLICY "Users can update their own endpoints"
  ON public.endpoints FOR UPDATE
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

-- 3. Metrics snapshots
create table if not exists public.metrics_snapshots (
  id uuid primary key default gen_random_uuid(),
  endpoint_id uuid not null references public.endpoints (id) on delete cascade,
  pod_name text not null,
  namespace text not null default 'default',
  status text not null,
  cpu_usage numeric null,
  memory_usage numeric null,
  restart_count integer not null default 0,
  timestamp timestamptz not null default now()
);

create index if not exists metrics_snapshots_endpoint_ts_idx
  on public.metrics_snapshots (endpoint_id, timestamp desc);
create index if not exists metrics_snapshots_endpoint_pod_ts_idx
  on public.metrics_snapshots (endpoint_id, pod_name, timestamp desc);

-- 4. Alert severity enum
do $$
begin
  if not exists (select 1 from pg_type where typname = 'alert_severity') then
    create type public.alert_severity as enum ('low', 'medium', 'high');
  end if;
end$$;

-- 5. Alerts table
create table if not exists public.alerts (
  id uuid primary key default gen_random_uuid(),
  endpoint_id uuid not null references public.endpoints (id) on delete cascade,
  message text not null,
  severity public.alert_severity not null default 'low',
  created_at timestamptz not null default now()
);

create index if not exists alerts_endpoint_created_at_idx
  on public.alerts (endpoint_id, created_at desc);

-- 6. Healing actions table
create table if not exists public.healing_actions (
  id uuid primary key default gen_random_uuid(),
  endpoint_id uuid not null references public.endpoints (id) on delete cascade,
  action_taken text not null,
  status text not null check (status in ('success', 'failure')),
  timestamp timestamptz not null default now()
);

create index if not exists healing_actions_endpoint_ts_idx
  on public.healing_actions (endpoint_id, timestamp desc);

-- ============================================================================
-- Cost Tracking (Gemini API)
-- ============================================================================

-- 7. Gemini cost records table
CREATE TABLE IF NOT EXISTS public.gemini_cost_records (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  stage TEXT NOT NULL,
  input_tokens INTEGER,
  output_tokens INTEGER,
  total_tokens INTEGER,
  cost_usd DECIMAL(10, 6),
  model TEXT,
  scenario TEXT,
  issue_id TEXT,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_gemini_cost_stage ON public.gemini_cost_records(stage);
CREATE INDEX IF NOT EXISTS idx_gemini_cost_created_at ON public.gemini_cost_records(created_at);
CREATE INDEX IF NOT EXISTS idx_gemini_cost_issue_id ON public.gemini_cost_records(issue_id);

-- Enable RLS on cost records
ALTER TABLE public.gemini_cost_records ENABLE ROW LEVEL SECURITY;

-- Drop existing policies
DROP POLICY IF EXISTS "Allow anon to read cost records" ON public.gemini_cost_records;
DROP POLICY IF EXISTS "Allow anon to insert cost records" ON public.gemini_cost_records;

-- Create RLS policies for cost records (allow public access)
CREATE POLICY "Allow anon to read cost records" 
  ON public.gemini_cost_records FOR SELECT 
  USING (true);

CREATE POLICY "Allow anon to insert cost records"
  ON public.gemini_cost_records FOR INSERT
  WITH CHECK (true);

-- ============================================================================
-- Test the setup
-- ============================================================================

-- Verify tables exist
SELECT 
  schemaname,
  tablename
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY tablename;
