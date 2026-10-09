import sqlite3

import pytest

from hld_navigator.backup import snapshot, validate
from hld_navigator.store import Store


def test_snapshot_restores_identity_and_history_without_rotating_tokens(tmp_path):
    source = tmp_path / "source.db"
    token = Store(str(source)).provision("reviewer", "pilot", "reviewer")
    backup = tmp_path / "backup.db"
    metadata = snapshot(source, backup)
    restored = tmp_path / "restored.db"
    snapshot(backup, restored)
    assert metadata["schema_version"] == 3
    assert len(metadata["sha256"]) == 64
    assert Store(str(restored)).principal(token, "pilot")["role"] == "reviewer"
    with sqlite3.connect(restored) as db:
        assert db.execute("SELECT count(*) FROM audit").fetchone()[0] == 1
    with pytest.raises(FileExistsError):
        snapshot(source, source)
    with pytest.raises(FileExistsError):
        snapshot(source, restored)
    assert Store(str(source)).principal(token, "pilot") is not None


def test_snapshot_preserves_committed_wal_data(tmp_path):
    source = tmp_path / "wal.db"
    with sqlite3.connect(source) as writer:
        writer.execute("PRAGMA journal_mode=WAL")
        writer.execute("CREATE TABLE facts(value TEXT)")
        writer.execute("INSERT INTO facts VALUES('committed')")
        writer.commit()
        destination = tmp_path / "copy.db"
        snapshot(source, destination)
        with sqlite3.connect(destination) as reader:
            assert reader.execute("SELECT value FROM facts").fetchone()[0] == "committed"


def test_missing_or_corrupt_database_cannot_be_restored(tmp_path):
    with pytest.raises(ValueError, match="does not exist"):
        snapshot(tmp_path / "missing.db", tmp_path / "destination.db")
    corrupt = tmp_path / "corrupt.db"
    corrupt.write_bytes(b"not a database")
    with pytest.raises(sqlite3.DatabaseError):
        validate(corrupt)
    destination = tmp_path / "destination.db"
    with pytest.raises(sqlite3.DatabaseError):
        snapshot(corrupt, destination)
    assert not destination.exists()
