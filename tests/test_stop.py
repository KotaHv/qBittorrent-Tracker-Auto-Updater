import threading
import time

import pytest

from exception import StopRequested
from stop import handle_signal, stop_event, wait_interruptibly


def test_handle_signal_sets_event_then_raises_on_second_signal():
    handle_signal(None, None)
    assert stop_event.is_set()

    with pytest.raises(StopRequested):
        handle_signal(None, None)


def test_wait_interruptibly_returns_immediately_when_stop_requested():
    stop_event.set()

    wait_interruptibly(60)


def test_wait_interruptibly_wakes_when_stop_requested_during_wait():
    def set_later():
        time.sleep(0.05)
        stop_event.set()

    thread = threading.Thread(target=set_later)
    thread.start()
    started = time.monotonic()

    wait_interruptibly(60)

    elapsed = time.monotonic() - started
    thread.join()

    assert elapsed < 1
