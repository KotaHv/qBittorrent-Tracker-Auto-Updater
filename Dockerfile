FROM ghcr.io/astral-sh/uv:0.12.1-python3.14-alpine3.23 AS builder

ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

# Omit development dependencies
ENV UV_NO_DEV=1

# Use the system Python from the base image, not a downloaded managed Python
ENV UV_PYTHON_DOWNLOADS=0

WORKDIR /app
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project
COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked

# Use the same Python base as the builder so the venv's interpreter path matches
FROM python:3.14-alpine3.23

RUN apk add --no-cache tzdata

# Setup a non-root user
RUN addgroup -S nonroot \
 && adduser -S -G nonroot nonroot

COPY --from=builder --chown=nonroot:nonroot /app /app

ENV PATH="/app/.venv/bin:$PATH"

# Keeps Python from buffering stdout and stderr to avoid situations where
# the application crashes without emitting any logs due to buffering.
ENV PYTHONUNBUFFERED=1

# Use the non-root user to run our application
USER nonroot

WORKDIR /app

CMD ["python", "src/main.py"]
