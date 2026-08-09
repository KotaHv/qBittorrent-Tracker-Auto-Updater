import signal
import sys
from time import monotonic, sleep

from loguru import logger

from config import settings
from exception import RetryError, SourceFetchError, StateSaveError
from log import setup_logger
from qbittorrent import qBittorrent
from request import Request
from storage import TrackerStateStore
from tracker import Tracker
from version import get_version

APP_NAME = "qBittorrent Tracker Auto Updater"


def banner(title: str, version: str) -> str:
    text = f"Starting {title} v{version}"
    width = len(text) + 8
    border = "═" * width
    blank = " " * width
    padding = " " * 4
    return "\n".join(
        (
            f"╔{border}╗",
            f"║{blank}║",
            f"║{padding}{text}{padding}║",
            f"║{blank}║",
            f"╚{border}╝",
        )
    )


setup_logger()
banner_text = banner(APP_NAME, get_version())
if sys.stderr.isatty():
    banner_text = f"\033[36m{banner_text}\033[0m"
print(banner_text, file=sys.stderr)
logger.info("Tracker sources:")
for url in settings.trackers_url:
    logger.info(f"  - {url}")
logger.debug(settings)


def main():
    qb = qBittorrent(
        host=settings.qb_host,
        username=settings.qb_username,
        password=settings.qb_password.get_secret_value(),
    )
    req = Request(proxy=settings.proxy.unicode_string() if settings.proxy else None)
    store = TrackerStateStore(settings.state_file)
    tracker = Tracker(
        qb=qb,
        req=req,
        store=store,
        trackers=settings.trackers,
        trackers_url=settings.trackers_url,
    )
    stopping = False

    def handle_signal(_signum, _frame):
        nonlocal stopping
        if stopping:
            raise KeyboardInterrupt
        stopping = True

    def wait_for_next_cycle() -> None:
        deadline = monotonic() + settings.interval
        while not stopping:
            remaining = deadline - monotonic()
            if remaining <= 0:
                break
            sleep(min(remaining, 0.5))

    # Handle both Ctrl-C and Docker stop (SIGTERM): finish the current
    # cycle, then exit at the next boundary.
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    if not store.load():
        while not stopping:
            try:
                tracker.bootstrap()
                break
            except (RetryError, SourceFetchError, StateSaveError) as e:
                logger.warning(f"Bootstrap failed: {e}; will retry next cycle.")
            finally:
                wait_for_next_cycle()

    while not stopping:
        try:
            tracker.run()
        except (RetryError, SourceFetchError, StateSaveError) as e:
            logger.warning(f"Tracker update failed: {e}, will retry next cycle.")
        if not stopping:
            logger.debug(f"Wait {settings.interval} seconds.")
            wait_for_next_cycle()
    logger.info("Received interrupt, shutting down gracefully.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Forced exit.")
