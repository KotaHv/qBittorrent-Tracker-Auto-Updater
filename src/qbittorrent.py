import time
from collections.abc import Iterable

import qbittorrentapi
from loguru import logger
from qbittorrentapi.exceptions import APIConnectionError, LoginFailed
from requests.exceptions import ConnectionError, InvalidURL

from exception import QBConnectionError, QBInvalidHostError, QBLoginFailedError
from utils import retry


class qBittorrent:
    def __init__(self, *, host: str, username: str, password: str) -> None:
        self.client = qbittorrentapi.Client(
            host=host, username=username, password=password
        )
        self.login()
        logger.success("qBittorrent authentication successful.")

    def login(self) -> None:
        """Log in, retrying only transient connection failures.

        Raises:
            QBInvalidHostError: the configured host URL is malformed.
            QBLoginFailedError: qBittorrent rejected the credentials.
            QBConnectionError: any other non-transient failure; the message
                carries the full error so users can diagnose it themselves.
        """
        first_failure = True
        while True:
            try:
                self.client.auth_log_in()
                return
            except LoginFailed as exc:
                raise QBLoginFailedError(
                    "qBittorrent login failed: check QB_USERNAME and QB_PASSWORD "
                    "in your configuration."
                ) from exc
            except APIConnectionError as exc:
                # The library re-raises inside its except block, so implicit
                # exception chaining puts the original requests failure in
                # __context__ (not __cause__).
                cause = exc.__context__
                if isinstance(cause, ConnectionError):
                    message = (
                        f"qBittorrent connection failed: {exc}. "
                        "Retrying in 60 seconds..."
                    )
                    if first_failure:
                        logger.error(message)
                        first_failure = False
                    else:
                        logger.debug(message)
                    time.sleep(60)
                    continue
                if isinstance(cause, InvalidURL):
                    raise QBInvalidHostError(
                        "Invalid qBittorrent host (QB_HOST / qb_host): "
                        f"{exc}. It must be a valid URL such as http://host:8080."
                    ) from exc
                raise QBConnectionError(f"qBittorrent error: {exc}") from exc

    @retry
    def add_trackers_for_downloading(self, trackers: Iterable[str]) -> None:
        for torrent in self.client.torrents.info.downloading():
            logger.debug(f"{torrent.name} add trackers: {trackers}")
            torrent.add_trackers(urls=trackers)

    @retry
    def rm_trackers_for_downloading(self, trackers: Iterable[str]) -> None:
        for torrent in self.client.torrents.info.downloading():
            logger.debug(f"{torrent.name} remove trackers: {trackers}")
            torrent.remove_trackers(urls=trackers)

    @retry
    def add_trackers_for_preferences(self, trackers: Iterable[str]) -> None:
        self.client.app_set_preferences({"add_trackers": "\n".join(trackers)})

    @retry
    def get_trackers(self) -> list[str]:
        preferences = self.client.app_preferences()
        return [t for t in preferences.add_trackers.split("\n") if t]
