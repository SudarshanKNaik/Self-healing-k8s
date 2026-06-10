# 🚀 Complete Supabase Setup Guide

## Your Supabase Instance

```
Project ID: fsuzgaghajovfzbykwjx
URL: https://fsuzgaghajovfzbykwjx.supabase.co
Database: postgres.fsuzgaghajovfzbykwjx.supabase.co:5432
```

---

## Step 1: Update Environment Variables

Update `h24-app/.env.local` with your new Supabase credentials:

```env
NEXT_PUBLIC_SUPABASE_URL=https://fsuzgaghajovfzbykwjx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=sb_publishable_91f874lTvloVNqpfITDzDw_ENYPOi7A
SUPABASE_SERVICE_ROLE_KEY=YOUR_SERVICE_ROLE_KEY_HERE
```

**To get your SERVICE_ROLE_KEY:**
1. Go to https://app.supabase.com
2. Select project `fsuzgaghajovfzbykwjx`
3. Click "Settings" → "API" 
4. Copy the **Service Role** key (not the Anon key)
5. Paste it as `SUPABASE_SERVICE_ROLE_KEY`

---

## Step 2: Run SQL Migrations

Go to **Supabase Dashboard** → **SQL Editor** → **New Query** and run these SQL scripts in order:

### Migration 1: Core Schema (001_init.sql)

```sql
-- KubePulse: Supabase schema + RLS
create extension if not exists "pgcrypto";

-- 1) endpoints
create table if not exists public.endpoints (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  name text not null,
  ngrok_url text not null,
  created_at timestamptz not null default now()
);

create index if not exists endpoints_user_id_idx on public.endpoints (user_id);
create index if not exists endpoints_created_at_idx on public.endpoints (created_at desc);

-- 2) metrics_snapshots
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

-- 3) Create alert_severity enum
do $$
begin
  if not exists (select 1 from pg_type where typname = 'alert_severity') then
    create type public.alert_severity as enum ('low', 'medium', 'high');
  end if;
end$$;

-- 4) alerts
create table if not exists public.alerts (
  id uuid primary key default gen_random_uuid(),
  endpoint_id uuid not null references public.endpoints (id) on delete cascade,
  message text not null,
  severity public.alert_severity not null default 'low',
  created_at timestamptz not null default now()
);

create index if not exists alerts_endpoint_created_at_idx
  on public.alerts (endpoint_id, created_at desc);

-- 5) healing_actions
create table if not exists public.healing_actions (
  id uuid primary key default gen_random_uuid(),
  endpoint_id uuid not null references public.endpoints (id) on delete cascade,
  action_taken text not null,
  status text not null check (status in ('success', 'failure')),
  timestamp timestamptz not null default now()
);

create index if not exists healing_actions_endpoint_ts_idx
  on public.healing_actions (endpoint_id, timestamp desc);

-- 6) normalized metrics series (Prometheus-like)
create table if not exists public.metrics_series (
  id uuid primary key default gen_random_uuid(),
  endpoint_id uuid not null references public.endpoints (id) on delete cascade,
  metric_name text not null,
  labels jsonb not null default '{}'::jsonb,
  value double precision not null,
  source text not null default 'scrape' check (source in ('scrape', 'push', 'derived')),
  timestamp timestamptz not null default now()
);

create index if not exists metrics_series_endpoint_metric_ts_idx
  on public.metrics_series (endpoint_id, metric_name, timestamp desc);
create index if not exists metrics_series_endpoint_ts_idx
  on public.metrics_series (endpoint_id, timestamp desc);
create index if not exists metrics_series_labels_gin_idx
  on public.metrics_series using gin (labels);

-- 7) pre-aggregated rollups for fast dashboards
create table if not exists public.metrics_rollups (
  id uuid primary key default gen_random_uuid(),
  endpoint_id uuid not null references public.endpoints (id) on delete cascade,
  bucket_start timestamptz not null,
  scope text not null check (scope in ('cluster', 'pod', 'namespace')),
  group_key text not null,
  avg_cpu double precision null,
  avg_memory double precision null,
  pod_running integer not null default 0,
  pod_failed integer not null default 0,
  pod_pending integer not null default 0,
  restart_rate double precision not null default 0,
  sample_count integer not null default 0,
  created_at timestamptz not null default now(),
  unique (endpoint_id, bucket_start, scope, group_key)
);

create index if not exists metrics_rollups_endpoint_bucket_idx
  on public.metrics_rollups (endpoint_id, bucket_start desc, scope);

-- 8) central logs table (Loki-like)
create table if not exists public.logs_entries (
  id uuid primary key default gen_random_uuid(),
  endpoint_id uuid null references public.endpoints (id) on delete set null,
  timestamp timestamptz not null default now(),
  labels jsonb not null default '{}'::jsonb,
  message text not null,
  source text not null default 'pod' check (source in ('pod', 'container', 'agent', 'system')),
  level text not null default 'info',
  correlation_id text null
);

create index if not exists logs_entries_endpoint_ts_idx
  on public.logs_entries (endpoint_id, timestamp desc);
create index if not exists logs_entries_labels_gin_idx
  on public.logs_entries using gin (labels);

-- 9) generic event timeline + lifecycle (AI + alerts + anomalies)
create table if not exists public.observability_events (
  id uuid primary key default gen_random_uuid(),
  endpoint_id uuid null references public.endpoints (id) on delete set null,
  correlation_id text null,
  event_type text not null,
  related_resource text null,
  related_kind text null,
  severity text not null default 'info' check (severity in ('info', 'warning', 'critical')),
  title text not null,
  details jsonb not null default '{}'::jsonb,
  timestamp timestamptz not null default now()
);

create index if not exists observability_events_endpoint_ts_idx
  on public.observability_events (endpoint_id, timestamp desc);
create index if not exists observability_events_type_ts_idx
  on public.observability_events (event_type, timestamp desc);

create table if not exists public.issue_lifecycles (
  id uuid primary key default gen_random_uuid(),
  endpoint_id uuid null references public.endpoints (id) on delete set null,
  issue_id text not null,
  title text not null,
  status text not null,
  detected_at timestamptz null,
  analysis_started_at timestamptz null,
  fix_applied_at timestamptz null,
  resolved_at timestamptz null,
  failed_at timestamptz null,
  updated_at timestamptz not null default now(),
  unique (endpoint_id, issue_id)
);

create index if not exists issue_lifecycles_endpoint_updated_idx
  on public.issue_lifecycles (endpoint_id, updated_at desc);
```

### Migration 2: Alerting Rules (002_observability_upgrade.sql)

```sql
-- KubePulse observability backend upgrade
create extension if not exists "pgcrypto";

-- Ensure enum exists
do $$
begin
  if not exists (select 1 from pg_type where typname = 'alert_severity') then
    create type public.alert_severity as enum ('low', 'medium', 'high');
  end if;
end$$;

-- Alert rules and state management
create table if not exists public.alert_rules (
  id uuid primary key default gen_random_uuid(),
  endpoint_id uuid null references public.endpoints (id) on delete cascade,
  rule_key text not null,
  metric_name text not null,
  aggregation text not null default 'avg' check (aggregation in ('avg', 'sum', 'min', 'max', 'rate')),
  threshold double precision not null,
  duration_seconds integer not null default 300,
  severity public.alert_severity not null default 'medium',
  enabled boolean not null default true,
  created_at timestamptz not null default now(),
  unique (endpoint_id, rule_key)
);

create table if not exists public.alert_states (
  id uuid primary key default gen_random_uuid(),
  endpoint_id uuid not null references public.endpoints (id) on delete cascade,
  rule_key text not null,
  state text not null check (state in ('pending', 'firing', 'resolved')),
  state_since timestamptz not null default now(),
  last_value double precision null,
  updated_at timestamptz not null default now(),
  unique (endpoint_id, rule_key)
);

create table if not exists public.alert_state_history (
  id uuid primary key default gen_random_uuid(),
  endpoint_id uuid not null references public.endpoints (id) on delete cascade,
  rule_key text not null,
  state text not null check (state in ('pending', 'firing', 'resolved')),
  value double precision null,
  message text not null,
  timestamp timestamptz not null default now()
);

create index if not exists alert_state_history_endpoint_ts_idx
  on public.alert_state_history (endpoint_id, timestamp desc);

-- Enable RLS for new tables
alter table if exists public.alert_rules enable row level security;
alter table if exists public.alert_states enable row level security;
alter table if exists public.alert_state_history enable row level security;
```

### Migration 3: Cost Tracking (003_gemini_cost_tracking.sql) ⭐ **IMPORTANT**

```sql
-- Create gemini_cost_records table for AI cost tracking
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

-- Create indexes for faster queries
CREATE INDEX IF NOT EXISTS idx_gemini_cost_stage ON public.gemini_cost_records(stage);
CREATE INDEX IF NOT EXISTS idx_gemini_cost_created_at ON public.gemini_cost_records(created_at);
CREATE INDEX IF NOT EXISTS idx_gemini_cost_issue_id ON public.gemini_cost_records(issue_id);

-- Enable RLS if needed
ALTER TABLE public.gemini_cost_records ENABLE ROW LEVEL SECURITY;

-- Allow anon key to read/insert (for public access)
DROP POLICY IF EXISTS "Allow anon to read cost records" ON public.gemini_cost_records;
DROP POLICY IF EXISTS "Allow anon to insert cost records" ON public.gemini_cost_records;

CREATE POLICY "Allow anon to read cost records" 
  ON public.gemini_cost_records FOR SELECT 
  USING (true);

CREATE POLICY "Allow anon to insert cost records"
  ON public.gemini_cost_records FOR INSERT
  WITH CHECK (true);
```

---

## Step 3: Verify Tables Were Created

In Supabase Dashboard:
1. Click **"Table Editor"** in the left sidebar
2. You should see these tables:
   - ✅ `endpoints`
   - ✅ `metrics_snapshots`
   - ✅ `alerts`
   - ✅ `healing_actions`
   - ✅ `metrics_series`
   - ✅ `metrics_rollups`
   - ✅ `logs_entries`
   - ✅ `observability_events`
   - ✅ `issue_lifecycles`
   - ✅ `alert_rules`
   - ✅ `alert_states`
   - ✅ `alert_state_history`
   - ✅ `gemini_cost_records` ⭐ (Most important for cost tracking)

---

## Step 4: Test the Connection

After updating `.env.local`, restart the Next.js server:

```powershell
cd d:\k8s-self-healing\h24-app
npm run dev
```

Visit http://localhost:3000/dashboard and check:
- ✅ No "Supabase env vars are missing" warning
- ✅ Dashboard should show real data (if you've run healing operations)
- ✅ Cost tracking should display in the dashboard

---

## Useful SQL Queries for Your Dashboard

### Query 1: View All Cost Records

```sql
SELECT * FROM public.gemini_cost_records
ORDER BY created_at DESC
LIMIT 100;
```

### Query 2: Cost Summary by Stage

```sql
SELECT 
  stage,
  COUNT(*) as total_calls,
  SUM(total_tokens) as total_tokens_used,
  AVG(total_tokens) as avg_tokens_per_call,
  SUM(cost_usd) as total_cost_usd,
  AVG(cost_usd) as avg_cost_per_call
FROM public.gemini_cost_records
GROUP BY stage
ORDER BY total_cost_usd DESC;
```

### Query 3: Cost by Scenario (Problem Type)

```sql
SELECT 
  scenario,
  COUNT(*) as incident_count,
  SUM(cost_usd) as total_cost_usd,
  AVG(cost_usd) as avg_cost_per_incident,
  MAX(total_tokens) as max_tokens_used
FROM public.gemini_cost_records
WHERE created_at >= NOW() - INTERVAL '30 days'
GROUP BY scenario
ORDER BY total_cost_usd DESC;
```

### Query 4: Daily Cost Trend

```sql
SELECT 
  DATE(created_at) as date,
  COUNT(*) as api_calls,
  SUM(total_tokens) as tokens,
  SUM(cost_usd) as daily_cost_usd
FROM public.gemini_cost_records
WHERE created_at >= NOW() - INTERVAL '30 days'
GROUP BY DATE(created_at)
ORDER BY date DESC;
```

### Query 5: Issue Lifecycle Tracking

```sql
SELECT 
  issue_id,
  title,
  status,
  detected_at,
  analysis_started_at,
  fix_applied_at,
  resolved_at,
  EXTRACT(EPOCH FROM (resolved_at - detected_at)) / 60 as resolution_minutes
FROM public.issue_lifecycles
WHERE endpoint_id IS NOT NULL
ORDER BY detected_at DESC
LIMIT 50;
```

### Query 6: Healing Actions History

```sql
SELECT 
  endpoint_id,
  action_taken,
  status,
  timestamp,
  EXTRACT(EPOCH FROM (NOW() - timestamp)) / 3600 as hours_ago
FROM public.healing_actions
ORDER BY timestamp DESC
LIMIT 50;
```

---

## Troubleshooting

### "Could not find table 'public.gemini_cost_records'"
→ Run Migration 3 (003_gemini_cost_tracking.sql) above

### "RLS policy prevents access"
→ Go to **Table Editor** → select table → **Auth** tab → Toggle RLS OFF temporarily

### "NEXT_PUBLIC_SUPABASE_URL is undefined"
→ Make sure `.env.local` has the correct URL and restart `npm run dev`

### Cost records not showing in dashboard
→ Check that RLS policies were created correctly with the INSERT/SELECT policies above

---

## Your System Status ✅

- Minikube: Running
- Flask API (port 5000): Running  
- ngrok tunnel: Running
- Next.js app (port 3000): Running
- Supabase: Ready to configure

**Next:** Update `.env.local`, run the SQL migrations, and restart the Next.js server!
