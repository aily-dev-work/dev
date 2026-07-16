"""Run due posts once (wrapper)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.cli import cmd_run_once


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--real", action="store_true")
    args = parser.parse_args()
    return cmd_run_once(args)


if __name__ == "__main__":
    raise SystemExit(main())
