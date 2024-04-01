from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseConfig(BaseSettings):
    # NOTE: BaseConfig 클래스는 .env 내의 다른 변수들은 보지 않고, ENV_STATE만 봄
    ENV_STATE: str | None = None

    # NOTE: Pydantic v2부터는 Config 클래스가 아닌 model_config 사용해야 함
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class GlobalConfig(BaseConfig):
    # Database
    DATABASE_URL: str | None = None
    DB_FORCE_ROLL_BACK: bool = False

    # Logging
    LOGTAIL_API_KEY: str | None = None

    # Security
    JWT_SECRET_KEY: str | None = None
    JWT_ALGORITHM: str = "HS256"

    # Mailgun
    MAILGUN_DOMAIN: str | None = None
    MAILGUN_API_KEY: str | None = None


class DevConfig(GlobalConfig):
    model_config = SettingsConfigDict(env_prefix="DEV_")


class ProdConfig(GlobalConfig):
    model_config = SettingsConfigDict(env_prefix="PROD_")


class TestConfig(GlobalConfig):
    # NOTE: Pydantic v2부터는 type을 무조건 써주어야 함
    # hardcoded, but are defaults that can be overwritten
    DATABASE_URL: str = "sqlite:///test.db"
    DB_FORCE_ROLL_BACK: bool = True  # -- important!
    JWT_SECRET_KEY: str = "163a30ff9545d7790e7e64077f4a12aaa46194f95feb02c6e9f53a650d4b62b3ec83929597a2f1f608e02686c1aceff16eda5c0bb8056c8b0a54367ca933d2b0"

    model_config = SettingsConfigDict(env_prefix="TEST_")


@lru_cache()
def get_config(env_state: str):
    configs = {"dev": DevConfig, "prod": ProdConfig, "test": TestConfig}
    return configs[env_state]()


config = get_config(BaseConfig().ENV_STATE)
