import signal
import sys
from time import monotonic, sleep

from loguru import logger

from config import settings
from exception import RetryError
from log import setup_logger
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
    tracker = Tracker(
        host=settings.qb_host,
        password=settings.qb_password.get_secret_value(),
        username=settings.qb_username,
        trackers=settings.trackers,
        trackers_url=settings.trackers_url,
    )
    stopping = False

    def handle_sigint(_signum, _frame):
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

    signal.signal(signal.SIGINT, handle_sigint)

    while not stopping:
        try:
            tracker.run()
        except RetryError:
            logger.warning("Tracker update failed, will retry next cycle.")
        if not stopping:
            logger.debug(f"Wait {settings.interval} seconds.")
            wait_for_next_cycle()
    logger.info("Received interrupt, shutting down gracefully.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Forced exit.")
