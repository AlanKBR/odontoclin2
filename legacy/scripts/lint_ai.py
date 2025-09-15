import json
import subprocess


def run_linter(cmd, name, fixable=True):
    print(f"\n=== {name} ===")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode == 0:
        print(f"{name}: OK")
    else:
        print(f"{name}: Issues detected.")
        if fixable:
            print("Some issues may have been auto-fixed.")
        print("AI_PARSE_BLOCK_START")
        print(
            json.dumps(
                {
                    "tool": name,
                    "cmd": cmd,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "returncode": result.returncode,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        print("AI_PARSE_BLOCK_END")


# Python
run_linter("black .", "Black (Python formatter)", fixable=True)
run_linter("isort .", "isort (Python import sorter)", fixable=True)
run_linter("ruff check . --fix", "Ruff (Python linter/formatter)", fixable=True)
run_linter("flake8 .", "Flake8 (Python linter)", fixable=False)

# Jinja/HTML
run_linter("djlint app/templates/", "Djlint (Jinja/HTML linter)", fixable=False)

# JavaScript
run_linter("npx eslint app/static/js/**/*.js --fix", "ESLint (JS linter)", fixable=True)

print(
    "\nLinting complete. Review any AI_PARSE_BLOCKs above for issues that require manual attention."
)
