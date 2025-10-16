# File with environment variables and general configuration logic.
# Env variables are combined in nested groups like "Security", "Database" etc.
# So environment variable (case-insensitive) for jwt_secret_key will be "security__jwt_secret_key"
#
# Pydantic priority ordering:
#
# 1. (Most important, will overwrite everything) - environment variables
# 2. `.env` file in root folder of project
# 3. Default values
#
# "sqlalchemy_database_uri" is computed field that will create valid database URL
#
# See https://pydantic-docs.helpmanual.io/usage/settings/
# Note, complex types like lists are read as json-encoded strings.


import logging.config
from functools import lru_cache
from pathlib import Path

from pydantic import AnyHttpUrl, BaseModel, Field, SecretStr, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine.url import URL

PROJECT_DIR = Path(__file__).parent.parent.parent


class Security(BaseModel):
    """Configuración relacionada con la seguridad y autenticación (JWT, CORS, etc.)."""
    jwt_issuer: str = "my-app"
    jwt_secret_key: SecretStr = SecretStr("sk-change-me")
    jwt_access_token_expire_secs: int = 24 * 3600  # 1d
    refresh_token_expire_secs: int = 28 * 24 * 3600  # 28d
    password_bcrypt_rounds: int = 12
    allowed_hosts: list[str] = ["localhost", "127.0.0.1"]
    backend_cors_origins: list[AnyHttpUrl] = []


class Database(BaseModel):
    """Configuración de conexión para la base de datos PostgreSQL."""
    hostname: str = "postgres"
    username: str = "postgres"
    password: SecretStr = SecretStr("passwd-change-me")
    port: int = 5432
    db: str = "postgres"

class Telemetry(BaseSettings):
    """Configuración para la telemetría y monitoreo (OpenTelemetry)."""
    service_name: str = "service_name"
    otlp_endpoint: str = "otl_endpoint"
    insecure_otlp: bool = True
    # 🔑 CLAVE: Nuevo flag para habilitar/deshabilitar la telemetría (se lee como TELEMETRY__ENABLED)
    enabled: bool = False # <-- Recomiendo 'False' por defecto si no es requerido en todos los entornos
    
class Kafka(BaseModel):
    """
    Configuración para la conexión con Apache Kafka.
    Se utiliza para la arquitectura basada en eventos.
    La variable de entorno asociada es: KAFKA__BOOTSTRAP_SERVERS
    """
    # Lista de servidores iniciales (brokers) de Kafka en formato host:port
    bootstrap_servers: str = "localhost:9092" 
    # Se recomienda usar KAFKA__ENABLED=false en el .env si se quiere deshabilitar
    enabled: bool = True # <-- Asume True por defecto

class Settings(BaseSettings):
    """
    Clase principal que contiene toda la configuración de la aplicación.
    Los campos se cargan automáticamente desde variables de entorno o .env.
    """
    title: str = "Minimal Fastapi Postgres Template"
    version: str = "6.1.0"
    description: str = "https://github.com/potlitel/minimal-fastapi-template"
    # Modelos de configuración anidados (se cargan con prefijo, ej. 'security__...')
    telemetry: Telemetry = Field(default_factory=Telemetry)
    security: Security = Field(default_factory=Security)
    database: Database = Field(default_factory=Database)
    kafka: Kafka = Field(default_factory=Kafka)
    
    log_level: str = "INFO"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def sqlalchemy_database_uri(self) -> URL:
        """
        Campo calculado que genera la URL de conexión completa a la base de datos
        para SQLAlchemy, incluyendo el driver asíncrono.
        """
        return URL.create(
            drivername="postgresql+asyncpg",
            username=self.database.username,
            password=self.database.password.get_secret_value(),
            host=self.database.hostname,
            port=self.database.port,
            database=self.database.db,
        )

    model_config = SettingsConfigDict(
        env_file=f"{PROJECT_DIR}/.env",
        case_sensitive=False,
        env_nested_delimiter="__",# Define el separador para variables anidadas (ej. DATABASE__HOSTNAME)
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Función optimizada (LRU Cache) para cargar la configuración una sola vez.
    Garantiza que la configuración sea singleton en toda la aplicación.
    """
    return Settings()


def logging_config(log_level: str) -> None:
    """Configura el sistema de logging de Python usando un diccionario de configuración."""
    conf = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "verbose": {
                "format": "{asctime} [{levelname}] {name}: {message}",
                "style": "{",
            },
        },
        "handlers": {
            "stream": {
                "class": "logging.StreamHandler",
                "formatter": "verbose",
                "level": "DEBUG",
            },
        },
        "loggers": {
            "": {
                "level": log_level,
                "handlers": ["stream"],
                "propagate": True,
            },
        },
    }
    logging.config.dictConfig(conf)


logging_config(log_level=get_settings().log_level)
