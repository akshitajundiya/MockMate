"""Entry point: python main.py [--role ... --focus ... | interactive]"""

import sys

from src.cli import run

if __name__ == "__main__":
    sys.exit(run())
