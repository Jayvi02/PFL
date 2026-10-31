@echo off
REM One-time setup for the auto-updating launcher.
REM Needs Git (https://git-scm.com/download/win) and uv (https://docs.astral.sh/uv/).
REM Downloads the app to %LOCALAPPDATA%\UPFLoans\app and puts a shortcut on the desktop.
setlocal
set "APPDIR=%LOCALAPPDATA%\UPFLoans\app"

where git >nul 2>nul || (echo Git is not installed. Get it from https://git-scm.com/download/win & pause & exit /b 1)
where uv >nul 2>nul || (echo uv is not installed. See https://docs.astral.sh/uv/getting-started/installation/ & pause & exit /b 1)

if exist "%APPDIR%\.git" (
    echo App folder already exists, updating it.
    git -C "%APPDIR%" pull --ff-only || (pause & exit /b 1)
) else (
    git clone -b main https://github.com/Jayvi02/PFL.git "%APPDIR%" || (pause & exit /b 1)
)

pushd "%APPDIR%"
uv venv -p 3.12 .venv || (pause & exit /b 1)
uv pip install -p .venv -e . || (pause & exit /b 1)
popd

powershell -NoProfile -Command "$s = (New-Object -ComObject WScript.Shell).CreateShortcut([Environment]::GetFolderPath('Desktop') + '\UPF Loan Manager.lnk'); $s.TargetPath = '%APPDIR%\packaging\launch_latest.bat'; $s.WorkingDirectory = '%APPDIR%'; $s.WindowStyle = 7; $s.Save()"

echo.
echo Done. Use the "UPF Loan Manager" shortcut on your desktop.
pause
