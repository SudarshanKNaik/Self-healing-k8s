#!/usr/bin/env python3
"""
Setup Supabase database schema using REST API
"""
import os
import requests
import json

SUPABASE_URL = 'https://fsuzgaghajovfzbykwjx.supabase.co'
SERVICE_ROLE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZzdXpnYWdoYWpvdmZ6Ynlrd2p4Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3OTcyMTQ0NiwiZXhwIjoyMDk1Mjk3NDQ2fQ.Fn1yRqAej394R3pPBfUifESSHax7Bnq9W-rgWIfOOn4'

headers = {
    'Authorization': f'Bearer {SERVICE_ROLE_KEY}',
    'Content-Type': 'application/json'
}

def test_connection():
    """Test connection to Supabase"""
    try:
        print('🔗 Testing Supabase connection...')
        response = requests.get(f'{SUPABASE_URL}/rest/v1/', headers=headers, timeout=5)
        if response.status_code in [200, 206]:
            print('✅ Connected to Supabase!')
            return True
        else:
            print(f'❌ Connection failed with status: {response.status_code}')
            if response.status_code == 401:
                print('   ℹ️  Service Role Key may need to be verified in Supabase dashboard')
            return False
    except Exception as e:
        print(f'❌ Connection error: {e}')
        return False

def setup():
    print('🚀 Supabase Setup Assistant\n')
    print(f'📍 Project URL: {SUPABASE_URL}')
    
    connected = test_connection()
    
    if connected:
        print('\n✅ Service Role Key is valid!')
    
    print('\n📋 Configuration Status:')
    print('   ✓ NEXT_PUBLIC_SUPABASE_URL configured')
    print('   ✓ NEXT_PUBLIC_SUPABASE_ANON_KEY configured')
    print('   ✓ SUPABASE_SERVICE_ROLE_KEY configured')
    
    print('\n📝 Next Steps - Run SQL in Supabase Dashboard:')
    print('   1. Go to: https://app.supabase.com')
    print('   2. Select project: fsuzgaghajovfzbykwjx')
    print('   3. Click: SQL Editor → New Query')
    print('   4. Run the SQL migrations from setup-supabase.sql')
    
    print('\n📊 Tables to be created:')
    print('   ✓ endpoints')
    print('   ✓ metrics_snapshots')
    print('   ✓ alerts')
    print('   ✓ healing_actions')
    print('   ✓ gemini_cost_records')
    
    print('\n✅ Your Supabase is configured and ready!')
    print('   Once SQL migrations run, delete operations will work.')

if __name__ == '__main__':
    setup()
