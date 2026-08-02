$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
$python = if (Test-Path -LiteralPath $venvPython) { $venvPython } else { "python" }

Push-Location $projectRoot
try {
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
    & npx playwright test
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
