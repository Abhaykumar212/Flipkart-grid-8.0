param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidateSet("A", "B", "C", "D", "E", "F", "G", "H")]
    [string]$Scenario,
    [switch]$NoReset
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
$python = if (Test-Path -LiteralPath $venvPython) { $venvPython } else { "python" }

Push-Location $projectRoot
try {
    if (-not $NoReset) {
        & (Join-Path $PSScriptRoot "reset_demo.ps1")
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }
    & $python -m scripts.run_scenario $Scenario.ToUpperInvariant()
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
