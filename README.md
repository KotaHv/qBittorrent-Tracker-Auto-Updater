# qbittorrent-tracker-auto-updater

Automatically updates trackers for qBittorrent.

## Configuration

All settings are read from environment variables or a `.env` file:

| Variable          | Default          | Description                                          |
| ----------------- | ---------------- | ---------------------------------------------------- |
| `interval`        | `3600`           | Update interval in seconds                           |
| `tracker_sources` | built-in sources | Newline-separated URLs of tracker lists to fetch     |
| `trackers`        | empty            | Newline-separated custom trackers                    |
| `proxy`           | unset            | HTTP/HTTPS proxy used to fetch tracker lists         |
| `qb_host`         | required         | qBittorrent WebUI URL, e.g. `http://host:8080`       |
| `qb_username`     | empty            | qBittorrent username; leave empty if the WebUI whitelists this IP |
| `qb_password`     | empty            | qBittorrent password; leave empty if the WebUI whitelists this IP |
| `qb_api_key`      | empty            | qBittorrent API key (`qbt_...`, WebUI-generated, v5.2.0+); takes precedence over username/password |
| `log_level`       | `INFO`           | Log level                                            |
| `state_file`      | `data/trackers_state.json` | Path to the JSON state file keeping per-source tracker history |
| `PUID`            | `1000`           | UID the container user is remapped to at startup; match it to the host user owning `./data` |
| `PGID`            | `1000`           | GID the container user is remapped to at startup      |
| `UMASK`           | `022`            | File creation mask for the app process                |

> `trackers_url` is deprecated and will be removed in a future release; use
> `tracker_sources` instead. The old name still works for backward
> compatibility, but a warning is printed when it is used. If both are set,
> `tracker_sources` wins.
