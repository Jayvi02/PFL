@echo off
REM Gets the latest version from GitHub (when online), then starts the app.
REM Works offline too: it just starts the version already on this PC.
cd /d "%~dp0.."
git pull --ff-only --quiet >nul 2>nul
uv pip install -p .venv -e . --quiet >nul 2>nul
start "" ".venv\Scripts\pythonw.exe" -m upf_loans
