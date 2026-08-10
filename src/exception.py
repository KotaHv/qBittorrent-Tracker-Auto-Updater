class AppError(Exception):
    """Base class for all application errors."""


class RetryError(AppError):
    pass


class SourceFetchError(AppError):
    """Raised when a strict fetch of all sources fails."""


class StateSaveError(AppError):
    """Raised when persisting the state file fails."""


class InvalidSettingsError(AppError):
    """Raised when settings fail validation; the underlying pydantic
    ValidationError is never exposed to users."""


class QBitTorrentError(AppError):
    """Base class for fatal errors while talking to qBittorrent."""


class QBInvalidHostError(QBitTorrentError):
    """Raised when the qBittorrent host URL is malformed."""


class QBLoginFailedError(QBitTorrentError):
    """Raised when qBittorrent rejects the configured credentials."""


class QBConnectionError(QBitTorrentError):
    """Raised for any other non-transient qBittorrent connection failure."""


class StopRequested(BaseException):
    """Control-flow exception: a stop was requested and code must unwind now.

    Raised on a second SIGINT/SIGTERM and by retry/login loops that notice the
    stop flag. Inherits BaseException so broad ``except Exception`` handlers
    cannot swallow it.
    """
