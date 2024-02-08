from httpx import Client, Response

from utils import retry


class Request:
    def __init__(self) -> None:
        self.client = Client(headers={"user-agent": "Mozilla/5.0"})

    @retry
    def get(self, url: str) -> Response:
        res = self.client.get(url)
        return res.raise_for_status()
