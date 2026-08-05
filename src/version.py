import tomllib
from functools import lru_cache
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


@lru_cache
def get_version() -> str:
    try:
        with (PROJECT_ROOT / "pyproject.toml").open("rb") as f:
            pyproject = tomllib.load(f)
        return str(pyproject["project"]["version"])
    except (OSError, KeyError, tomllib.TOMLDecodeError):
        return "unknown"
