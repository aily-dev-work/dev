"""Verify OAuth tokens without posting."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.cli import cmd_verify_auth  # noqa: E402
from argparse import Namespace  # noqa: E402


def main() -> int:
    return cmd_verify_auth(Namespace())


if __name__ == "__main__":
    raise SystemExit(main())
