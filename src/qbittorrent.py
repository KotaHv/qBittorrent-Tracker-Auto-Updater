import time
from collections.abc import Iterable

import qbittorrentapi
from loguru import logger
from qbittorrentapi.exceptions import APIConnectionError

from utils import retry


class qBittorrent:
    def __init__(self, *, host: str, username: str, password: str) -> None:
        self.client = qbittorrentapi.Client(
            host=host, username=username, password=password
        )
        self.login()
        logger.success("qBittorrent authentication successful.")

    def login(self) -> None:
        while True:
            try:
                self.client.auth_log_in()
                return
            except APIConnectionError as e:
                if type(e) is not APIConnectionError:
                    raise
                logger.error(
                    f"qBittorrent connection failed: {e}. Retrying in 60 seconds..."
                )
                time.sleep(60)

    @retry
    def add_trackers_for_downloading(self, trackers: Iterable[str]) -> None:
        for torrent in self.client.torrents.info.downloading():
            logger.debug(f"{torrent.name} add trackers")
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
        return preferences.add_trackers.split("\n")
