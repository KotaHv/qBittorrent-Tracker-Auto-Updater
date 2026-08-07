from httpx import Client, Response
from loguru import logger

from utils import retry


class Request:
    def __init__(self, *, proxy: str | None = None) -> None:
        self.client = Client(headers={"user-agent": "Mozilla/5.0"}, proxy=proxy)

    @retry
    def get(self, url: str) -> Response:
        res = self.client.get(url)
        res.raise_for_status()
        logger.trace(f"{url}: {res.status_code}")
        return res
