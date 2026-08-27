from app.database import normalize_database_url


def test_normalizes_legacy_postgres_scheme():
    legacy = "postgres://user:pass@host:5432/dbname"
    assert normalize_database_url(legacy) == "postgresql://user:pass@host:5432/dbname"


def test_leaves_modern_postgresql_scheme_untouched():
    modern = "postgresql://user:pass@host:5432/dbname"
    assert normalize_database_url(modern) == modern


def test_leaves_sqlite_url_untouched():
    sqlite_url = "sqlite:///./indu_twin.db"
    assert normalize_database_url(sqlite_url) == sqlite_url
