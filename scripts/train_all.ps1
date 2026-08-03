param(
    [ValidateSet("small", "full")]
    [string]$Scale = "full",
    [int]$Seed = 42
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
$python = if (Test-Path -LiteralPath $venvPython) { $venvPython } else { "python" }

Push-Location $projectRoot
try {
    & $python -m ml.generate_dataset
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & $python -m ml.train_model
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & $python -m ml.simulator.generate --scale $Scale --seed $Seed
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & $python -m ml.training.train_risk
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & $python -m ml.training.train_root_cause
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & $python -m ml.training.evaluate --model risk
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & $python -m ml.training.evaluate --model root_cause
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
