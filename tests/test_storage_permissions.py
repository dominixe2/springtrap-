import os
import stat
from pathlib import Path

import pytest

from micro_helper import api


@pytest.mark.skipif(os.name != "posix", reason="POSIX permission bits are not portable to Windows.")
def test_default_micro_helper_storage_and_sqlite_sidecars_are_private(monkeypatch, tmp_path):
    data_dir = tmp_path / ".micro-helper"
    database_path = data_dir / "micro_helper.sqlite3"
    monkeypatch.setattr(api, "DATABASE_PATH", database_path)

    with api.database():
        assert stat.S_IMODE(data_dir.stat().st_mode) == 0o700
        assert stat.S_IMODE(database_path.stat().st_mode) == 0o600
        for suffix in ("-wal", "-shm", "-journal"):
            sidecar = Path(str(database_path) + suffix)
            if sidecar.exists():
                assert stat.S_IMODE(sidecar.stat().st_mode) == 0o600


@pytest.mark.skipif(os.name != "posix", reason="POSIX permission bits are not portable to Windows.")
def test_custom_database_parent_permissions_are_not_changed(monkeypatch, tmp_path):
    shared_dir = tmp_path / "shared"
    shared_dir.mkdir()
    os.chmod(shared_dir, 0o755)
    database_path = shared_dir / "custom.sqlite3"
    monkeypatch.setattr(api, "DATABASE_PATH", database_path)

    with api.database():
        assert stat.S_IMODE(shared_dir.stat().st_mode) == 0o755
        assert stat.S_IMODE(database_path.stat().st_mode) == 0o600


@pytest.mark.skipif(os.name != "posix", reason="POSIX symbolic-link behavior is not portable to Windows.")
def test_database_refuses_symbolic_link_target(monkeypatch, tmp_path):
    data_dir = tmp_path / ".micro-helper"
    data_dir.mkdir()
    real_database = tmp_path / "outside.sqlite3"
    real_database.write_bytes(b"")
    database_path = data_dir / "micro_helper.sqlite3"
    database_path.symlink_to(real_database)
    monkeypatch.setattr(api, "DATABASE_PATH", database_path)

    with pytest.raises(RuntimeError, match="symbolic-link"):
        with api.database():
            pass


@pytest.mark.skipif(os.name != "posix", reason="POSIX permission bits are not portable to Windows.")
def test_existing_database_file_is_restricted_before_use(monkeypatch, tmp_path):
    data_dir = tmp_path / ".micro-helper"
    data_dir.mkdir()
    database_path = data_dir / "micro_helper.sqlite3"
    database_path.write_bytes(b"")
    os.chmod(database_path, 0o644)
    monkeypatch.setattr(api, "DATABASE_PATH", database_path)

    with api.database():
        assert stat.S_IMODE(database_path.stat().st_mode) == 0o600


@pytest.mark.skipif(os.name != "posix", reason="POSIX special files are not portable to Windows.")
def test_database_refuses_fifo_without_blocking(monkeypatch, tmp_path):
    data_dir = tmp_path / ".micro-helper"
    data_dir.mkdir()
    database_path = data_dir / "micro_helper.sqlite3"
    os.mkfifo(database_path)
    monkeypatch.setattr(api, "DATABASE_PATH", database_path)

    with pytest.raises(RuntimeError, match="non-regular"):
        with api.database():
            pass
