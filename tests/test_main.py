import os

# main.py loads the settings singleton at import time, and qb_* are required.
os.environ.setdefault("QB_HOST", "http://localhost:8080")
os.environ.setdefault("QB_USERNAME", "admin")
os.environ.setdefault("QB_PASSWORD", "adminadmin")

import pytest

import main as main_module
from exception import (
    QBConnectionError,
    QBInvalidHostError,
    QBLoginFailedError,
)


class _StopWaiting(Exception):
    """Break main()'s indefinite wait-for-intervention loop on the first sleep."""


def patch_sleep_to_stop_wait(monkeypatch) -> None:
    def stop_waiting(_seconds):
        raise _StopWaiting

    monkeypatch.setattr(main_module, "sleep", stop_waiting)


def test_login_failed_logs_guidance_and_waits_instead_of_exiting(
    monkeypatch, capsys
):
    class FakeQB:
        def __init__(self, **kwargs) -> None:
            raise QBLoginFailedError("boom")

    monkeypatch.setattr(main_module, "qBittorrent", FakeQB)
    patch_sleep_to_stop_wait(monkeypatch)

    with pytest.raises(_StopWaiting):
        main_module.main()

    stderr = capsys.readouterr().err
    assert "qBittorrent error" in stderr
    assert "will not retry" in stderr
    assert "docker compose restart" in stderr


def test_invalid_host_logs_guidance_and_waits_instead_of_exiting(
    monkeypatch, capsys
):
    class FakeQB:
        def __init__(self, **kwargs) -> None:
            raise QBInvalidHostError("boom")

    monkeypatch.setattr(main_module, "qBittorrent", FakeQB)
    patch_sleep_to_stop_wait(monkeypatch)

    with pytest.raises(_StopWaiting):
        main_module.main()

    stderr = capsys.readouterr().err
    assert "will not retry" in stderr


def test_connection_error_logs_guidance_and_waits_instead_of_exiting(
    monkeypatch, capsys
):
    class FakeQB:
        def __init__(self, **kwargs) -> None:
            raise QBConnectionError("boom")

    monkeypatch.setattr(main_module, "qBittorrent", FakeQB)
    patch_sleep_to_stop_wait(monkeypatch)

    with pytest.raises(_StopWaiting):
        main_module.main()

    stderr = capsys.readouterr().err
    assert "qBittorrent error" in stderr
    assert "will not retry" in stderr
