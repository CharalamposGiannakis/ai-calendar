$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$BackendPath = Join-Path $ProjectRoot "backend"
$PythonPath = Join-Path $BackendPath ".venv\Scripts\python.exe"
$AlembicConfig = Join-Path $BackendPath "alembic.ini"
$DatabasePath = Join-Path $ProjectRoot "storage\db\ai_calendar.db"

if (-not (Test-Path $PythonPath)) {
    Write-Error "Python virtual environment not found at $PythonPath"
    exit 1
}

if (-not (Test-Path $DatabasePath)) {
    Write-Error "Development database not found at $DatabasePath"
    exit 1
}

$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$BackupPath = Join-Path (Split-Path -Parent $DatabasePath) "ai_calendar_${Timestamp}_before_alembic_adoption.db"
Copy-Item -LiteralPath $DatabasePath -Destination $BackupPath -ErrorAction Stop
Write-Host "Created backup: $BackupPath"

$ValidationScript = @"
import sqlite3
import sys
from pathlib import Path

db_path = Path(r'''$DatabasePath''')

expected_columns = {
    "categories": {
        "id",
        "name",
        "color",
        "description",
        "created_at",
        "updated_at",
    },
    "events": {
        "id",
        "title",
        "description",
        "start_datetime",
        "end_datetime",
        "all_day",
        "location",
        "category_id",
        "source_type",
        "status",
        "created_at",
        "updated_at",
    },
}

required_not_null = {
    "categories": {"name", "created_at", "updated_at"},
    "events": {
        "title",
        "start_datetime",
        "end_datetime",
        "all_day",
        "source_type",
        "status",
        "created_at",
        "updated_at",
    },
}

expected_indexes = {
    "categories": {
        "ix_categories_id": False,
        "ix_categories_name": True,
    },
    "events": {
        "ix_events_id": False,
        "ix_events_start_datetime": False,
        "ix_events_end_datetime": False,
    },
}

errors = []

with sqlite3.connect(db_path) as connection:
    table_names = {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }

    if "alembic_version" in table_names:
        errors.append("alembic_version already exists; this database appears to be adopted.")

    for table_name, columns in expected_columns.items():
        if table_name not in table_names:
            errors.append(f"missing expected table: {table_name}")
            continue

        table_info = {
            row[1]: {"type": row[2], "notnull": bool(row[3]), "pk": bool(row[5])}
            for row in connection.execute(f"PRAGMA table_info({table_name})")
        }

        missing_columns = columns - set(table_info)
        if missing_columns:
            errors.append(
                f"{table_name} missing columns: {', '.join(sorted(missing_columns))}"
            )

        for column_name in required_not_null[table_name]:
            if column_name in table_info and not table_info[column_name]["notnull"]:
                errors.append(f"{table_name}.{column_name} should be NOT NULL")

        if "id" in table_info and not table_info["id"]["pk"]:
            errors.append(f"{table_name}.id should be the primary key")

        index_info = {
            row[1]: bool(row[2])
            for row in connection.execute(f"PRAGMA index_list({table_name})")
        }
        for index_name, should_be_unique in expected_indexes[table_name].items():
            if index_name not in index_info:
                errors.append(f"{table_name} missing index: {index_name}")
            elif index_info[index_name] != should_be_unique:
                errors.append(
                    f"{table_name}.{index_name} unique flag mismatch"
                )

    if "events" in table_names:
        foreign_keys = [
            {
                "table": row[2],
                "from": row[3],
                "to": row[4],
                "on_delete": row[6],
            }
            for row in connection.execute("PRAGMA foreign_key_list(events)")
        ]
        if not any(
            item["table"] == "categories"
            and item["from"] == "category_id"
            and item["to"] == "id"
            and item["on_delete"].upper() == "SET NULL"
            for item in foreign_keys
        ):
            errors.append("events.category_id foreign key to categories.id with ON DELETE SET NULL is missing")

if errors:
    print("Database schema validation failed:")
    for error in errors:
        print(f"- {error}")
    sys.exit(1)

print("Database schema validation passed.")
"@

$ValidationScript | & $PythonPath -
if ($LASTEXITCODE -ne 0) {
    Write-Error "Adoption aborted. The database was not stamped. Backup remains at $BackupPath"
    exit $LASTEXITCODE
}

Set-Location $ProjectRoot
& $PythonPath -m alembic -c $AlembicConfig stamp head
if ($LASTEXITCODE -ne 0) {
    Write-Error "Alembic stamp failed. Backup remains at $BackupPath"
    exit $LASTEXITCODE
}

Write-Host "Database adopted successfully. Backup remains at $BackupPath"
