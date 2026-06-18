$ProjectRoot = Split-Path -Parent $PSScriptRoot
$BackendPath = Join-Path $ProjectRoot "backend"
$ActivateScript = Join-Path $BackendPath ".venv\Scripts\Activate.ps1"
$PythonPath = Join-Path $BackendPath ".venv\Scripts\python.exe"
$AlembicConfig = Join-Path $BackendPath "alembic.ini"
$DatabasePath = Join-Path $ProjectRoot "storage\db\ai_calendar.db"

if (-not (Test-Path $ActivateScript)) {
    Write-Error "Virtual environment not found at $ActivateScript"
    exit 1
}

& $ActivateScript

if (Test-Path $DatabasePath) {
    $AdoptionCheck = @"
import sqlite3
import sys
from pathlib import Path

db_path = Path(r'''$DatabasePath''')
with sqlite3.connect(db_path) as connection:
    table_names = {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }

if "alembic_version" in table_names:
    sys.exit(0)

if {"categories", "events"} & table_names:
    sys.exit(2)

sys.exit(0)
"@

    $AdoptionCheck | & $PythonPath -
    if ($LASTEXITCODE -eq 2) {
        Write-Error "Existing database has application tables but no Alembic version. Run .\scripts\adopt_existing_database.ps1 once before starting the app."
        exit 1
    }
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Could not inspect the existing SQLite database before migration."
        exit 1
    }
}

Set-Location $ProjectRoot
& $PythonPath -m alembic -c $AlembicConfig upgrade head
if ($LASTEXITCODE -ne 0) {
    Write-Error "Database migration failed. Uvicorn was not started."
    exit $LASTEXITCODE
}

Set-Location $BackendPath
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
