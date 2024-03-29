from typing import Literal, Annotated, List, Tuple, Any, Type

from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
    PydanticBaseSettingsSource,
    EnvSettingsSource,
    DotEnvSettingsSource,
)
from pydantic import BeforeValidator, AnyUrl, AnyHttpUrl, SecretStr, AfterValidator
from pydantic.fields import FieldInfo


class MyEnvSettingsSource(EnvSettingsSource):
    def prepare_field_value(
        self, field_name: str, field: FieldInfo, value: Any, value_is_complex: bool
    ) -> Any:
        if field_name in ["trackers", "trackers_url"] and value:
            return value.split("\\n")
        return super().prepare_field_value(field_name, field, value, value_is_complex)


class MyDotEnvSettingsSource(DotEnvSettingsSource, MyEnvSettingsSource):
    def prepare_field_value(
        self, field_name: str, field: FieldInfo, value: Any, value_is_complex: bool
    ) -> Any:
        return MyEnvSettingsSource.prepare_field_value(
            self, field_name, field, value, value_is_complex
        )


class Settings(BaseSettings):
    interval: int | float = 60 * 60
    trackers_url: Annotated[
        List[AnyHttpUrl],
        AfterValidator(lambda urls: [url.unicode_string() for url in urls]),
    ] = [
        "https://raw.githubusercontent.com/ngosang/trackerslist/master/trackers_best.txt",
        "https://raw.githubusercontent.com/XIU2/TrackersListCollection/master/best.txt",
    ]
    trackers: Annotated[
        List[AnyUrl],
        AfterValidator(lambda urls: [url.unicode_string() for url in urls]),
    ] = []
    log_level: Annotated[
        Literal["TRACE", "DEBUG", "INFO", "SUCCESS", "WARNING", "ERROR", "CRITICAL"],
        BeforeValidator(lambda s: s.upper()),
    ] = "INFO"
    qb_host: str = "localhost:8080"
    qb_username: str = "admin"
    qb_password: SecretStr = "adminadmin"

    debug: bool = False

    model_config = SettingsConfigDict(env_file=".env")

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            MyEnvSettingsSource(settings_cls),
            MyDotEnvSettingsSource(settings_cls),
            file_secret_settings,
        )


settings = Settings()
