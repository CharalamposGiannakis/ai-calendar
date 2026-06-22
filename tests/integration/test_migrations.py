from datetime import datetime
import os
import sqlite3
import subprocess
import sys

import pytest


REVISION_0001 = "20260619_0001"
REVISION_0002 = "20260623_0002"
REVISION_0003 = "20260623_0003"


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


def database_url(database_path):
    return f"sqlite:///{database_path.as_posix()}"


def table_names(connection):
    return {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }


def column_names(connection, table_name):
    return {row[1] for row in connection.execute(f"PRAGMA table_info({table_name})")}


def index_names(connection, table_name):
    return {row[1] for row in connection.execute(f"PRAGMA index_list({table_name})")}


def insert_legacy_event(connection, *, title, start, end, all_day):
    connection.execute(
        """
        INSERT INTO events (
            title, description, start_datetime, end_datetime, all_day, location,
            category_id, source_type, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            title,
            "Synthetic migration fixture",
            start,
            end,
            all_day,
            "Synthetic room",
            None,
            "manual",
            "active",
        ),
    )


def test_time_semantics_upgrade_converts_synthetic_legacy_rows_and_downgrades(tmp_path):
    database_path = tmp_path / "time_semantics.db"
    url = database_url(database_path)
    assert_success(run_alembic(url, "upgrade", REVISION_0001))

    with sqlite3.connect(database_path) as connection:
        insert_legacy_event(
            connection,
            title="Winter timed",
            start="2026-01-15 09:00:00",
            end="2026-01-15 10:00:00",
            all_day=False,
        )
        insert_legacy_event(
            connection,
            title="Summer timed",
            start="2026-07-15 09:00:00",
            end="2026-07-15 10:00:00",
            all_day=False,
        )
        insert_legacy_event(
            connection,
            title="One-day all-day",
            start="2026-09-03 00:00:00",
            end="2026-09-03 23:59:59",
            all_day=True,
        )
        insert_legacy_event(
            connection,
            title="Multi-day all-day",
            start="2026-09-10 00:00:00",
            end="2026-09-12 23:59:59",
            all_day=True,
        )

    assert_success(run_alembic(url, "upgrade", REVISION_0002))

    with sqlite3.connect(database_path) as connection:
        rows = connection.execute(
            """
            SELECT all_day, start_datetime, end_datetime, start_date, end_date, timezone_name
            FROM events
            ORDER BY id
            """
        ).fetchall()

        assert datetime.fromisoformat(rows[0][1]) == datetime(2026, 1, 15, 8, 0)
        assert datetime.fromisoformat(rows[0][2]) == datetime(2026, 1, 15, 9, 0)
        assert rows[0][5] == "Europe/Amsterdam"
        assert datetime.fromisoformat(rows[1][1]) == datetime(2026, 7, 15, 7, 0)
        assert rows[1][5] == "Europe/Amsterdam"
        assert rows[2] == (1, None, None, "2026-09-03", "2026-09-04", None)
        assert rows[3] == (1, None, None, "2026-09-10", "2026-09-13", None)

        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO events (title, all_day, source_type, status)
                VALUES ('Invalid synthetic event', 0, 'manual', 'active')
                """
            )

    assert_success(run_alembic(url, "downgrade", REVISION_0001))

    with sqlite3.connect(database_path) as connection:
        assert "start_date" not in column_names(connection, "events")
        assert "timezone_name" not in column_names(connection, "events")
        all_day_start, all_day_end = connection.execute(
            "SELECT start_datetime, end_datetime FROM events WHERE all_day = 1 ORDER BY id LIMIT 1"
        ).fetchone()
        assert datetime.fromisoformat(all_day_start) == datetime(2026, 9, 3, 0, 0)
        assert datetime.fromisoformat(all_day_end) == datetime(2026, 9, 3, 23, 59, 59)


def test_import_foundation_schema_constraints_and_downgrade(tmp_path):
    database_path = tmp_path / "import_foundation.db"
    url = database_url(database_path)
    assert_success(run_alembic(url, "upgrade", "head"))

    with sqlite3.connect(database_path) as connection:
        assert {
            "source_documents",
            "import_batches",
            "import_rows",
            "candidate_events",
        }.issubset(table_names(connection))
        assert "candidate_event_id" in column_names(connection, "events")
        assert "ix_source_documents_sha256_checksum" in index_names(
            connection, "source_documents"
        )
        assert "ix_import_batches_source_document_id" in index_names(
            connection, "import_batches"
        )
        assert "ix_import_rows_import_batch_id" in index_names(connection, "import_rows")

        connection.execute(
            """
            INSERT INTO source_documents (
                original_filename, storage_path, file_type, size_bytes, sha256_checksum
            ) VALUES (?, ?, ?, ?, ?)
            """,
            ("synthetic.xlsx", "uploads/synthetic.xlsx", "xlsx", 12, "a" * 64),
        )
        source_document_id = connection.execute(
            "SELECT id FROM source_documents"
        ).fetchone()[0]
        connection.execute(
            "INSERT INTO import_batches (source_document_id) VALUES (?)",
            (source_document_id,),
        )
        import_batch_id = connection.execute("SELECT id FROM import_batches").fetchone()[0]
        connection.execute(
            "INSERT INTO import_rows (import_batch_id, row_index) VALUES (?, ?)",
            (import_batch_id, 0),
        )
        import_row_id = connection.execute("SELECT id FROM import_rows").fetchone()[0]

        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO import_batches (source_document_id, status) VALUES (?, 'bad')",
                (source_document_id,),
            )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO import_batches (source_document_id, total_rows_detected)
                VALUES (?, -1)
                """,
                (source_document_id,),
            )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO candidate_events (
                    import_batch_id, import_row_id, title, all_day, review_status
                ) VALUES (?, ?, 'Invalid candidate', 0, 'pending')
                """,
                (import_batch_id, import_row_id),
            )

        connection.execute(
            """
            INSERT INTO candidate_events (
                import_batch_id, import_row_id, title, all_day, start_date, end_date,
                review_status
            ) VALUES (?, ?, 'Valid candidate', 1, '2026-09-03', '2026-09-04', 'pending')
            """,
            (import_batch_id, import_row_id),
        )
        candidate_event_id = connection.execute("SELECT id FROM candidate_events").fetchone()[0]
        event_values = (
            "Synthetic approved event",
            1,
            "2026-09-03",
            "2026-09-04",
            "manual",
            "active",
            candidate_event_id,
        )
        connection.execute(
            """
            INSERT INTO events (
                title, all_day, start_date, end_date, source_type, status, candidate_event_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            event_values,
        )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO events (
                    title, all_day, start_date, end_date, source_type, status, candidate_event_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                event_values,
            )

        candidate_foreign_keys = connection.execute(
            "PRAGMA foreign_key_list(candidate_events)"
        ).fetchall()
        assert {row[3] for row in candidate_foreign_keys} >= {
            "import_batch_id",
            "import_row_id",
            "category_id",
        }
        event_foreign_keys = connection.execute("PRAGMA foreign_key_list(events)").fetchall()
        assert any(
            row[3] == "candidate_event_id" and row[2] == "candidate_events"
            for row in event_foreign_keys
        )

    assert_success(run_alembic(url, "downgrade", REVISION_0002))

    with sqlite3.connect(database_path) as connection:
        names = table_names(connection)
        assert "source_documents" not in names
        assert "import_batches" not in names
        assert "import_rows" not in names
        assert "candidate_events" not in names
        assert "candidate_event_id" not in column_names(connection, "events")


def test_fresh_upgrade_check_and_downgrade_on_temporary_sqlite(tmp_path):
    database_path = tmp_path / "migration_test.db"
    url = database_url(database_path)

    assert_success(run_alembic(url, "upgrade", "head"))

    with sqlite3.connect(database_path) as connection:
        names = table_names(connection)
        assert {"categories", "events", "alembic_version"}.issubset(names)
        assert {
            "source_documents",
            "import_batches",
            "import_rows",
            "candidate_events",
        }.issubset(names)
        assert "ix_events_start_datetime" in index_names(connection, "events")
        assert "ix_events_end_datetime" in index_names(connection, "events")

    current = run_alembic(url, "current")
    assert_success(current)
    assert REVISION_0003 in current.stdout

    assert_success(run_alembic(url, "check"))
    assert_success(run_alembic(url, "downgrade", "base"))
