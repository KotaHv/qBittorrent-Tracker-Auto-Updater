from pathlib import Path
from typing import Annotated, Any, Literal, Self

from pydantic import AnyHttpUrl, AnyUrl, BeforeValidator, SecretStr, model_validator
from pydantic.fields import FieldInfo
from pydantic_settings import (
    BaseSettings,
    DotEnvSettingsSource,
    EnvSettingsSource,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

DEFAULT_SOURCES = [
    "https://raw.githubusercontent.com/ngosang/trackerslist/master/trackers_best.txt",
    "https://raw.githubusercontent.com/XIU2/TrackersListCollection/master/best.txt",
]


def _normalize_urls(value: Any, url_type: type[AnyUrl]) -> list[str]:
    if isinstance(value, str):
        value = value.splitlines()
    return [url_type(str(url)).unicode_string() for url in value]


def _normalize_tracker_urls(value: Any) -> list[str]:
    return _normalize_urls(value, AnyHttpUrl)


def _normalize_trackers(value: Any) -> list[str]:
    return _normalize_urls(value, AnyUrl)


def _split_tracker_values(field_name: str, value: Any) -> list[str] | None:
    if (
        field_name in {"trackers", "trackers_url", "tracker_sources"}
        and isinstance(value, str)
        and value
    ):
        return value.replace("\\n", "\n").splitlines()
    return None


class MyEnvSettingsSource(EnvSettingsSource):
    def prepare_field_value(
        self, field_name: str, field: FieldInfo, value: Any, value_is_complex: bool
    ) -> Any:
        split = _split_tracker_values(field_name, value)
        if split is not None:
            return split
        return super().prepare_field_value(field_name, field, value, value_is_complex)


class MyDotEnvSettingsSource(DotEnvSettingsSource):
    def prepare_field_value(
        self, field_name: str, field: FieldInfo, value: Any, value_is_complex: bool
    ) -> Any:
        split = _split_tracker_values(field_name, value)
        if split is not None:
            return split
        return super().prepare_field_value(field_name, field, value, value_is_complex)


class Settings(BaseSettings):
    interval: int | float = 60 * 60
    trackers_url: Annotated[list[str], BeforeValidator(_normalize_tracker_urls)] = []
    tracker_sources: Annotated[list[str], BeforeValidator(_normalize_tracker_urls)] = (
        DEFAULT_SOURCES
    )
    trackers: Annotated[list[str], BeforeValidator(_normalize_trackers)] = []
    proxy: AnyHttpUrl | None = None
    log_level: Annotated[
        Literal["TRACE", "DEBUG", "INFO", "SUCCESS", "WARNING", "ERROR", "CRITICAL"],
        BeforeValidator(lambda s: s.upper()),
    ] = "INFO"
    qb_host: str = "localhost:8080"
    qb_username: str = "admin"
    qb_password: SecretStr = SecretStr("adminadmin")

    debug: bool = False
    state_file: Path = Path("data/trackers_state.json")

    model_config = SettingsConfigDict(env_file=".env")

    @model_validator(mode="after")
    def _migrate_deprecated_trackers_url(self) -> Self:
        """Migrate the deprecated `trackers_url` setting to `tracker_sources`."""
        if (
            "trackers_url" in self.model_fields_set
            and self.trackers_url
            and "tracker_sources" not in self.model_fields_set
        ):
            self.tracker_sources = self.trackers_url
        return self

    @property
    def uses_deprecated_trackers_url(self) -> bool:
        """True when the deprecated `trackers_url` setting was explicitly set."""
        return "trackers_url" in self.model_fields_set

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            MyEnvSettingsSource(settings_cls),
            MyDotEnvSettingsSource(settings_cls),
            file_secret_settings,
        )


settings = Settings()
