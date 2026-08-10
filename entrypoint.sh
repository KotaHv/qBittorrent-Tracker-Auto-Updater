#!/bin/sh

set -e

umask ${UMASK}

groupmod -o -g "${PGID}" nonroot
usermod -o -u "${PUID}" nonroot

chown -R nonroot:nonroot /app

exec su-exec "${PUID}:${PGID}" "$@"
