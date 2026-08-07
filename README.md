# qbittorrent-tracker-auto-updater

Automatically updates trackers for qBittorrent.

## Configuration

All settings are read from environment variables or a `.env` file:

| Variable       | Default | Description                                        |
| -------------- | ------- | -------------------------------------------------- |
| `interval`     | `3600`  | Update interval in seconds                         |
| `trackers_url` | built-in sources | Newline-separated URLs of tracker lists to fetch |
| `trackers`     | empty   | Newline-separated custom trackers                  |
| `proxy`        | unset   | HTTP/HTTPS proxy used to fetch tracker lists       |
| `qb_host`      | `localhost:8080` | qBittorrent WebUI host                      |
| `qb_username`  | `admin` | qBittorrent username                               |
| `qb_password`  | `adminadmin` | qBittorrent password                         |
| `log_level`    | `INFO`  | Log level                                          |

### Proxy

If fetching tracker lists from the internet requires a proxy, set `proxy`:

```dotenv
proxy=http://127.0.0.1:7890
```

Only `http://` and `https://` proxy URLs are supported. The proxy is used for
tracker list requests only; the connection to the qBittorrent WebUI is not
proxied.
