import os

# utils imports `config`, whose module-level settings singleton requires the
# qb_* credentials to be set.
os.environ.setdefault("QB_HOST", "http://localhost:8080")
os.environ.setdefault("QB_USERNAME", "admin")
os.environ.setdefault("QB_PASSWORD", "adminadmin")

import pytest

import utils
from exception import StopRequested
from stop import stop_event
from utils import retry, wait_for_next_cycle


def test_retry_stops_retrying_when_stop_requested(monkeypatch):
    attempts = []

    @retry
    def flaky():
        attempts.append(1)
        raise RuntimeError("boom")

    # A stop during the backoff wait must abort the remaining retries.
    monkeypatch.setattr(
        utils, "wait_interruptibly", lambda _seconds: stop_event.set()
    )

    with pytest.raises(StopRequested):
        flaky()

    assert attempts == [1]


def test_retry_skips_attempt_when_stop_requested_before_call():
    attempts = []

    @retry
    def flaky():
        attempts.append(1)
        raise RuntimeError("boom")

    stop_event.set()

    with pytest.raises(StopRequested):
        flaky()

    assert attempts == []


def test_wait_for_next_cycle_returns_immediately_when_stop_requested():
    stop_event.set()

    wait_for_next_cycle()
