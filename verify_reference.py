from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REFERENCE = ROOT / "reference" / "accepted_v1.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    reference = json.loads(REFERENCE.read_text())
    expected = reference["result_file_sha256"]

    missing: list[str] = []
    mismatched: list[tuple[str, str, str]] = []
    for relative_path, expected_hash in expected.items():
        path = ROOT / relative_path
        if not path.is_file():
            missing.append(relative_path)
            continue
        actual_hash = sha256_file(path)
        if actual_hash != expected_hash:
            mismatched.append((relative_path, expected_hash, actual_hash))

    if missing or mismatched:
        if missing:
            print("Missing accepted reference files:")
            for path in missing:
                print(f"  - {path}")
        if mismatched:
            print("Accepted reference hash mismatches:")
            for path, expected_hash, actual_hash in mismatched:
                print(f"  - {path}\n    expected {expected_hash}\n    actual   {actual_hash}")
        raise SystemExit(1)

    print(f"Accepted V1 reference integrity verified: {len(expected)} files")


if __name__ == "__main__":
    main()
