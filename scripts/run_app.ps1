$ProjectRoot = Split-Path -Parent $PSScriptRoot
$BackendPath = Join-Path $ProjectRoot "backend"
$ActivateScript = Join-Path $BackendPath ".venv\Scripts\Activate.ps1"

Set-Location $BackendPath

if (-not (Test-Path $ActivateScript)) {
    Write-Error "Virtual environment not found at $ActivateScript"
    exit 1
}

& $ActivateScript

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000