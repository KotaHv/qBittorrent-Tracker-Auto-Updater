import os
from typing import Any

# Settings' qb_* fields are required; provide values so the module-level
# `settings = Settings()` singleton can be created at import time.
os.environ.setdefault("QB_HOST", "http://localhost:8080")
os.environ.setdefault("QB_USERNAME", "admin")
os.environ.setdefault("QB_PASSWORD", "adminadmin")

import pytest
from pydantic import AnyHttpUrl, SecretStr

from config import DEFAULT_SOURCES, Settings
from exception import InvalidSettingsError


def make_settings(**kwargs: Any) -> Settings:
    """Build Settings with the required qb_* credentials filled in."""
    return Settings(
        qb_host=AnyHttpUrl("http://localhost:8080"),
        qb_username="admin",
        qb_password=SecretStr("adminadmin"),
        **kwargs,
    )


@pytest.fixture(autouse=True)
def _no_local_dotenv(monkeypatch, tmp_path):
    """Run from an empty directory so a developer's local .env can't interfere."""
    monkeypatch.chdir(tmp_path)


def test_qb_host_is_required(monkeypatch):
    for var in ("QB_HOST", "QB_USERNAME", "QB_PASSWORD"):
        monkeypatch.delenv(var, raising=False)

    with pytest.raises(InvalidSettingsError) as exc_info:
        Settings()  # type: ignore[reportCallIssue]

    message = str(exc_info.value)
    assert "qb_host" in message
    assert "qb_username" not in message
    assert "qb_password" not in message


def test_qb_credentials_are_optional(monkeypatch):
    monkeypatch.setenv("QB_USERNAME", "")
    monkeypatch.setenv("QB_PASSWORD", "")

    settings = Settings(qb_host=AnyHttpUrl("http://localhost:8080"))

    assert settings.qb_username == ""
    assert settings.qb_password.get_secret_value() == ""


def test_empty_qb_host_is_required(monkeypatch):
    monkeypatch.setenv("QB_HOST", "")

    with pytest.raises(InvalidSettingsError, match="qb_host"):
        Settings()  # type: ignore[reportCallIssue]


def test_invalid_setting_is_translated_too():
    with pytest.raises(InvalidSettingsError, match="proxy"):
        make_settings(proxy="not a url")


def test_qb_settings_load_from_env(monkeypatch):
    monkeypatch.setenv("QB_HOST", "http://127.0.0.1:8080")
    monkeypatch.setenv("QB_USERNAME", "user")
    monkeypatch.setenv("QB_PASSWORD", "pass")
    settings = Settings()  # type: ignore[reportCallIssue]

    assert settings.qb_host.unicode_string() == "http://127.0.0.1:8080/"
    assert settings.qb_username == "user"
    assert settings.qb_password.get_secret_value() == "pass"


def test_qb_host_accepts_scheme_less_hosts(monkeypatch):
    monkeypatch.setenv("QB_HOST", "192.168.1.1")
    settings = Settings()  # type: ignore[reportCallIssue]
    assert settings.qb_host.unicode_string() == "http://192.168.1.1/"

    monkeypatch.setenv("QB_HOST", "localhost:8080")
    settings = Settings()  # type: ignore[reportCallIssue]
    assert settings.qb_host.unicode_string() == "http://localhost:8080/"


def test_default_sources_when_nothing_set():
    settings = make_settings()

    assert settings.tracker_sources == DEFAULT_SOURCES
    assert settings.trackers_url == []
    assert settings.uses_deprecated_trackers_url is False


def test_tracker_sources_from_env_literal_newlines(monkeypatch):
    monkeypatch.setenv(
        "TRACKER_SOURCES",
        "https://a.example.com/list\\nhttps://b.example.com/list",
    )
    settings = make_settings()

    assert settings.tracker_sources == [
        "https://a.example.com/list",
        "https://b.example.com/list",
    ]
    assert settings.uses_deprecated_trackers_url is False


def test_tracker_sources_from_env_real_newlines(monkeypatch):
    monkeypatch.setenv(
        "TRACKER_SOURCES",
        "https://a.example.com/list\nhttps://b.example.com/list",
    )
    settings = make_settings()

    assert settings.tracker_sources == [
        "https://a.example.com/list",
        "https://b.example.com/list",
    ]


def test_deprecated_trackers_url_env_migrates(monkeypatch):
    monkeypatch.setenv("TRACKERS_URL", "https://old.example.com/list")
    settings = make_settings()

    assert settings.uses_deprecated_trackers_url is True
    assert settings.trackers_url == ["https://old.example.com/list"]
    assert settings.tracker_sources == ["https://old.example.com/list"]


def test_deprecated_trackers_url_init_kwarg_migrates():
    settings = make_settings(trackers_url=["https://old.example.com/list"])

    assert settings.uses_deprecated_trackers_url is True
    assert settings.tracker_sources == ["https://old.example.com/list"]


def test_tracker_sources_wins_over_deprecated(monkeypatch):
    monkeypatch.setenv("TRACKER_SOURCES", "https://new.example.com/list")
    monkeypatch.setenv("TRACKERS_URL", "https://old.example.com/list")
    settings = make_settings()

    assert settings.uses_deprecated_trackers_url is True
    assert settings.tracker_sources == ["https://new.example.com/list"]


def test_tracker_sources_init_kwarg_wins_over_deprecated():
    settings = make_settings(
        tracker_sources=["https://new.example.com/list"],
        trackers_url=["https://old.example.com/list"],
    )

    assert settings.tracker_sources == ["https://new.example.com/list"]
