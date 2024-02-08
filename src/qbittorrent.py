from typing import Iterable

import qbittorrentapi
from loguru import logger

from utils import retry


class qBittorrent:
    def __init__(self, *, host: str, username: str, password: str) -> None:
        self.client = qbittorrentapi.Client(
            host=host, username=username, password=password
        )

    @retry
    def add_trackers_for_downloading(self, trackers: Iterable[str]):
        for torrent in self.client.torrents.info.downloading():
            logger.debug(torrent.name)
            torrent.add_trackers(urls=trackers)

    @retry
    def add_trackers_for_preferences(self, trackers: Iterable[str]):
        self.client.app_set_preferences({"add_trackers": "\n".join(trackers)})
