$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
$python = if (Test-Path -LiteralPath $venvPython) { $venvPython } else { "python" }

function Get-FreeTcpPort {
    $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, 0)
    try {
        $listener.Start()
        return ([System.Net.IPEndPoint]$listener.LocalEndpoint).Port
    }
    finally {
        $listener.Stop()
    }
}

Push-Location $projectRoot
try {
    $requiredArtifacts = @(
        "ml/artifacts/model.joblib",
        "ml/artifacts/explainer.joblib",
        "ml/artifacts/risk/v1/model.joblib",
        "ml/artifacts/risk/v1/explainer.joblib",
        "ml/artifacts/root_cause/v1/model.joblib",
        "ml/artifacts/root_cause/v1/explainers.joblib"
    )
    $missingArtifacts = @($requiredArtifacts | Where-Object { -not (Test-Path -LiteralPath $_) })
    if ($missingArtifacts.Count -gt 0) {
        Write-Output "Model artifacts are missing; training the reproducible full-scale demo models."
        & (Join-Path $PSScriptRoot "train_all.ps1") -Scale full
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }
    & $python -m pytest -q
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & $python -m ruff check backend ml scripts tests
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & npm run lint
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & npx tsc -b --noEmit
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & npm run build
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & npx vitest run
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    $previousCi = $env:CI
    $previousBackendPort = $env:E2E_BACKEND_PORT
    $previousFrontendPort = $env:E2E_FRONTEND_PORT
    $previousApiBase = $env:E2E_API_BASE
    try {
        $env:CI = "1"
        if (-not $env:E2E_BACKEND_PORT) { $env:E2E_BACKEND_PORT = [string](Get-FreeTcpPort) }
        if (-not $env:E2E_FRONTEND_PORT) {
            do { $env:E2E_FRONTEND_PORT = [string](Get-FreeTcpPort) }
            while ($env:E2E_FRONTEND_PORT -eq $env:E2E_BACKEND_PORT)
        }
        if (-not $env:E2E_API_BASE) { $env:E2E_API_BASE = "http://localhost:$($env:E2E_BACKEND_PORT)" }
        & npx playwright test
        $playwrightExitCode = $LASTEXITCODE
    }
    finally {
        $env:CI = $previousCi
        $env:E2E_BACKEND_PORT = $previousBackendPort
        $env:E2E_FRONTEND_PORT = $previousFrontendPort
        $env:E2E_API_BASE = $previousApiBase
    }
    exit $playwrightExitCode
}
finally {
    Pop-Location
}
