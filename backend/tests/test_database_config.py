from app.core.config import Settings


def test_plain_postgresql_url_uses_installed_psycopg_driver() -> None:
    settings = Settings(DATABASE_URL="postgresql://user:password@example.test/db")

    assert settings.sqlalchemy_database_url.startswith("postgresql+psycopg://")


def test_explicit_database_driver_url_is_preserved() -> None:
    settings = Settings(
        DATABASE_URL="postgresql+psycopg://user:password@example.test/db"
    )

    assert settings.sqlalchemy_database_url.startswith("postgresql+psycopg://")


def test_sqlite_database_url_is_preserved() -> None:
    settings = Settings(DATABASE_URL="sqlite:///./.local/test.db")

    assert settings.sqlalchemy_database_url == "sqlite:///./.local/test.db"
