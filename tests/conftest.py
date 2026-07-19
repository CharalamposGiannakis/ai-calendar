import os
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.db import create_database_engine, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.seed import seed_default_categories  # noqa: E402


def run_migrations(database_url):
    previous_database_url = os.environ.get("AI_CALENDAR_DATABASE_URL")
    os.environ["AI_CALENDAR_DATABASE_URL"] = database_url

    alembic_config = Config(str(BACKEND_DIR / "alembic.ini"))
    alembic_config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))

    try:
        command.upgrade(alembic_config, "head")
    finally:
        if previous_database_url is None:
            os.environ.pop("AI_CALENDAR_DATABASE_URL", None)
        else:
            os.environ["AI_CALENDAR_DATABASE_URL"] = previous_database_url


@pytest.fixture
def test_engine(tmp_path):
    database_path = tmp_path / "test_ai_calendar.db"
    database_url = f"sqlite:///{database_path.as_posix()}"
    run_migrations(database_url)

    database_engine = create_database_engine(database_url)
    try:
        yield database_engine
    finally:
        database_engine.dispose()


@pytest.fixture
def client(test_engine):
    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=test_engine,
    )

    seed_db = TestingSessionLocal()
    try:
        seed_default_categories(seed_db)
    finally:
        seed_db.close()

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    # Do not enter app lifespan here; it uses the normal application SessionLocal.
    test_client = TestClient(app)
    try:
        yield test_client
    finally:
        test_client.close()
        app.dependency_overrides.clear()
