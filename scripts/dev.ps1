$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
$python = if (Test-Path -LiteralPath $venvPython) { $venvPython } else { "python" }

Push-Location $projectRoot
try {
    & $python -m alembic upgrade head
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & $python -m scripts.seed_catalog
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    $api = Start-Process -FilePath $python `
        -ArgumentList "-m", "uvicorn", "backend.main:app", "--reload", "--port", "8000" `
        -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru
    try {
        & npm run dev
        exit $LASTEXITCODE
    }
    finally {
        if ($api -and -not $api.HasExited) { Stop-Process -Id $api.Id }
    }
}
finally {
    Pop-Location
}
