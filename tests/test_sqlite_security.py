import os
import sqlite3

import pytest

from app.services.sqlite_security import (
    secure_sqlite_path, secure_sqlite_sidecars, is_private_file,
)


@pytest.mark.skipif(os.name != "posix", reason="POSIX permissions only")
def test_sqlite_file_is_private(tmp_path):
    path = tmp_path / "user-data.sqlite3"
    secure_sqlite_path(path)
    assert is_private_file(path)
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE test (value TEXT)")
    assert is_private_file(path)


@pytest.mark.skipif(os.name != "posix", reason="POSIX permissions only")
def test_existing_permissions_are_restricted(tmp_path):
    path = tmp_path / "existing.sqlite3"
    path.write_bytes(b"")
    os.chmod(path, 0o666)
    secure_sqlite_path(path)
    assert is_private_file(path)


def test_symlink_database_is_rejected(tmp_path):
    destination = tmp_path / "target.sqlite3"
    destination.write_bytes(b"")
    link = tmp_path / "link.sqlite3"
    try:
        link.symlink_to(destination)
    except (OSError, NotImplementedError):
        pytest.skip("Symlinks not supported")
    with pytest.raises(RuntimeError, match="symlink"):
        secure_sqlite_path(link)


@pytest.mark.skipif(os.name != "posix", reason="POSIX permissions only")
def test_sidecar_permissions(tmp_path):
    path = tmp_path / "db.sqlite3"
    wal = tmp_path / "db.sqlite3-wal"
    wal.write_bytes(b"")
    os.chmod(wal, 0o666)
    secure_sqlite_sidecars(path)
    assert is_private_file(wal)
