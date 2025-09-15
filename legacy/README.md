# OdontoClin

A dental clinic management system built with Flask. This application helps manage patient records, treatments, appointments, and financial information for dental clinics.

## Features

- Patient management
- Treatment planning and tracking
- User authentication and role-based access
- Financial tracking for treatments

## Development Setup

### Prerequisites
- Python 3.10+
- pip

### Installation

1. Clone the repository
```bash
git clone <repository-url>
cd prototipo
```

2. Install dependencies
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### Run with ngrok (public URL)

Expose your local Flask server securely over the internet using ngrok.

Prerequisites:
- Create a free ngrok account to get an auth token
- Ensure these packages are installed (already listed in requirements.txt): `pyngrok`, `python-dotenv`

Steps (Windows PowerShell):

1. Set your ngrok token (one-time):
```powershell
$env:NGROK_AUTHTOKEN = "SEU_TOKEN_AQUI"
```
2. Optionally set region/host/port in `.env`:
```
NGROK_REGION=us
FLASK_HOST=127.0.0.1
FLASK_PORT=5000
```
3. Start the app with an ngrok tunnel:
```powershell
python run_with_ngrok.py --app app:create_app --port 5000
```
The script prints both Local and Public URLs. Press Ctrl+C to stop; cleanup is automatic.

Reserved domain / edge (optional):
- If you have a reserved domain or edge from ngrok, set it in `.env` or pass via CLI.
```powershell
# Using environment
$env:NGROK_DOMAIN = "cricket-uncommon-lamprey.ngrok-free.app"  # or
$env:NGROK_EDGE_ID = "rd_31Zcf19yrpwhbkgu4JExufvDykH"

# Or via flags
python run_with_ngrok.py --app app:create_app --domain cricket-uncommon-lamprey.ngrok-free.app
# or
python run_with_ngrok.py --app app:create_app --edge rd_31Zcf19yrpwhbkgu4JExufvDykH
```

### Code Quality Tools

This project uses several tools to ensure code quality:

- **Black**: Code formatter
- **isort**: Import sorter
- **flake8**: Style guide enforcer
- **pylint**: Code analysis

#### VS Code Integration

If you're using VS Code, the workspace settings are already configured to:
- Format code on save using Black
- Sort imports using isort
- Show linting errors from flake8 and pylint

#### Manual Linting

You can run the linting tools manually using:

```bash
# On Linux/macOS
python lint.py

# On Windows
python lint.py
```

### Git Pre-commit Hook

A pre-commit hook is set up to run the linting checks before each commit. If the linting fails, the commit will be blocked.

### Linting Configuration

- **Black**: 100 character line length
- **isort**: Black profile compatibility
- **flake8**: 100 character line length, ignoring specific errors
- **pylint**: Customized rules in .pylintrc file
