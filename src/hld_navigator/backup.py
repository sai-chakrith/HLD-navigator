"""Local operator snapshots. Restore to a new path; never overwrite a live database."""

import argparse
import hashlib
import json
import sqlite3
from contextlib import closing
from pathlib import Path


def validate(database):
    with closing(sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True)) as db:
        if db.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
            raise ValueError("Database integrity check failed")
        if db.execute("PRAGMA foreign_key_check").fetchone():
            raise ValueError("Database foreign key check failed")
        return db.execute("PRAGMA user_version").fetchone()[0]


def snapshot(source, destination):
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if not source.is_file():
        raise ValueError("Source database does not exist")
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation prevents accidental replacement, including the source itself.
    with destination.open("xb"):
        pass
    try:
        with closing(sqlite3.connect(source.as_uri() + "?mode=ro", uri=True)) as original:
            with closing(sqlite3.connect(destination)) as copied:
                original.backup(copied)
        version = validate(destination)
        with destination.open("rb") as stream:
            sha256 = hashlib.file_digest(stream, "sha256").hexdigest()
        return {"file": str(destination), "sha256": sha256, "schema_version": version}
    except Exception:
        destination.unlink(missing_ok=True)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["backup", "restore"])
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    try:
        if args.operation == "restore":
            validate(args.source)
        result = snapshot(args.source, args.destination)
    except (ValueError, OSError, sqlite3.Error) as error:
        parser.exit(1, f"{error}\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
