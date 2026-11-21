"""Start the optional local interface with python -m sorbflow.web."""

from .server import main

if __name__ == "__main__":
    raise SystemExit(main())
