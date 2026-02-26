from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Backward-compatible wrapper for ingestion prompt release.")
    parser.add_argument("--source-template", default="ingestion.jinja")
    parser.add_argument("--owner", default="mle-team")
    parser.add_argument("--changelog", required=True)
    parser.add_argument("--schema-version", default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    script = Path(__file__).resolve().parent / "release_prompt.py"
    cmd = [
        sys.executable,
        str(script),
        "--prompt-id",
        "ingestion",
        "--source-template",
        args.source_template,
        "--owner",
        args.owner,
        "--changelog",
        args.changelog,
    ]
    if args.schema_version:
        cmd.extend(["--schema-version", args.schema_version])
    if args.dry_run:
        cmd.append("--dry-run")
    raise SystemExit(subprocess.call(cmd))


if __name__ == "__main__":
    main()
