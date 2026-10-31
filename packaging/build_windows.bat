@echo off
REM Build the Windows app folder dist\UPFLoanManager\UPFLoanManager.exe
REM Requires uv (https://docs.astral.sh/uv/) - run from the repository root.
uv venv -p 3.12 .venv
uv pip install -p .venv -e ".[dev]"
.venv\Scripts\python -m pytest -q || exit /b 1
.venv\Scripts\pyinstaller --noconfirm --clean packaging\upf_loans.spec || exit /b 1
start /wait "" dist\UPFLoanManager\UPFLoanManager.exe --self-test || exit /b 1
echo.
echo Built dist\UPFLoanManager\UPFLoanManager.exe
