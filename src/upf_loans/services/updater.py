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


def write_install_script(new_dir: Path, install_dir: Path, pid: int) -> Path:
    """Batch script: wait for this process to exit, copy the new files in, restart."""
    script = new_dir.parent / "install_update.bat"
    log = new_dir.parent / "install_update.log"
    lines = [
        "@echo off",
        "setlocal",
        ":wait",
        f'tasklist /FI "PID eq {pid}" 2>nul | find "{pid}" >nul',
        "if not errorlevel 1 (",
        "  timeout /t 1 /nobreak >nul",
        "  goto wait",
        ")",
        f'robocopy "{new_dir}" "{install_dir}" /E /IS /IT /R:10 /W:1 /NFL /NDL /NJH /NJS > "{log}"',
        "if errorlevel 8 (",
        f'  echo The update could not replace the program files. See {log} > "{new_dir.parent / "FAILED.txt"}"',
        ")",
        f'start "" "{install_dir / EXE_NAME}"',
        "endlocal",
    ]
    script.write_text("\r\n".join(lines) + "\r\n", encoding="ascii", errors="replace")
    return script


def launch_install(script: Path) -> None:
    """Start the install script detached; the caller must then quit the app."""
    import subprocess

    flags = 0
    if sys.platform == "win32":
        flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW
    subprocess.Popen(["cmd", "/c", str(script)], creationflags=flags, close_fds=True, cwd=str(script.parent))


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
