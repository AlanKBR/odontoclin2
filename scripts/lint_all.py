"""Lint orchestration script.

Runs auto-fix capable tools first, then static analyzers, aggregates
unfixed issues into a concise machine-friendly summary printed to stdout.
Exit code 0 if all clean or only auto-fixed changes were needed,
1 if remaining issues.

Tools used (installed on demand if missing):
- black (format)
- isort (imports)
- autoflake (remove unused imports/vars)
- flake8 (style/errors)
- pylint (broader analysis) [summary only]
- mypy (type checking, errors only excerpt)

The script favors minimal noise: prints sections only when there are
remaining problems after auto-fixes. Designed so an AI agent can parse:
Markers: >>>SECTION:<NAME> and >>>ENDSECTION

"""

from __future__ import annotations

import importlib
import importlib.util
import subprocess
import sys
from pathlib import Path
from typing import List

REPO_ROOT = Path(__file__).resolve().parent.parent
PY_SRC_GLOBS = ["app", "tests", "config.py", "run.py", "inspect_tables.py"]

AUTO_TOOLS = [
    (
        "autoflake",
        [
            "autoflake",
            "--in-place",
            "--remove-all-unused-imports",
            "--remove-unused-variables",
            "--recursive",
        ],
    ),
    ("isort", ["isort"]),
    ("black", ["black"]),
]

CHECK_TOOLS = [
    ("flake8", ["flake8", "--max-line-length=100"]),
]

OPTIONAL_TOOLS = [
    # Only report error-level messages from pylint
    # to avoid failing on warnings/duplicates
    (
        "pylint",
        [
            "pylint",
            "--output-format=text",
            "--score=n",
            "--disable=all",
            "--enable=E",
        ],
    ),
    ("mypy", ["mypy", "--ignore-missing-imports", "--no-color-output"]),
]

REQUIRED_PACKAGES = ["black", "isort", "autoflake", "flake8"]
OPTIONAL_PACKAGES = ["pylint", "mypy", "types-python-dateutil"]


def ensure_packages(pkgs: List[str]) -> None:
    to_install = []
    for p in pkgs:
        try:
            importlib.import_module(p.split("[")[0])
        except Exception:  # pragma: no cover - dynamic env
            to_install.append(p)
    if to_install:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", *to_install],
            check=False,
        )


def build_target_list() -> List[str]:
    targets: List[str] = []
    for g in PY_SRC_GLOBS:
        p = REPO_ROOT / g
        if p.is_dir():
            targets.append(str(p))
        elif p.exists():
            targets.append(str(p))
    return targets


def run(cmd: List[str], capture: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd + build_target_list(),
        capture_output=capture,
        text=True,
    )


def run_autofixers() -> None:
    for name, base in AUTO_TOOLS:
        proc = run(base)
        if proc.returncode not in (0, 1):  # some tools use 1 for changes
            print(f"[warn] {name} exited with {proc.returncode}")


def collect_issues() -> dict:
    results: dict[str, str] = {}
    # flake8
    for name, base in CHECK_TOOLS:
        proc = run(base)
        if proc.stdout.strip():
            results[name] = proc.stdout.strip()
    # optional
    for name, base in OPTIONAL_TOOLS:
        if importlib.util.find_spec(name) is None:
            continue
        proc = run(base)
        # Only include mypy output if it reported errors (non-zero exit)
        if name == "mypy" and proc.returncode == 0:
            continue
        out = (proc.stdout or "") + (proc.stderr or "")
        if out.strip():
            # truncate very long output to last 200 lines
            lines = out.strip().splitlines()[-200:]
            results[name] = "\n".join(lines)
    return results


def main() -> int:
    ensure_packages(REQUIRED_PACKAGES)
    ensure_packages(OPTIONAL_PACKAGES)  # best effort
    run_autofixers()
    issues = collect_issues()
    if not issues:
        print("CLEAN")
        return 0
    for section, text in issues.items():
        print(f">>>SECTION:{section.upper()}")
        print(text)
        print(f">>>ENDSECTION:{section.upper()}")
    return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
