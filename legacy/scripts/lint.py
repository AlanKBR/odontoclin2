# -*- coding: utf-8 -*-
"""
Lint and format all Python and JavaScript files in the project.

This script helps maintain code quality by running:
- black: Code formatter for Python
- isort: Import organizer for Python
- ruff: Linter for Python (replaces Flake8 for linting, can also format)
- flake8: Style guide enforcement for Python (can be replaced by Ruff)
- eslint: Linter for JavaScript
- djlint: Linter and formatter for Jinja2 templates
- Checks and configures Jinja2 Enhance VS Code extension.
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

# sys.stdout.reconfigure(encoding='utf-8')  # Disabled for compatibility


def check_tool_installed(tool_name: str) -> bool:
    """
    Check if a command-line tool is installed and accessible.
    For ruff, it prioritizes 'python -m ruff' and then direct PATH execution.
    """
    if tool_name == "ruff":
        # Priority 1: Check if runnable via 'python -m ruff --version'
        try:
            result_module = subprocess.run(
                [sys.executable, "-m", "ruff", "--version"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
                timeout=10,
            )
            if result_module.returncode == 0:
                return True
        except Exception:  # Catches FileNotFoundError, subprocess.TimeoutExpired, etc.
            pass  # If 'python -m ruff' fails, try direct 'ruff'

        # Priority 2: Check if 'ruff' is in PATH and 'ruff --version' works
        if shutil.which(tool_name):  # tool_name is "ruff"
            try:
                is_windows = sys.platform == "win32"
                result_direct = subprocess.run(
                    [tool_name, "--version"],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    check=False,
                    shell=is_windows,
                    timeout=10,
                )
                if result_direct.returncode == 0:
                    return True
            except Exception:
                pass  # Direct execution failed
        return False  # Both methods failed for ruff

    # For 'code' (VS Code CLI) and 'djlint'
    # Presence in PATH is sufficient for these.
    if tool_name in ["code", "djlint"]:
        return shutil.which(tool_name) is not None

    # For 'npm'
    if tool_name == "npm":
        if shutil.which(tool_name) is None:
            return False
        try:
            is_windows = sys.platform == "win32"
            result = subprocess.run(
                [tool_name, "--version"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
                shell=is_windows,
                timeout=20,  # Increased timeout for npm
            )
            return result.returncode == 0
        except Exception:
            return False

    # Default for other tools (e.g., black, isort, flake8)
    # Check if they are in PATH. The actual execution success is handled by run_command.
    if shutil.which(tool_name) is not None:
        return True

    return False  # Tool not found by any method


def run_command(command: list[str], verbose: bool = False) -> bool:
    """
    Run a shell command and print its output.

    Args:
        command: A list of strings representing the command and its arguments
                 (e.g., ["black", "--line-length", "100", "file.py"]).
        verbose: Whether to print all output from the command.

    Returns:
        True if the command executed successfully (exit code 0), False otherwise.
    """
    tool_name = command[0]
    actual_command = command

    if not check_tool_installed(tool_name):
        print(f"[WARN] {tool_name} is not installed. Skipping.")
        if tool_name == "npm":
            print("   To install npm, visit: https://nodejs.org/")
        elif tool_name in ["black", "isort", "flake8", "ruff"]:
            print(f"   To install, run: pip install {tool_name}")
        elif tool_name == "djlint":
            print("   To install, run: pip install djlint")
        return False

    # Don't print every command execution
    if verbose:
        print(f"🚀 Running: {' '.join(actual_command)}")

    try:
        is_windows = sys.platform == "win32"
        shell_for_command = is_windows if tool_name in ["npm", "code"] else False
        project_root = Path(__file__).parent.resolve()

        # Special handling for ruff if it needs `python -m`
        if tool_name == "ruff":
            try:
                # First, try direct execution
                subprocess.run(
                    [tool_name, "--version"],
                    capture_output=True,
                    check=True,
                    encoding="utf-8",
                    errors="replace",  # Added errors="replace"
                    text=True,  # Ensure text=True for encoding/errors
                    timeout=5,
                )
                # If successful, actual_command remains as is
            except (
                FileNotFoundError,
                subprocess.CalledProcessError,
                subprocess.TimeoutExpired,
            ):
                # If direct execution fails, try with `python -m ruff`
                if verbose:
                    print(f"ℹ️ {tool_name} using python -m execution method")
                actual_command = [sys.executable, "-m"] + command

        result = subprocess.run(
            actual_command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",  # Added errors="replace"
            check=False,
            shell=shell_for_command,
            cwd=project_root,
        )

        if result.stdout and verbose:
            print("   --- stdout ---")
            print(result.stdout.strip())
            print("   --- end stdout ---")

        if result.returncode != 0:
            if verbose or result.stderr:
                print(f"❌ {tool_name} failed with errors")
                if result.stderr:
                    print("   --- stderr ---")
                    print(result.stderr.strip())
                    print("   --- end stderr ---")
            return False

        return True
    except FileNotFoundError:
        print(f"❌ Error: Command not found: {tool_name}")
        return False
    except subprocess.SubprocessError as e:
        print(f"❌ Error running {tool_name}: {e}")
        return False


def find_python_files(directory: Path) -> list[str]:
    """
    Find all Python files (ending with .py) in a given directory and its subdirectories.

    Args:
        directory: The Path object representing the directory to search.

    Returns:
        A list of strings, where each string is the absolute path to a Python file.
    """
    return [str(p) for p in directory.rglob("*.py")]


def find_javascript_files(directory: Path) -> list[str]:
    """
    Find all JavaScript files (ending with .js) in a given directory and its subdirectories.

    Args:
        directory: The Path object representing the directory to search.

    Returns:
        A list of strings, where each string is the absolute path to a JavaScript file.
    """
    return [str(p) for p in directory.rglob("*.js")]


def find_jinja2_files(directory: Path) -> list[str]:
    """
    Find all Jinja2 template files (ending with .html) in a given directory and its subdirectories.

    Args:
        directory: The Path object representing the directory to search.

    Returns:
        A list of strings, where each string is the absolute path to a Jinja2 template file.
    """
    return [str(p) for p in directory.rglob("*.html")]


JINJA2_ENHANCE_EXTENSION_ID = "samuelcolvin.jinjahtml"
VSCODE_SETTINGS = {
    "files.associations": {"*.html": "jinja-html"},
    "emmet.includeLanguages": {"jinja-html": "html"},
}


def check_vscode_extension_installed(extension_id: str) -> bool:
    """
    Check if a specific VS Code extension is installed.

    Args:
        extension_id: The ID of the extension (e.g., "samuelcolvin.jinjahtml").

    Returns:
        True if the extension is installed, False otherwise.
    """
    if not check_tool_installed("code"):
        return False  # VS Code CLI not available

    try:
        result = subprocess.run(
            ["code", "--list-extensions"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",  # Added errors="replace"
            check=True,
            shell=sys.platform == "win32",
        )
        installed_extensions = result.stdout.lower().splitlines()
        return extension_id.lower() in installed_extensions
    except Exception:
        return False


def install_vscode_extension(extension_id: str) -> bool:
    """
    Install a VS Code extension using the command line.

    Args:
        extension_id: The ID of the extension to install.

    Returns:
        True if the installation command was attempted successfully (does not guarantee
        the extension installed correctly, but that the command ran), False otherwise.
    """
    if not check_tool_installed("code"):
        return False

    return run_command(["code", "--install-extension", extension_id, "--force"])


def configure_vscode_jinja_settings(project_root: Path) -> bool:
    """
    Ensure .vscode/settings.json has the required Jinja2 Enhance configurations.

    Args:
        project_root: The root directory of the project.

    Returns:
        True if settings are correctly configured or updated, False on error.
    """
    vscode_dir = project_root / ".vscode"
    settings_file = vscode_dir / "settings.json"
    made_changes = False

    try:
        vscode_dir.mkdir(exist_ok=True)  # Create .vscode directory if it doesn't exist

        current_settings: dict = {}
        if settings_file.exists():
            try:
                try:
                    with open(settings_file, "r", encoding="utf-8") as f:
                        content = f.read()
                except UnicodeDecodeError:
                    with open(settings_file, "r", encoding="latin1") as f:
                        content = f.read()
                if content.strip():
                    current_settings = json.loads(content)
                else:
                    print(f"ℹ️ {settings_file} is empty. Will create new settings.")
            except json.JSONDecodeError:
                print(f"⚠️ {settings_file} contains invalid JSON. It will be overwritten.")
                current_settings = {}  # Treat as empty if corrupt
            except Exception:
                current_settings = {}

        # Check and update files.associations
        if not isinstance(current_settings.get("files.associations"), dict):
            current_settings["files.associations"] = {}
        if current_settings["files.associations"].get("*.html") != "jinja-html":
            current_settings["files.associations"]["*.html"] = "jinja-html"
            made_changes = True
            print("   Updated 'files.associations' for Jinja2.")

        # Check and update emmet.includeLanguages
        if not isinstance(current_settings.get("emmet.includeLanguages"), dict):
            current_settings["emmet.includeLanguages"] = {}
        if current_settings["emmet.includeLanguages"].get("jinja-html") != "html":
            current_settings["emmet.includeLanguages"]["jinja-html"] = "html"
            made_changes = True
            print("   Updated 'emmet.includeLanguages' for Jinja2.")

        if made_changes or not settings_file.exists():
            with open(settings_file, "w", encoding="utf-8") as f:
                json.dump(current_settings, f, indent=4)
            print(f"✅ Jinja2 Enhance settings configured in {settings_file}")
        else:
            print(f"✅ Jinja2 Enhance settings already correctly configured in {settings_file}.")
        return True

    except Exception:
        return False


# List of required VS Code extensions for linting/formatting
REQUIRED_VSCODE_EXTENSIONS = [
    "ms-python.black-formatter",  # Black formatter for Python
    "ms-python.flake8",  # Flake8 linter for Python
    "charliermarsh.ruff",  # Ruff linter/formatter for Python
    "monosans.djlint",  # djLint for Jinja2 templates
    "dbaeumer.vscode-eslint",  # ESLint for JavaScript
    "samuelcolvin.jinjahtml",  # Jinja2 Enhance for HTML templates
]


def check_and_install_vscode_extensions():
    """
    Ensure all required VS Code extensions for linting/formatting are installed.
    """
    if not check_tool_installed("code"):
        print("[WARN] VS Code CLI ('code') not found in PATH. Skipping extension checks.")
        return
    for ext in REQUIRED_VSCODE_EXTENSIONS:
        if not check_vscode_extension_installed(ext):
            print(f"[EXT] Installing missing VS Code extension: {ext}")
            install_vscode_extension(ext)
        else:
            print(f"[EXT] VS Code extension already installed: {ext}")


def main() -> int:
    """
    Main function to run linting and formatting tools (Black, isort, Flake8, ESLint, djlint)
    on all Python, JavaScript, and Jinja2 files in the project, excluding specified directories.

    Returns:
        0 if all checks pass, 1 if any issues are found.
    """
    # Add a verbose flag for detailed output
    verbose = "--verbose" in sys.argv

    project_root = Path(__file__).parent.resolve()
    exclude_dirs = ["venv", "env", "__pycache__", "migrations", ".git", "node_modules"]

    # Check and install all required VS Code extensions for linting/formatting
    check_and_install_vscode_extensions()

    # Find and filter files
    python_files = find_python_files(project_root)
    python_files = [f for f in python_files if not any(excl in f for excl in exclude_dirs)]
    js_files = find_javascript_files(project_root)
    js_files = [f for f in js_files if not any(excl in f for excl in exclude_dirs)]
    jinja2_files = find_jinja2_files(project_root)
    jinja2_files = [f for f in jinja2_files if not any(excl in f for excl in exclude_dirs)]

    # Initialize results
    results = {}

    # Print summary of files found
    print(
        f"[DIR] Found {len(python_files)} Python files, {len(js_files)} JavaScript files, and {len(jinja2_files)} Jinja2 files"
    )
    print("Running linters and formatters...")

    # Run Python tools
    if python_files:
        print("\n[PY] Python Code Quality Tools")
        print("----------------------------")

        print("[BLK] Black (formatting):", end=" ")
        results["black"] = run_command(["black", "--line-length", "100", *python_files], verbose)
        print("[OK] Done" if results["black"] else "[ERR] Failed")

        print("[ISO] isort (import sorting):", end=" ")
        isort_cmd = ["isort", "--profile", "black", "--line-length", "100"]
        results["isort"] = run_command(isort_cmd + python_files, verbose)
        print("[OK] Done" if results["isort"] else "[ERR] Failed")

        print("[RUF] Ruff (linting):", end=" ")
        # Ruff can replace Flake8 for linting and also offers formatting
        results["ruff"] = run_command(["ruff", "check", ".", "--fix", *python_files], verbose)
        print("[OK] Done" if results["ruff"] else "[ERR] Failed")

        print("[FLK] Flake8 (linting):", end=" ")
        results["flake8"] = run_command(["flake8", "--max-line-length=100", *python_files], verbose)
        print("[OK] Done" if results["flake8"] else "[ERR] Failed")
    else:
        results.update({"black": True, "isort": True, "ruff": True, "flake8": True})

    # Run JavaScript tools
    if js_files:
        print("\n[JS] JavaScript Code Quality Tools")
        print("-------------------------------")

        npm_installed = check_tool_installed("npm")
        if not npm_installed:
            print("▶️ ESLint: ⚠️ npm not installed, skipping")
            results["eslint"] = False
        else:
            eslint_exists = Path(project_root / "node_modules" / "eslint").exists()
            package_json_exists = Path(project_root / "package.json").exists()
            if not package_json_exists:
                print("[ESL] ESLint: [WARN] package.json not found, skipping")
                results["eslint"] = False
            elif not eslint_exists:
                print("[ESL] ESLint:", end=" ")
                install_success = run_command(["npm", "install"], verbose)
                if not install_success:
                    print("[ERR] Failed to install dependencies")
                    results["eslint"] = False
                else:
                    results["eslint"] = run_command(
                        ["npm", "run", "lint:js", "--", "--quiet"], verbose
                    )
                    print("[OK] Done" if results["eslint"] else "[ERR] Failed")
            else:
                print("[ESL] ESLint:", end=" ")
                results["eslint"] = run_command(["npm", "run", "lint:js", "--", "--quiet"], verbose)
                print("[OK] Done" if results["eslint"] else "[ERR] Failed")
    else:
        results["eslint"] = True  # No JS files, so consider it successful

    # Run Jinja2 tools
    if jinja2_files:
        print("\n[JINJA] Jinja2 Template Tools")
        print("-----------------------")

        print("[DJL] djlint:", end=" ")
        djlint_config_args = []
        if (project_root / "pyproject.toml").exists():
            djlint_config_args = [
                "--configuration",
                str(project_root / "pyproject.toml"),
            ]
        elif (project_root / ".djlintrc").exists():
            djlint_config_args = ["--configuration", str(project_root / ".djlintrc")]

        if check_tool_installed("djlint"):
            djlint_cmd_args = (
                ["djlint", "--profile", "jinja", "--warn", "--check"]
                + djlint_config_args
                + jinja2_files
            )
            djlint_success = run_command(djlint_cmd_args, verbose)

            if not djlint_success:
                print(" Issues found. Attempting auto-fix...")
                reformat_args = (
                    ["djlint", "--profile", "jinja", "--warn", "--reformat"]
                    + djlint_config_args
                    + jinja2_files
                )
                reformat_success = run_command(reformat_args, verbose)

                if reformat_success:
                    djlint_fixed = run_command(djlint_cmd_args, verbose)

                    if djlint_fixed:
                        print("[OK] All issues fixed automatically")
                        results["djlint"] = True
                    else:
                        print("⚠️ Some issues remain after auto-fix")
                        # Handle interactive environment
                        try:
                            # Only show details if requested
                            if input("Show detailed issues? (y/n): ").strip().lower() == "y":
                                result = subprocess.run(
                                    djlint_cmd_args,
                                    capture_output=True,
                                    text=True,
                                    encoding="utf-8",
                                    errors="replace",  # Added errors="replace"
                                )
                                print("\\n--- djlint issues ---")
                                print(result.stdout.strip())
                                if result.stderr and result.stderr.strip():
                                    print(result.stderr.strip())
                                print("--- end djlint issues ---\n")

                            # Allow applying fixes anyway
                            if (
                                input("Apply formatting changes anyway? (y/n): ").strip().lower()
                                == "y"
                            ):
                                print("Applying formatting changes...")
                                forced_reformat = run_command(reformat_args, verbose)
                                if forced_reformat:
                                    print("[OK] Formatting applied (with remaining issues)")
                                    results["djlint"] = True  # Consider it a success
                                else:
                                    print("❌ Failed to apply formatting")
                                    results["djlint"] = False
                            else:
                                print("❓ Manual review required")
                                results["djlint"] = False
                        except EOFError:
                            # Non-interactive mode
                            print("ℹ️ Non-interactive mode: showing issues summary")
                            result = subprocess.run(
                                djlint_cmd_args,
                                capture_output=True,
                                text=True,
                                encoding="utf-8",
                                errors="replace",  # Added errors="replace"
                            )
                            print("\\n--- djlint issues summary ---")
                            print(result.stdout.strip())
                            print("--- end djlint issues summary ---\n")
                            results["djlint"] = False
                else:
                    print("Auto-fix failed")
                    results["djlint"] = False
            else:
                print("[OK] No issues found")
                results["djlint"] = True
        else:
            print("⚠️ Not installed")
            results["djlint"] = False

        # VS Code Extension check for Jinja2
        print("[JINJA2] Jinja2 VS Code Extension:", end=" ")
        code_cli_available = check_tool_installed("code")
        if code_cli_available:
            has_extension = check_vscode_extension_installed(JINJA2_ENHANCE_EXTENSION_ID)
            if not has_extension:
                print("Installing...")
                install_vscode_extension(JINJA2_ENHANCE_EXTENSION_ID)
            configure_vscode_jinja_settings(project_root)
            print("[OK] Configured")
        else:
            print("⚠️ VS Code CLI not found")
            print(f"   Extension ID: {JINJA2_ENHANCE_EXTENSION_ID}")
            print("   Settings needed in .vscode/settings.json:")
            print(json.dumps(VSCODE_SETTINGS, indent=2))
    else:
        results["djlint"] = True  # No Jinja2 files, so consider it successful

    # Print summary
    for tool, success in results.items():
        print(f"{tool:10s}: {'[OK] Passed' if success else '[ERR] Failed'}")

    if not all(results.values()):
        print("\n[WARN] Some checks failed. Fix issues before committing.")
        print("   Run with --verbose for detailed output.")
        return 1

    print("\n[OK] All checks passed!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
