import os
import tempfile
from datetime import datetime
from pathlib import Path

from loguru import logger
from pydantic import ValidationError

from exception import StateSaveError
from model import Sources, TrackerState


class TrackerStateStore:
    """Manages a :class:`TrackerState` and atomically persists it to a JSON file."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.state = TrackerState()

    def load(self) -> bool:
        """Load the state file into ``self.state``; True when a valid file was loaded."""
        try:
            self.state = TrackerState.model_validate_json(
                self.path.read_text(encoding="utf-8")
            )
        except FileNotFoundError:
            logger.info(f"No state file at {self.path}; starting empty.")
            return False
        except ValidationError as e:
            logger.warning(
                f"Invalid state file {self.path}: {e}; backing up and rebuilding."
            )
            self._backup()
            return False
        logger.info(f"Loaded tracker state from {self.path}.")
        return True

    def save(self) -> None:
        """Durably persist ``self.state``: fsync temp file, atomic rename, fsync dir."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = self.state.model_dump_json(indent=2)
        temporary_file = tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=self.path.parent,
            prefix=f".{self.path.name}.",
            delete=False,
        )
        temporary_path = Path(temporary_file.name)
        try:
            with temporary_file:
                temporary_file.write(payload)
                temporary_file.flush()
                os.fsync(temporary_file.fileno())
            os.replace(temporary_path, self.path)
            directory_fd = os.open(self.path.parent, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        except Exception as e:
            temporary_path.unlink(missing_ok=True)
            raise StateSaveError(f"Failed to save state to {self.path}: {e}") from e

    def commit(self, sources: Sources, last_committed: list[str]) -> None:
        """Record a successful commit and persist it atomically."""
        self.state.sources = sources
        self.state.last_committed = last_committed
        self.state.updated_at = datetime.now().astimezone().replace(microsecond=0)
        self.save()

    def _backup(self) -> None:
        backup = self.path.with_name(
            f"{self.path.name}.bak-{datetime.now().strftime('%Y%m%d-%H%M%S-%f')}"
        )
        try:
            os.replace(self.path, backup)
            logger.warning(f"Backed up invalid state file to {backup}.")
        except OSError as e:
            logger.error(f"Failed to back up state file {self.path}: {e}.")
