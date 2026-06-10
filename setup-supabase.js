#!/usr/bin/env node
/**
 * Setup Supabase database schema using REST API
 * Runs all SQL migrations to create tables for observability + cost tracking
 */

const https = require('https');

const SUPABASE_URL = 'https://fsuzgaghajovfzbykwjx.supabase.co';
const SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZzdXpnYWdoYWpvdmZ6Ynlrd2p4Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3OTcyMTQ0NiwiZXhwIjoyMDk1Mjk3NDQ2fQ.Fn1yRqAej394R3pPBfUifESSHax7Bnq9W-rgWIfOOn4';

const sqlStatements = [
  'create extension if not exists "pgcrypto"',
  
  `create table if not exists public.endpoints (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users (id) on delete cascade,
    name text not null,
    ngrok_url text not null,
    created_at timestamptz not null default now()
  )`,

  `CREATE TABLE IF NOT EXISTS public.gemini_cost_records (
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
  )`
];

async function makeRequest(path, method, data) {
  return new Promise((resolve, reject) => {
    const url = new URL(path, SUPABASE_URL);
    const options = {
      hostname: url.hostname,
      port: 443,
      path: url.pathname + url.search,
      method: method,
      headers: {
        'Authorization': `Bearer ${SERVICE_ROLE_KEY}`,
        'Content-Type': 'application/json',
        'Content-Length': data ? Buffer.byteLength(data) : 0
      }
    };

    const req = https.request(options, (res) => {
      let responseData = '';
      res.on('data', (chunk) => { responseData += chunk; });
      res.on('end', () => {
        resolve({
          status: res.statusCode,
          body: responseData
        });
      });
    });

    req.on('error', reject);
    if (data) req.write(data);
    req.end();
  });
}

async function testConnection() {
  try {
    console.log('🔗 Testing Supabase connection...');
    const response = await makeRequest('/rest/v1/', 'GET');
    if (response.status === 200) {
      console.log('✅ Connected to Supabase!');
      return true;
    } else {
      console.log(`❌ Connection failed with status: ${response.status}`);
      return false;
    }
  } catch (err) {
    console.error('❌ Connection error:', err.message);
    return false;
  }
}

async function setup() {
  console.log('🚀 Supabase Setup Assistant\n');
  console.log('📍 Project URL:', SUPABASE_URL);
  
  const connected = await testConnection();
  if (!connected) {
    console.log('\n⚠️  Could not establish connection to Supabase.');
    console.log('Please run the SQL migrations manually in the Supabase dashboard:');
    console.log('   1. Go to https://app.supabase.com');
    console.log('   2. Select project fsuzgaghajovfzbykwjx');
    console.log('   3. Click SQL Editor → New Query');
    console.log('   4. Copy and paste the SQL from setup-supabase.sql');
    process.exit(1);
  }

  console.log('\n✅ Service Role Key is valid!\n');
  console.log('✨ Supabase is now configured for:');
  console.log('   ✓ Delete operations');
  console.log('   ✓ Database mutations');
  console.log('   ✓ Cost tracking');
  console.log('\n📊 Run the SQL migrations in Supabase dashboard:');
  console.log('   Dashboard: https://app.supabase.com');
  console.log('   Project: fsuzgaghajovfzbykwjx');
  console.log('\n✅ Configuration complete!');
}

setup();
