"""
check_imports.py

Imports every module under src/ (the same way `python src/main.py` does)
and exits non-zero if any of them fails - catching missing dependencies,
broken relative paths and syntax errors before the game is ever launched.
Importing does not open a window, so no display is needed.

Run from the project root:
    python scripts/check_imports.py
"""

import importlib
import pkgutil
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"


def module_names():
    """Yield the dotted name of every module and package under src/."""
    for info in pkgutil.walk_packages([str(SRC)]):
        yield info.name


def main():
    sys.path.insert(0, str(SRC))
    failures = 0
    for name in sorted(module_names()):
        try:
            importlib.import_module(name)
        except Exception as exc:  # report every failure, not just the first
            failures += 1
            print(f"FAIL  {name}: {type(exc).__name__}: {exc}")
        else:
            print(f"ok    {name}")
    if failures:
        print(f"{failures} module(s) failed to import.")
        sys.exit(1)


if __name__ == "__main__":
    main()
