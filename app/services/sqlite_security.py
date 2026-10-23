"""Best-effort local SQLite file permission hardening.

This restricts access by other OS users. It does NOT encrypt the database,
protect against a compromised process, or secure copies and backups.
"""
from __future__ import annotations

import os
import stat
from pathlib import Path


def secure_sqlite_path(path: str | Path) -> Path:
    """Create a private database file and reject symbolic-link destinations."""
    db = Path(path)
    if db.is_symlink():
        raise RuntimeError("Refusing SQLite database symlink")
    db.parent.mkdir(parents=True, exist_ok=True)
    if os.name != "posix":
        return db

    if db.exists():
        if not db.is_file():
            raise RuntimeError("SQLite destination must be a regular file")
        os.chmod(db, 0o600)
    else:
        flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        fd = os.open(db, flags, 0o600)
        os.close(fd)

    os.chmod(db, 0o600)
    return db


def secure_sqlite_sidecars(path: str | Path) -> None:
    """Harden SQLite WAL and shared-memory files if they exist."""
    if os.name != "posix":
        return
    db = Path(path)
    for suffix in ("-wal", "-shm", "-journal"):
        sidecar = Path(str(db) + suffix)
        if sidecar.is_symlink():
            raise RuntimeError("Refusing SQLite sidecar symlink")
        if sidecar.exists() and sidecar.is_file():
            os.chmod(sidecar, 0o600)


def is_private_file(path: str | Path) -> bool:
    if os.name != "posix":
        return False
    file = Path(path)
    return file.is_file() and not file.is_symlink() and stat.S_IMODE(file.stat().st_mode) == 0o600
