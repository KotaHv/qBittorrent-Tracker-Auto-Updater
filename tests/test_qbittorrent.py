import os
import time

# Importing the qBittorrent wrapper pulls in `config`, whose module-level
# settings singleton requires the qb_* credentials to be set.
os.environ.setdefault("QB_HOST", "http://localhost:8080")
os.environ.setdefault("QB_USERNAME", "admin")
os.environ.setdefault("QB_PASSWORD", "adminadmin")

import pytest
import qbittorrentapi
from qbittorrentapi.exceptions import (
    APIConnectionError,
    LoginFailed,
)
from requests.exceptions import ConnectionError, InvalidURL, RequestException, Timeout

from exception import QBConnectionError, QBInvalidHostError, QBLoginFailedError
from qbittorrent import qBittorrent


def wrapped(exc: RequestException) -> APIConnectionError:
    """Mimic qbittorrentapi: collapse a requests failure into an
    APIConnectionError, preserving the original exception in ``__context__``."""
    try:
        raise exc
    except RequestException:
        try:
            raise APIConnectionError(
                f"Failed to connect to qBittorrent. {type(exc).__name__}: {exc!r}"
            )
        except APIConnectionError as wrapped_exc:
            return wrapped_exc


def client_raising(raise_queue: list[Exception]):
    """A qBittorrent Client stand-in that pops the next failure from the queue."""

    class FakeClient:
        def __init__(self, *, host: str, username: str, password: str) -> None:
            self.host = host
            self.username = username
            self.password = password

        def auth_log_in(self) -> None:
            if raise_queue:
                raise raise_queue.pop(0)

    return FakeClient


def patch_client(monkeypatch, raise_queue: list[Exception]) -> None:
    monkeypatch.setattr(qbittorrentapi, "Client", client_raising(raise_queue))


def test_login_retries_connection_error_then_succeeds(monkeypatch):
    sleeps = []
    monkeypatch.setattr(time, "sleep", sleeps.append)
    patch_client(
        monkeypatch,
        [wrapped(ConnectionError("refused")), wrapped(ConnectionError("refused"))],
    )

    qBittorrent(host="http://localhost:8080", username="u", password="p")

    assert sleeps == [60, 60]


def test_login_invalid_url_is_fatal_and_explains_host():
    """A malformed host fails during request preparation, before any network
    I/O, so the real client raises InvalidURL wrapped in APIConnectionError."""
    with pytest.raises(QBInvalidHostError, match="QB_HOST") as err:
        qBittorrent(host="http://:8080", username="u", password="p")

    assert isinstance(err.value.__cause__, APIConnectionError)
    assert isinstance(err.value.__cause__.__context__, InvalidURL)


def test_login_failed_is_fatal_and_explains_credentials(monkeypatch):
    exc = LoginFailed()
    patch_client(monkeypatch, [exc])

    with pytest.raises(QBLoginFailedError, match="QB_USERNAME") as err:
        qBittorrent(host="http://localhost:8080", username="u", password="p")

    assert err.value.__cause__ is exc


def test_login_other_wrapped_error_is_fatal(monkeypatch):
    exc = wrapped(Timeout("timed out"))
    patch_client(monkeypatch, [exc])

    with pytest.raises(QBConnectionError) as err:
        qBittorrent(host="http://localhost:8080", username="u", password="p")

    assert err.value.__cause__ is exc
