<#
.SYNOPSIS
    One-command bring-up for judging: installs what's missing, trains models only if
    artifacts are absent, resets the demo database, frees stale ports, starts the API
    and the storefront/dashboard together, and opens the judge-facing pages.

.PARAMETER NoReset
    Skip the database reset. Use only when you deliberately want to keep whatever
    state a previous run left behind.

.PARAMETER SkipInstall
    Skip the pip/npm dependency check. Use on repeat runs once you know the
    environment is already installed, to start faster.

.PARAMETER NoBrowser
    Do not auto-open browser tabs.

.EXAMPLE
    ./scripts/showcase.ps1
#>
param(
    [switch]$NoReset,
    [switch]$SkipInstall,
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
$backendPort = 8000
$frontendPort = 5173

function Write-Step($msg) {
    Write-Host ""
    Write-Host "==> $msg" -ForegroundColor Cyan
}

function Stop-PortOwner([int]$port) {
    $conns = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    foreach ($c in $conns) {
        Write-Host "  Freeing port $port (stopping PID $($c.OwningProcess))" -ForegroundColor Yellow
        Stop-Process -Id $c.OwningProcess -Force -ErrorAction SilentlyContinue
    }
}

Push-Location $projectRoot
try {
    Write-Step "Checking prerequisites"
    if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
        throw "Node.js 22 is required and was not found on PATH."
    }
    # Ask for npm.cmd specifically: bare "npm" resolves to npm.ps1 first in
    # PowerShell's own command discovery, and cmd.exe cannot execute a .ps1.
    $npmCmd = (Get-Command npm.cmd -ErrorAction SilentlyContinue).Source
    if (-not $npmCmd) { $npmCmd = (Get-Command npm -ErrorAction SilentlyContinue).Source }
    if (-not $npmCmd) { throw "npm was not found on PATH." }

    if (-not (Test-Path -LiteralPath $venvPython)) {
        Write-Host "  No .venv found; creating one."
        python -m venv .venv
    }
    $python = $venvPython

    if (-not $SkipInstall) {
        Write-Step "Installing/verifying Python dependencies"
        & $python -m pip install -q -r requirements-dev.txt
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

        if (-not (Test-Path -LiteralPath (Join-Path $projectRoot "node_modules"))) {
            Write-Step "Installing Node dependencies (first run only)"
            & $npmCmd ci
            if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        }
    }

    if (-not (Test-Path -LiteralPath (Join-Path $projectRoot ".env"))) {
        Write-Step "Creating .env from .env.example"
        Copy-Item (Join-Path $projectRoot ".env.example") (Join-Path $projectRoot ".env")
    }

    $requiredArtifacts = @(
        "ml/artifacts/risk/v1/model.joblib",
        "ml/artifacts/risk/v1/explainer.joblib",
        "ml/artifacts/root_cause/v1/model.joblib",
        "ml/artifacts/root_cause/v1/explainers.joblib"
    )
    $missingArtifacts = @($requiredArtifacts | Where-Object { -not (Test-Path -LiteralPath $_) })
    if ($missingArtifacts.Count -gt 0) {
        Write-Step "Training model artifacts (first run only, a few minutes)"
        & (Join-Path $PSScriptRoot "train_all.ps1") -Scale full
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }

    Write-Step "Freeing ports $backendPort and $frontendPort if a stale run is holding them"
    Stop-PortOwner $backendPort
    Stop-PortOwner $frontendPort

    if (-not $NoReset) {
        Write-Step "Resetting the demo database (catalogue, experiment, promoted models, review cache)"
        & (Join-Path $PSScriptRoot "reset_demo.ps1")
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }

    Write-Step "Starting the API on :$backendPort"
    $api = Start-Process -FilePath $python `
        -ArgumentList "-m", "uvicorn", "backend.main:app", "--port", "$backendPort" `
        -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru

    Write-Step "Starting the storefront/dashboard on :$frontendPort"
    # npm resolves to npm.cmd on Windows, which Start-Process cannot launch
    # directly (it is not a PE executable) -- run it through cmd.exe instead.
    $web = Start-Process -FilePath "$env:ComSpec" `
        -ArgumentList "/c", "`"$npmCmd`"", "run", "dev", "--", "--port", "$frontendPort", "--strictPort" `
        -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru

    try {
        Write-Step "Waiting for the API to report ready"
        # Use 127.0.0.1, not localhost: uvicorn binds IPv4-only here, and on
        # a machine where localhost resolves to ::1 first, Invoke-WebRequest
        # hangs on the unanswered IPv6 attempt well past -TimeoutSec.
        $ready = $false
        for ($i = 0; $i -lt 45; $i++) {
            try {
                $r = Invoke-WebRequest -Uri "http://127.0.0.1:$backendPort/ready" -UseBasicParsing -TimeoutSec 2
                if ($r.StatusCode -eq 200) { $ready = $true; break }
            } catch {}
            Start-Sleep -Seconds 1
        }
        if (-not $ready) {
            Write-Host "  API did not report ready within 45s; it may still be starting. Check http://localhost:$backendPort/ready" -ForegroundColor Yellow
        }

        if (-not $NoBrowser) {
            Start-Sleep -Seconds 2
            Start-Process "http://localhost:$frontendPort/"
            Start-Process "http://localhost:$frontendPort/dashboard/scenarios"
            Start-Process "http://localhost:$backendPort/docs"
        }

        Write-Host ""
        Write-Host "Flipkart GRiD 8.0 demo is live:" -ForegroundColor Green
        Write-Host "  Storefront        http://localhost:$frontendPort/"
        Write-Host "  Live sessions     http://localhost:$frontendPort/dashboard"
        Write-Host "  Scenario theatre  http://localhost:$frontendPort/dashboard/scenarios"
        Write-Host "  Architecture      http://localhost:$frontendPort/dashboard/architecture"
        Write-Host "  Swagger API       http://localhost:$backendPort/docs"
        Write-Host ""
        Write-Host "Press Ctrl+C to stop both servers." -ForegroundColor Cyan
        Wait-Process -Id $api.Id
    }
    finally {
        Write-Step "Stopping servers"
        # npm/vite run as descendants of $web via cmd.exe, so killing $web alone
        # leaves node running; free by port instead, which catches the whole tree.
        Stop-PortOwner $backendPort
        Stop-PortOwner $frontendPort
        foreach ($p in @($api, $web)) {
            if ($p -and -not $p.HasExited) { Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue }
        }
    }
}
finally {
    Pop-Location
}
