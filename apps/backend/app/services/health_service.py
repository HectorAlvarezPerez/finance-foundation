from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import engine


def get_health_status() -> tuple[bool, str]:
    try:
        if not _database_schema_is_current():
            return False, "database schema is not up to date"
    except (OSError, RuntimeError, SQLAlchemyError, ValueError):
        return False, "database schema check failed"

    return True, "ok"


def _database_schema_is_current() -> bool:
    alembic_config = _load_alembic_config()
    script_directory = ScriptDirectory.from_config(alembic_config)
    expected_heads = set(script_directory.get_heads())

    with engine.connect() as connection:
        result = connection.execute(text("SELECT version_num FROM alembic_version"))
        current_revisions = {row[0] for row in result if row[0]}

    if not current_revisions:
        return False

    return current_revisions == expected_heads


def _load_alembic_config() -> Config:
    app_root = Path(__file__).resolve().parents[2]
    config_path = app_root / "alembic.ini"
    script_location = app_root / "alembic"

    if not config_path.exists():
        raise FileNotFoundError(f"Alembic config not found: {config_path}")

    if not script_location.exists():
        raise FileNotFoundError(f"Alembic script directory not found: {script_location}")

    config = Config(str(config_path))
    config.set_main_option("script_location", str(script_location))
    return config
