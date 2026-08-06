"""Entry point: python main.py [--role ... --focus ... | interactive]"""

import sys

from src.cli import run

if __name__ == "__main__":
    # Windows consoles default to cp1252, which turns the em-dashes and ellipses
    # in the UI into replacement characters. Force UTF-8 where supported.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, OSError):
            pass

    sys.exit(run())
