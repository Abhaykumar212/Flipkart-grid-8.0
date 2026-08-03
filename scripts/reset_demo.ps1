$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
$python = if (Test-Path -LiteralPath $venvPython) { $venvPython } else { "python" }
$databaseUrl = if ($env:DATABASE_URL) { $env:DATABASE_URL } else { "sqlite:///./data/grid8.db" }
$databasePath = $null
if ($databaseUrl.StartsWith("sqlite:///")) {
    $sqliteTarget = $databaseUrl.Substring("sqlite:///".Length)
    $databasePath = [System.IO.Path]::GetFullPath((Join-Path $projectRoot $sqliteTarget))
    $dataRoot = [System.IO.Path]::GetFullPath((Join-Path $projectRoot "data"))
    if (-not $databasePath.StartsWith($dataRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to reset a SQLite database outside $dataRoot"
    }
}

Push-Location $projectRoot
try {
    $startedAt = Get-Date
    if ($databasePath -and (Test-Path -LiteralPath $databasePath)) {
        Remove-Item -LiteralPath $databasePath -Force
    }
    & $python -m alembic upgrade head
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & $python -m scripts.seed_catalog
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & $python -m scripts.seed_experiment
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & $python -m ml.training.registry promote --model risk --version v1
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & $python -m ml.training.registry promote --model root_cause --version v1
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & $python -m scripts.warm_review_cache
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    $elapsed = ((Get-Date) - $startedAt).TotalSeconds
    Write-Output ("Demo reset complete in {0:N2}s" -f $elapsed)
}
finally {
    Pop-Location
}
