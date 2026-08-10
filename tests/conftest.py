import pytest

from stop import stop_event


@pytest.fixture(autouse=True)
def clear_stop_event():
    """The stop flag is process-global (signal state); reset it around every
    test so a test that sets it cannot leak into the next one."""
    stop_event.clear()
    yield
    stop_event.clear()
