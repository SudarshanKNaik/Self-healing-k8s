param(
    [int]$AppPort = 5000,
    [int]$NgrokPort = 5000
)

$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $repoRoot

function Get-PythonCommand {
    $venvPython = Join-Path $repoRoot '.venv\Scripts\python.exe'
    if (Test-Path $venvPython) {
        return $venvPython
    }

    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCmd) {
        return $pythonCmd.Source
    }

    return 'py'
}

function Wait-ForHttpEndpoint {
    param(
        [string]$Url,
        [int]$TimeoutSeconds = 30
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2 | Out-Null
            return $true
        }
        catch {
            Start-Sleep -Seconds 1
        }
    }

    return $false
}

$pythonExe = Get-PythonCommand

if (Wait-ForHttpEndpoint -Url "http://127.0.0.1:$AppPort/health" -TimeoutSeconds 2) {
    Write-Host "Flask app already responding on port $AppPort."
}
else {
    Write-Host "Starting Flask app on port $AppPort..."
    $appProcess = Start-Process -FilePath $pythonExe -ArgumentList 'app.py' -WorkingDirectory $repoRoot -PassThru

    if (-not (Wait-ForHttpEndpoint -Url "http://127.0.0.1:$AppPort/health" -TimeoutSeconds 30)) {
        throw 'Flask app did not become healthy in time.'
    }
}

$tunnelUrl = $null
if (Wait-ForHttpEndpoint -Url 'http://127.0.0.1:4040/api/tunnels' -TimeoutSeconds 2) {
    try {
        $tunnels = Invoke-RestMethod -Uri 'http://127.0.0.1:4040/api/tunnels' -Method Get -TimeoutSec 5
        $tunnelUrl = $tunnels.tunnels | Select-Object -First 1 -ExpandProperty public_url
    }
    catch {
        $tunnelUrl = $null
    }
}

if (-not $tunnelUrl) {
    Write-Host "Starting ngrok tunnel on port $NgrokPort..."
    $ngrokProcess = Start-Process -FilePath 'ngrok' -ArgumentList @('http', $NgrokPort) -WorkingDirectory $repoRoot -PassThru

    if (Wait-ForHttpEndpoint -Url 'http://127.0.0.1:4040/api/tunnels' -TimeoutSeconds 30) {
        try {
            $tunnels = Invoke-RestMethod -Uri 'http://127.0.0.1:4040/api/tunnels' -Method Get -TimeoutSec 5
            $tunnelUrl = $tunnels.tunnels | Select-Object -First 1 -ExpandProperty public_url
        }
        catch {
            $tunnelUrl = $null
        }
    }
}

Write-Host ''
Write-Host 'Running endpoints:'
Write-Host "Local health: http://127.0.0.1:$AppPort/health"
Write-Host "Local data:   http://127.0.0.1:$AppPort/pods"

if ($tunnelUrl) {
    Write-Host "Ngrok health: $tunnelUrl/health"
    Write-Host "Ngrok data:   $tunnelUrl/pods"
}
else {
    Write-Host 'Ngrok tunnel started, but the public URL could not be read yet.'
    Write-Host 'Open http://127.0.0.1:4040 to inspect the tunnel URL.'
}

Write-Host ''
Write-Host 'Press Ctrl+C in each terminal to stop the app and ngrok.'