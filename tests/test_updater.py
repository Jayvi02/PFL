import io
import json
import zipfile

import pytest

from upf_loans.services import updater
from upf_loans.services.errors import ServiceError


class FakeResponse(io.BytesIO):
    def __init__(self, data: bytes):
        super().__init__(data)
        self.headers = {"Content-Length": str(len(data))}

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def release(sha="abc123", assets=True):
    return json.dumps({
        "target_commitish": sha, "published_at": "2026-11-01T10:00:00Z",
        "assets": [{"name": updater.ASSET_NAME, "url": "https://api.example/asset/1", "size": 10}] if assets else [],
    }).encode()


def test_update_available_when_build_differs(monkeypatch):
    monkeypatch.setattr(updater._build, "BUILD_SHA", "old111")
    monkeypatch.setattr(updater.urllib.request, "urlopen", lambda req, timeout: FakeResponse(release("new222")))
    info = updater.check()
    assert info.available and info.latest == "new222" and info.current == "old111"


def test_no_update_when_same_build(monkeypatch):
    monkeypatch.setattr(updater._build, "BUILD_SHA", "same")
    monkeypatch.setattr(updater.urllib.request, "urlopen", lambda req, timeout: FakeResponse(release("same")))
    assert not updater.check().available


def test_missing_asset_and_offline(monkeypatch):
    monkeypatch.setattr(updater.urllib.request, "urlopen", lambda req, timeout: FakeResponse(release(assets=False)))
    with pytest.raises(ServiceError, match="no Windows download"):
        updater.check()

    def offline(req, timeout):
        raise updater.urllib.error.URLError("no network")
    monkeypatch.setattr(updater.urllib.request, "urlopen", offline)
    with pytest.raises(ServiceError, match="Could not reach GitHub"):
        updater.check()


def test_download_unpack_and_script(monkeypatch, tmp_path):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("UPFLoanManager/UPFLoanManager.exe", b"exe")
        zf.writestr("UPFLoanManager/_internal/x.dll", b"dll")
    data = buf.getvalue()
    monkeypatch.setattr(updater.urllib.request, "urlopen", lambda req, timeout: FakeResponse(data))
    info = updater.UpdateInfo(True, "a", "b", "", "https://api.example/asset/1", len(data))
    seen = []
    zip_path = updater.download(info, progress=lambda d, t: seen.append((d, t)), target_dir=tmp_path / "update")
    assert seen[-1] == (len(data), len(data))
    new_dir = updater.unpack(zip_path)
    assert (new_dir / "UPFLoanManager.exe").exists()
    script = updater.write_install_script(new_dir, tmp_path / "app", 4242, "newsha")
    text = script.read_text()
    assert "PID eq 4242" in text and "robocopy" in text and "/E " in text and "/MIR" not in text
    assert "timeout" not in text and "ping -n 2" in text  # timeout needs a console window
    assert "PYINSTALLER_RESET_ENVIRONMENT=1" in text and "install_update.log" in text
    assert (new_dir.parent / "target.txt").read_text() == "newsha"
    assert str(tmp_path / "app" / "UPFLoanManager.exe") in text


def test_version_number_follows_the_build(monkeypatch):
    monkeypatch.setattr(updater._build, "BUILD_NUMBER", 0)
    assert updater.current_version().endswith("(dev)")
    monkeypatch.setattr(updater._build, "BUILD_NUMBER", 42)
    assert updater.current_version() == f"{updater.config.APP_VERSION}.42"


def test_latest_version_read_from_release_title(monkeypatch):
    data = json.loads(release("new222"))
    data["name"] = "UPF Loan Manager 1.0.57"
    monkeypatch.setattr(updater.urllib.request, "urlopen", lambda req, timeout: FakeResponse(json.dumps(data).encode()))
    assert updater.check().latest_version == "1.0.57"


def test_previous_install_reported_and_cleaned(monkeypatch, tmp_path):
    monkeypatch.setenv("UPF_LOANS_HOME", str(tmp_path))
    work = tmp_path / "update"
    work.mkdir()
    (work / "target.txt").write_text("newsha")
    (work / "install_update.log").write_text("installer started\nrobocopy exit code 16")
    monkeypatch.setattr(updater._build, "BUILD_SHA", "oldsha")
    msg = updater.check_previous_install()
    assert "did not install" in msg and "exit code 16" in msg
    assert not work.exists()
    assert updater.check_previous_install() is None

    work.mkdir()
    (work / "target.txt").write_text("oldsha")  # update worked: running the target build
    assert updater.check_previous_install() is None and not work.exists()
