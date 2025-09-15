"""
Deprecated script: backdoor token generator has been removed from the project.

This file is intentionally retained to avoid import errors in old docs/scripts,
but it no longer functions. The simplified approach now uses a configurable
MASTER_PASSWORD for technician troubleshooting during development. See README.
"""

import sys


def main() -> None:
    print(
        "This script is deprecated and non-functional. The token-based login was removed. "
        "Use the MASTER_PASSWORD mechanism documented in README.md."
    )
    sys.exit(1)


if __name__ == "__main__":
    main()
