import tomllib
from typing import Any

from cosmotech.example_api.utils.logging import LOGGER


def str_to_bool(string: str) -> bool:
    return string.lower() in ("yes", "true", "t", "y", "1")


class Configuration:

    def __get_path(self, path: str, default: Any = None) -> Any:
        root = self.config_content
        elements = path.split(".")
        for element in elements:
            if element not in root:
                return default
            root = root[element]
        return root

    def __has_path(self, path) -> bool:
        return self.__get_path(path) is not None

    def __has_paths(self, paths) -> bool:
        return all(self.__get_path(path) is not None for path in paths)

    @property
    def psql_uri(self):
        paths = [
            "postgres.host",
            "postgres.port",
            "postgres.database",
            "postgres.schema",
            "postgres.username",
        ]

        if self.__get_path("postgres.enabled") == "false" or not self.__has_paths(paths):
            raise AttributeError("PostgreSQL config is not complete")

        # Read password from secret file if it exists, otherwise fall back to config
        password = None
        password_file = "/app/secrets/postgres-password"
        try:
            with open(password_file, "r") as f:
                password = f.read().strip()
                LOGGER.info("PostgreSQL password loaded from secret file")
        except FileNotFoundError:
            # Fall back to config password
            password = self.__get_path("postgres.password")
            if password is not None:
                LOGGER.warning(
                    "PostgreSQL password secret file not found, using password from config "
                    "(not recommended for production)"
                )
        except Exception as e:
            # On any other error, try to fall back to config password
            LOGGER.error(f"Error reading PostgreSQL password from secret file '{password_file}': {e}")
            password = self.__get_path("postgres.password")
            if password is not None:
                LOGGER.warning(
                    "Falling back to PostgreSQL password from config due to secret file read error "
                    "(not recommended for production)"
                )

        # Validate that password is not None or empty after all fallback attempts
        if password is None or password == "":
            raise AttributeError(
                "PostgreSQL password is not available. "
                "Please provide password via secret file (/app/secrets/postgres-password) "
                "or in config.toml under [postgres].password"
            )

        return (
            "postgresql://"
            + f"{self.__get_path('postgres.username')}"
            + f":{password}"
            + f"@{self.__get_path('postgres.host')}"
            + f":{self.__get_path('postgres.port')}"
            + f"/{self.__get_path('postgres.database')}"
        )

    @property
    def psql_schema(self):
        return self.__get_path("postgres.schema")

    @property
    def database_reset(self):
        return str_to_bool(self.__get_path("database.reset", "False"))

    @property
    def use_psql(self):
        return str_to_bool(self.__get_path("postgres.enabled", "False"))

    @property
    def alembic_script_location(self):
        return self.__get_path("alembic.script_location", "cosmotech/example_api/migrations")

    @property
    def cors_origins(self):
        return self.__get_path("cors.origins", [])

    @property
    def usage_enabled(self):
        return str_to_bool(self.__get_path("usage.enabled", "True"))

    def __init__(self, config_path):
        self.config_path = config_path
        try:
            with open(config_path, "rb") as f:
                self.config_content = tomllib.load(f)
        except FileNotFoundError:
            self.config_content = dict()
