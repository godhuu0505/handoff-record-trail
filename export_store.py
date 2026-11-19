"""Create or inspect a single-file Relate snapshot of the fictional demo."""

import argparse
import hashlib
import json
import os
from importlib.metadata import version
from pathlib import Path
from tempfile import TemporaryDirectory

import relate

from trace import DEMO_WRITES, trace


def inspect_store(path):
    if path.suffix != ".rl":
        raise ValueError("Use a .rl single-file store.")
    if not path.is_file():
        raise FileNotFoundError(f"Store is not an existing file: {path}")
    with relate.connect(str(path), read_only=True) as db:
        result = trace(db, "share-01")
        versions = db.execute(
            "MATCH (v:CareVersion) RETURN v.id AS id, v.status AS status ORDER BY id"
        ).data()
    return {
        "engine": f"Relate {version('relate-db')}",
        "format": "single-file .rl",
        "file": str(path),
        "bytes": path.stat().st_size,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "trace": result,
        "versions": versions,
    }


def create_store(path):
    if path.suffix != ".rl":
        raise ValueError("Use a .rl single-file store.")
    if path.exists() or path.is_symlink():
        raise FileExistsError(f"Refusing to overwrite: {path}")
    if not path.parent.is_dir():
        raise FileNotFoundError(f"Output directory does not exist: {path.parent}")
    with TemporaryDirectory(prefix=".relate-snapshot-", dir=path.parent) as directory:
        staged = Path(directory) / "snapshot.rl"
        with relate.connect(str(staged)) as db:
            for statement in DEMO_WRITES[:4]:
                db.execute(statement)
        if not staged.is_file():
            raise RuntimeError("Relate did not create a single-file store.")
        inspect_store(staged)
        # Linking publishes the closed store atomically and refuses an existing path.
        os.link(staged, path)
    return inspect_store(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["create", "inspect"])
    parser.add_argument("path", type=Path, help="Path to a single-file .rl store")
    args = parser.parse_args()
    try:
        result = create_store(args.path) if args.action == "create" else inspect_store(args.path)
    except (OSError, ValueError, relate.Error) as exc:
        parser.exit(2, f"{exc}\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
