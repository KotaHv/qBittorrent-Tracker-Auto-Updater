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
    StopRequested,
)
from stop import stop_event


class _StopWaiting(Exception):
    """Break main()'s indefinite wait-for-intervention loop on the first wait."""


def patch_stop_wait_to_raise(monkeypatch) -> None:
    def stop_waiting():
        raise _StopWaiting

    monkeypatch.setattr(stop_event, "wait", stop_waiting)


def test_login_failed_logs_guidance_and_waits_instead_of_exiting(
    monkeypatch, capsys
):
    class FakeQB:
        def __init__(self, **kwargs) -> None:
            raise QBLoginFailedError("boom")

    monkeypatch.setattr(main_module, "qBittorrent", FakeQB)
    patch_stop_wait_to_raise(monkeypatch)

    with pytest.raises(_StopWaiting):
        main_module.main()

    stderr = capsys.readouterr().err
    assert "boom" in stderr
    assert "will not retry" in stderr
    assert "docker compose restart" in stderr


def test_invalid_host_logs_guidance_and_waits_instead_of_exiting(
    monkeypatch, capsys
):
    class FakeQB:
        def __init__(self, **kwargs) -> None:
            raise QBInvalidHostError("boom")

    monkeypatch.setattr(main_module, "qBittorrent", FakeQB)
    patch_stop_wait_to_raise(monkeypatch)

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
    patch_stop_wait_to_raise(monkeypatch)

    with pytest.raises(_StopWaiting):
        main_module.main()

    stderr = capsys.readouterr().err
    assert "boom" in stderr
    assert "will not retry" in stderr


def test_stop_during_login_shuts_down_gracefully(monkeypatch, capsys):
    class FakeQB:
        def __init__(self, **kwargs) -> None:
            raise StopRequested

    monkeypatch.setattr(main_module, "qBittorrent", FakeQB)

    main_module.main()

    stderr = capsys.readouterr().err
    assert "shutting down gracefully" in stderr


def test_stop_during_fatal_wait_shuts_down_gracefully(monkeypatch, capsys):
    class FakeQB:
        def __init__(self, **kwargs) -> None:
            raise QBConnectionError("boom")

    monkeypatch.setattr(main_module, "qBittorrent", FakeQB)
    monkeypatch.setattr(stop_event, "wait", lambda: None)

    main_module.main()

    stderr = capsys.readouterr().err
    assert "will not retry" in stderr
    assert "shutting down gracefully" in stderr


def test_runtime_auth_failure_logs_guidance_and_waits(monkeypatch, capsys):
    class FakeQB:
        def __init__(self, **kwargs) -> None:
            pass

    class FakeStore:
        def load(self) -> bool:
            return True

    class FakeTracker:
        def __init__(self, **kwargs) -> None:
            pass

        def run(self) -> None:
            raise QBLoginFailedError("credentials rejected at runtime")

    monkeypatch.setattr(main_module, "qBittorrent", FakeQB)
    monkeypatch.setattr(main_module, "TrackerStateStore", lambda _path: FakeStore())
    monkeypatch.setattr(main_module, "Tracker", FakeTracker)
    monkeypatch.setattr(stop_event, "wait", lambda: None)

    main_module.main()

    stderr = capsys.readouterr().err
    assert "credentials rejected at runtime" in stderr
    assert "will not retry" in stderr
    assert "shutting down gracefully" in stderr
