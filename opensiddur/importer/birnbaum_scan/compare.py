"""Compatibility entrypoint for the shared scan comparison tool."""
from opensiddur.importer.scan.compare import *  # noqa: F403

if __name__ == '__main__':
    raise SystemExit(main())
