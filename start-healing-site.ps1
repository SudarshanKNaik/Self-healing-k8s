# Ayush Healing Backend Logs - Startup Script
# This script starts the h24-app website with healing execution logging

$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$h24AppRoot = Join-Path $projectRoot "h24-app"
$logFilePath = Join-Path $h24AppRoot "ayush.md"

Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║     Ayush - Healing Backend Logging System                    ║" -ForegroundColor Cyan
Write-Host "║     Starting Next.js Development Server                       ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Check if log file exists, if not create it
if (-not (Test-Path $logFilePath)) {
    Write-Host "📝 Creating ayush.md log file..." -ForegroundColor Yellow
    $header = @"
# Ayush - Healing Backend Logs

This file tracks all remediation options executed and their outcomes.

---

"@
    Set-Content -Path $logFilePath -Value $header -Encoding UTF8
    Write-Host "✓ Log file created at: $logFilePath" -ForegroundColor Green
}
Write-Host ""

Write-Host "📦 Starting Next.js development server..." -ForegroundColor Cyan
Write-Host ""

# Navigate to h24-app and start dev server
Push-Location $h24AppRoot
try {
    # Start the dev server
    npm run dev
}
finally {
    Pop-Location
}
