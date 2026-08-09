class RetryError(Exception):
    pass


class SourceFetchError(Exception):
    """Raised when a strict fetch of all sources fails."""


class StateSaveError(Exception):
    """Raised when persisting the state file fails."""
