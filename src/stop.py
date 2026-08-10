import signal
import threading

from exception import StopRequested

# Process-wide cooperative shutdown flag. The SIGINT/SIGTERM handler sets it;
# long-running loops (login retries, the @retry decorator) check it so a
# signal stops the app promptly instead of leaving Docker to SIGKILL the
# container after its stop grace period.
stop_event = threading.Event()


def handle_signal(_signum, _frame) -> None:
    """First signal: request a graceful stop. Second signal: exit now."""
    if stop_event.is_set():
        raise StopRequested
    stop_event.set()


def register_signal_handlers() -> None:
    """Install the SIGINT/SIGTERM handlers. Must run on the main thread."""
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)


def wait_interruptibly(seconds: float) -> None:
    """Block for up to ``seconds``, returning immediately if a stop is requested.

    Delegates to ``stop_event.wait()``: the signal handler's ``set()`` wakes
    the wait directly, with no polling latency and no reliance on signals
    interrupting ``time.sleep`` (which PEP 475 makes resume instead).
    """
    stop_event.wait(seconds)
