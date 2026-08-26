import sqlite3

from app.services import backup as backup_module


def test_create_backup_copies_data(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, v TEXT)")
    conn.execute("INSERT INTO t (v) VALUES ('hello')")
    conn.commit()
    conn.close()

    monkeypatch.setattr(backup_module.settings, "database_url", f"sqlite:///{db_path}")

    result = backup_module.create_backup()
    assert result is not None
    assert result.exists()
    assert result.parent.name == "backups"

    check = sqlite3.connect(str(result))
    rows = check.execute("SELECT v FROM t").fetchall()
    check.close()
    assert rows == [("hello",)]


def test_create_backup_returns_none_for_missing_db(tmp_path, monkeypatch):
    monkeypatch.setattr(backup_module.settings, "database_url", f"sqlite:///{tmp_path}/nope.db")
    assert backup_module.create_backup() is None


def test_create_backup_returns_none_for_non_sqlite(monkeypatch):
    monkeypatch.setattr(backup_module.settings, "database_url", "postgresql://x/y")
    assert backup_module.create_backup() is None


def test_prune_old_backups_keeps_only_the_most_recent(tmp_path, monkeypatch):
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    names = [f"indu_twin_2026010{i}_000000.db" for i in range(1, 6)]
    for name in names:
        (backup_dir / name).write_text("x")

    monkeypatch.setattr(backup_module, "BACKUP_RETENTION", 2)
    backup_module._prune_old_backups(backup_dir)

    remaining = sorted(p.name for p in backup_dir.glob("indu_twin_*.db"))
    assert remaining == names[-2:]


def test_sqlite_path_handles_relative_and_absolute_urls(monkeypatch):
    monkeypatch.setattr(backup_module.settings, "database_url", "sqlite:///./indu_twin.db")
    assert backup_module._sqlite_path().name == "indu_twin.db"

    monkeypatch.setattr(backup_module.settings, "database_url", "sqlite:////app/data/x.db")
    resolved = backup_module._sqlite_path()
    assert resolved.name == "x.db"
    assert resolved.parent.name == "data"
