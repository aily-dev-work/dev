"""Add a scheduled post (wrapper)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.cli import cmd_add_post


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--text", required=True)
    parser.add_argument("--scheduled-at", required=True)
    args = parser.parse_args()
    return cmd_add_post(args)


if __name__ == "__main__":
    raise SystemExit(main())
