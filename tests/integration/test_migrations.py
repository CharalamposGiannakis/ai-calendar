import os
import sqlite3
import subprocess
import sys


def run_alembic(database_url, *args):
    env = os.environ.copy()
    env["AI_CALENDAR_DATABASE_URL"] = database_url
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "alembic",
            "-c",
            "backend/alembic.ini",
            *args,
        ],
        cwd=os.getcwd(),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def assert_success(result):
    assert result.returncode == 0, (
        f"stdout:\n{result.stdout}\n\nstderr:\n{result.stderr}"
    )


def table_names(connection):
    return {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }


def index_names(connection, table_name):
    return {row[1] for row in connection.execute(f"PRAGMA index_list({table_name})")}


def test_alembic_upgrade_check_and_downgrade_on_temporary_sqlite(tmp_path):
    database_path = tmp_path / "migration_test.db"
    database_url = f"sqlite:///{database_path.as_posix()}"

    upgrade = run_alembic(database_url, "upgrade", "head")
    assert_success(upgrade)

    with sqlite3.connect(database_path) as connection:
        names = table_names(connection)
        assert "categories" in names
        assert "events" in names
        assert "alembic_version" in names

        category_indexes = index_names(connection, "categories")
        assert "ix_categories_id" in category_indexes
        assert "ix_categories_name" in category_indexes

        event_indexes = index_names(connection, "events")
        assert "ix_events_id" in event_indexes
        assert "ix_events_start_datetime" in event_indexes
        assert "ix_events_end_datetime" in event_indexes

        event_foreign_keys = connection.execute("PRAGMA foreign_key_list(events)").fetchall()
        assert any(
            row[2] == "categories"
            and row[3] == "category_id"
            and row[4] == "id"
            and row[6].upper() == "SET NULL"
            for row in event_foreign_keys
        )

    current = run_alembic(database_url, "current")
    assert_success(current)
    assert "20260619_0001" in current.stdout

    check = run_alembic(database_url, "check")
    assert_success(check)

    downgrade = run_alembic(database_url, "downgrade", "base")
    assert_success(downgrade)
