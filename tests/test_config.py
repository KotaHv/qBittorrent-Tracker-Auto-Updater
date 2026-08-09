import pytest

from config import DEFAULT_SOURCES, Settings


@pytest.fixture(autouse=True)
def _no_local_dotenv(monkeypatch, tmp_path):
    """Run from an empty directory so a developer's local .env can't interfere."""
    monkeypatch.chdir(tmp_path)


def test_default_sources_when_nothing_set():
    settings = Settings()

    assert settings.tracker_sources == DEFAULT_SOURCES
    assert settings.trackers_url == []
    assert settings.uses_deprecated_trackers_url is False


def test_tracker_sources_from_env_literal_newlines(monkeypatch):
    monkeypatch.setenv(
        "TRACKER_SOURCES",
        "https://a.example.com/list\\nhttps://b.example.com/list",
    )
    settings = Settings()

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
    settings = Settings()

    assert settings.tracker_sources == [
        "https://a.example.com/list",
        "https://b.example.com/list",
    ]


def test_deprecated_trackers_url_env_migrates(monkeypatch):
    monkeypatch.setenv("TRACKERS_URL", "https://old.example.com/list")
    settings = Settings()

    assert settings.uses_deprecated_trackers_url is True
    assert settings.trackers_url == ["https://old.example.com/list"]
    assert settings.tracker_sources == ["https://old.example.com/list"]


def test_deprecated_trackers_url_init_kwarg_migrates():
    settings = Settings(trackers_url=["https://old.example.com/list"])

    assert settings.uses_deprecated_trackers_url is True
    assert settings.tracker_sources == ["https://old.example.com/list"]


def test_tracker_sources_wins_over_deprecated(monkeypatch):
    monkeypatch.setenv("TRACKER_SOURCES", "https://new.example.com/list")
    monkeypatch.setenv("TRACKERS_URL", "https://old.example.com/list")
    settings = Settings()

    assert settings.uses_deprecated_trackers_url is True
    assert settings.tracker_sources == ["https://new.example.com/list"]


def test_tracker_sources_init_kwarg_wins_over_deprecated():
    settings = Settings(
        tracker_sources=["https://new.example.com/list"],
        trackers_url=["https://old.example.com/list"],
    )

    assert settings.tracker_sources == ["https://new.example.com/list"]
