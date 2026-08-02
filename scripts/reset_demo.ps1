$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$databasePath = Join-Path $projectRoot "data\grid8.db"
$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
$python = if (Test-Path -LiteralPath $venvPython) { $venvPython } else { "python" }

Push-Location $projectRoot
try {
    if (Test-Path -LiteralPath $databasePath) {
        Remove-Item -LiteralPath $databasePath -Force
    }
    & $python -m alembic upgrade head
    & $python -m scripts.seed_catalog
    & $python -m scripts.warm_review_cache
}
finally {
    Pop-Location
}

