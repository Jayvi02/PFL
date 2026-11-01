"""In-app updates from the GitHub "latest" release.

The GitHub build stamps the commit it was built from into ``_build.BUILD_SHA``.
An update is available when the release was built from a different commit.
Installing downloads the zip, unpacks it next to the data folder, and hands over
to a small batch script that waits for the app to close, copies the new files
over the program folder and starts the app again. The database lives in the
data folder, not the program folder, so it is never touched.
"""

from __future__ import annotations

import json
import re
import os
import shutil
import sys
import urllib.error
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .. import _build, config
from .errors import ServiceError

REPO = "Jayvi02/PFL"
RELEASE_API = f"https://api.github.com/repos/{REPO}/releases/tags/latest"
ASSET_NAME = "UPFLoanManager-windows.zip"
EXE_NAME = "UPFLoanManager.exe"


@dataclass(frozen=True)
class UpdateInfo:
    available: bool
    current: str
    latest: str
    published_at: str
    asset_url: str
    size: int
    latest_version: str = ""


def current_build() -> str:
    return _build.BUILD_SHA


def current_version() -> str:
    """Version shown to the user: 1.0.<GitHub run number>, or "1.0 (dev)" when run from source."""
    number = getattr(_build, "BUILD_NUMBER", 0)
    return f"{config.APP_VERSION}.{number}" if number else f"{config.APP_VERSION} (dev)"


def build_date() -> str:
    return getattr(_build, "BUILD_DATE", "")


def is_installed_build() -> bool:
    """True when running the packaged exe (updates can only replace a packaged build)."""
    return bool(getattr(sys, "frozen", False))


def _request(url: str, token: str, accept: str) -> urllib.request.Request:
    headers = {"Accept": accept, "User-Agent": "UPFLoanManager", "X-GitHub-Api-Version": "2022-11-28"}
    if token.strip():
        headers["Authorization"] = f"Bearer {token.strip()}"
    return urllib.request.Request(url, headers=headers)


def _explain(exc: Exception, token: str) -> ServiceError:
    if isinstance(exc, urllib.error.HTTPError):
        if exc.code in (401, 403):
            return ServiceError("GitHub refused the request. Try again later.")
        if exc.code == 404:
            return ServiceError("No update found on GitHub. The repository may still be private.")
        return ServiceError(f"GitHub returned an error ({exc.code}).")
    return ServiceError("Could not reach GitHub. Check the internet connection and try again.")


def check(token: str = "", timeout: float = 10) -> UpdateInfo:
    try:
        with urllib.request.urlopen(_request(RELEASE_API, token, "application/vnd.github+json"), timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, ValueError) as exc:
        raise _explain(exc, token) from exc
    asset = next((a for a in data.get("assets", []) if a.get("name") == ASSET_NAME), None)
    if asset is None:
        raise ServiceError("The latest release has no Windows download yet.")
    latest = str(data.get("target_commitish", ""))
    current = current_build()
    return UpdateInfo(
        available=bool(latest) and latest != current,
        current=current,
        latest=latest,
        published_at=str(data.get("published_at", "")),
        asset_url=str(asset["url"]),
        size=int(asset.get("size") or 0),
        latest_version=_version_from_title(str(data.get("name") or "")),
    )


def _version_from_title(title: str) -> str:
    match = re.search(r"\d+\.\d+\.\d+", title)
    return match.group(0) if match else ""


def download(info: UpdateInfo, token: str = "", progress: Callable[[int, int], None] | None = None,
             target_dir: Path | None = None) -> Path:
    target_dir = target_dir or (config.home_dir() / "update")
    if target_dir.exists():
        shutil.rmtree(target_dir, ignore_errors=True)
    target_dir.mkdir(parents=True)
    zip_path = target_dir / ASSET_NAME
    try:
        req = _request(info.asset_url, token, "application/octet-stream")
        with urllib.request.urlopen(req, timeout=60) as r, open(zip_path, "wb") as out:
            total = int(r.headers.get("Content-Length") or info.size or 0)
            done = 0
            while chunk := r.read(256 * 1024):
                out.write(chunk)
                done += len(chunk)
                if progress:
                    progress(done, total)
    except (urllib.error.URLError, OSError) as exc:
        raise _explain(exc, token) from exc
    return zip_path


def unpack(zip_path: Path) -> Path:
    """Extract the zip and return the folder that contains UPFLoanManager.exe."""
    dest = zip_path.parent / "new"
    try:
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(dest)
    except zipfile.BadZipFile as exc:
        raise ServiceError("The downloaded update is damaged. Try again.") from exc
    for exe in dest.rglob(EXE_NAME):
        return exe.parent
    raise ServiceError("The downloaded update does not contain the program.")


def write_install_script(new_dir: Path, install_dir: Path, pid: int, target_sha: str = "") -> Path:
    """Batch script: wait for this process to exit, copy the new files in, restart.

    Every step is written to install_update.log so a failed update can be explained
    on the next start (see ``check_previous_install``).
    """
    work = new_dir.parent
    script = work / "install_update.bat"
    log = work / "install_update.log"
    failed = work / "FAILED.txt"
    (work / "target.txt").write_text(target_sha, encoding="ascii")
    exe = install_dir / EXE_NAME
    lines = [
        "@echo off",
        "setlocal",
        f'set "LOG={log}"',
        'echo [%date% %time%] installer started > "%LOG%"',
        "set /a tries=0",
        ":wait",
        f'tasklist /FI "PID eq {pid}" /NH 2>nul | find " {pid} " >nul',
        "if errorlevel 1 goto closed",
        "set /a tries+=1",
        "if %tries% GEQ 120 goto closed",
        # ping works without a console window, unlike timeout
        "ping -n 2 127.0.0.1 >nul",
        "goto wait",
        ":closed",
        'echo [%date% %time%] app closed, copying files >> "%LOG%"',
        f'robocopy "{new_dir}" "{install_dir}" /E /IS /IT /R:20 /W:1 /NP /NFL /NDL >> "%LOG%" 2>&1',
        "set RC=%errorlevel%",
        'echo [%date% %time%] robocopy exit code %RC% >> "%LOG%"',
        "if %RC% GEQ 8 (",
        f'  echo The update could not replace the program files in {install_dir}. > "{failed}"',
        ")",
        # a fresh PyInstaller environment for the restarted program
        "set PYINSTALLER_RESET_ENVIRONMENT=1",
        "set _MEIPASS2=",
        "set _PYI_APPLICATION_HOME_DIR=",
        "set _PYI_ARCHIVE_FILE=",
        "set _PYI_PARENT_PROCESS_LEVEL=",
        "set _PYI_SPLASH_IPC=",
        f'cd /d "{install_dir}"',
        f'start "" "{exe}"',
        'echo [%date% %time%] restarted the app >> "%LOG%"',
        "endlocal",
    ]
    script.write_text("\r\n".join(lines) + "\r\n", encoding="mbcs" if sys.platform == "win32" else "utf-8",
                      errors="replace")
    return script


def launch_install(script: Path) -> None:
    """Start the install script in its own hidden console, outside this app's process tree."""
    import subprocess

    env = {k: v for k, v in os.environ.items() if not k.startswith(("_PYI_", "_MEIPASS"))}
    env["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
    kwargs = dict(cwd=str(script.parent), env=env, close_fds=True,
                  stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if sys.platform != "win32":
        subprocess.Popen(["sh", "-c", f'echo "{script}"'], **kwargs)
        return
    info = subprocess.STARTUPINFO()
    info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    info.wShowWindow = 0  # SW_HIDE
    base = subprocess.CREATE_NEW_CONSOLE | subprocess.CREATE_NEW_PROCESS_GROUP
    cmd = [os.environ.get("COMSPEC", "cmd.exe"), "/c", str(script)]
    try:
        subprocess.Popen(cmd, creationflags=base | subprocess.CREATE_BREAKAWAY_FROM_JOB, startupinfo=info, **kwargs)
    except OSError:
        # the app's job doesn't allow breakaway; start it normally
        subprocess.Popen(cmd, creationflags=base, startupinfo=info, **kwargs)


def check_previous_install() -> str | None:
    """After an update attempt, return a message if it did not take effect; clean up either way."""
    work = config.home_dir() / "update"
    target_file = work / "target.txt"
    if not target_file.exists():
        return None
    target = target_file.read_text(errors="replace").strip()
    log_file = work / "install_update.log"
    log = log_file.read_text(errors="replace").strip() if log_file.exists() else ""
    message = None
    if target and target != current_build():
        message = "The last update did not install; this is still the old version."
        if not log:
            message += (" The installer never started, so something on this computer (often antivirus) stopped it. "
                        "You can update by hand: download the zip again and replace the program folder.")
        else:
            message += "\n\nInstaller log:\n" + "\n".join(log.splitlines()[-12:])
    shutil.rmtree(work, ignore_errors=True)
    return message


def install_dir() -> Path:
    return Path(sys.executable).resolve().parent


def can_write(folder: Path) -> bool:
    probe = folder / ".upf_write_test"
    try:
        probe.write_text("x")
        probe.unlink()
        return True
    except OSError:
        return False


def last_failure() -> str | None:
    failed = config.home_dir() / "update" / "FAILED.txt"
    if failed.exists():
        text = failed.read_text(errors="replace").strip()
        try:
            failed.unlink()
        except OSError:
            pass
        return text
    return None


def pid() -> int:
    return os.getpid()
