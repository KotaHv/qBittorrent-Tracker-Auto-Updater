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
| `qb_host`         | `localhost:8080` | qBittorrent WebUI host                               |
| `qb_username`     | `admin`          | qBittorrent username                                 |
| `qb_password`     | `adminadmin`     | qBittorrent password                                 |
| `log_level`       | `INFO`           | Log level                                            |
| `state_file`      | `data/trackers_state.json` | Path to the JSON state file keeping per-source tracker history |

> `trackers_url` is deprecated and will be removed in a future release; use
> `tracker_sources` instead. The old name still works for backward
> compatibility, but a warning is printed when it is used. If both are set,
> `tracker_sources` wins.

### State file

The program persists per-source tracker history in a JSON file (`state_file`),
which makes partial-source failures safe: a source that fails keeps its last
successful list, so its trackers are never deleted by accident. When no valid
state exists, the program bootstraps: it fetches every source (all must
succeed) and adopts the current qBittorrent `add_trackers` preferences as the
initial diff baseline. The state file is written atomically only after a
successful update.

In Docker, the compose example mounts `./data:/app/data`; with the default
`state_file` (`data/trackers_state.json` relative to the working directory,
i.e. `/app/data/trackers_state.json`), state survives container restarts
without extra configuration. Override `state_file` to use a different path:

```yaml
volumes:
  - ./data:/app/data
```

```dotenv
state_file=/app/data/trackers_state.json
```

The directory must be writable by the container user; with a host bind mount
adjust its permissions if needed (`chmod` the host `./data` directory). Locally,
the `data/` directory is created automatically on the first successful update.

### Proxy

If fetching tracker lists from the internet requires a proxy, set `proxy`:

```dotenv
proxy=http://127.0.0.1:7890
```

Only `http://` and `https://` proxy URLs are supported. The proxy is used for
tracker list requests only; the connection to the qBittorrent WebUI is not
proxied.
