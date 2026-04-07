import os
import pathlib
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.routing import APIRoute
from sqlmodel import create_engine

from cosmotech.example_api import API_NAME, __version__
from cosmotech.example_api.routers import (
    usage_router,
)
from cosmotech.example_api.schema import add_engine, initialize_tables
from cosmotech.example_api.utils.config import Configuration
from cosmotech.example_api.utils.logging import LOGGER
from cosmotech.example_api.utils.oauth2 import KEYCLOAK_REALM
from cosmotech.example_api.utils.usage_middleware import UsageMiddleware

ROOT_URI = os.environ.get("ROOT_URI", "/")
DATA_DIR = os.environ.get("DATA_DIR", "./data")
CONFIG_PATH = os.environ.get("CONFIG_PATH", "config.toml")


@asynccontextmanager
async def lifespan(app: FastAPI):
    LOGGER.debug(f"Root uri : {ROOT_URI}")
    LOGGER.debug(f"Keycloak realm : {KEYCLOAK_REALM}")
    LOGGER.debug(f"Data dir : {DATA_DIR}")
    LOGGER.debug(f"Config path : {CONFIG_PATH}")

    if KEYCLOAK_REALM is None:
        raise EnvironmentError("KEYCLOAK_REALM is required")

    if not pathlib.Path(DATA_DIR).exists():
        pathlib.Path(DATA_DIR).mkdir(parents=True, exist_ok=True)

    try:
        _config = Configuration(CONFIG_PATH)
        uri = _config.psql_uri
        connect_args = {"options": "-csearch_path={}".format(_config.psql_schema)}
    except (AttributeError, FileNotFoundError):
        LOGGER.warning("No psql uri configured, going for sqlite database")
        sqlite_file_name = pathlib.Path(DATA_DIR) / "database.db"
        uri = f"sqlite:///{sqlite_file_name.absolute()}"
        connect_args = {}

    add_engine(create_engine(uri, connect_args=connect_args))
    initialize_tables()

    yield


# Code found on FastAPI discussion : https://github.com/fastapi/fastapi/discussions/6695#discussioncomment-8247988
# Used to remove 422 error code from documentation
_openapi = FastAPI.openapi


def openapi(self: FastAPI):
    _openapi(self)

    for _, method_item in self.openapi_schema.get("paths").items():
        for _, param in method_item.items():
            responses = param.get("responses")
            # remove 422 response, also can remove other status code
            if "422" in responses:
                del responses["422"]

            # Keep only the most specific (last) tag so that sub-router endpoints
            # appear exclusively under their own category and not under every
            # ancestor router's category.
            if "tags" in param and len(param["tags"]) > 1:
                param["tags"] = [param["tags"][-1]]

    return self.openapi_schema


FastAPI.openapi = openapi

app = FastAPI(
    version=__version__,
    docs_url="/swagger",
    redoc_url="/swagger/redoc",
    swagger_ui_oauth2_redirect_url="/swagger/oauth2-redirect",
    openapi_url="/openapi.json",
    title=API_NAME,
    description=f"API for {API_NAME}",
    root_path=ROOT_URI,
    lifespan=lifespan,
)

try:
    _configuration = Configuration(CONFIG_PATH)
    if origin := _configuration.cors_origins:
        from fastapi.middleware.cors import CORSMiddleware

        app.add_middleware(
            CORSMiddleware,
            allow_origins=origin,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        LOGGER.info(f"CORS configured")
    else:
        LOGGER.info("No CORS origins configured")
except FileNotFoundError:
    LOGGER.info("No configuration file found, skipping CORS configuration")


@app.get("/about")
async def root(request: Request):
    from cosmotech.example_api import __version__

    return {"version": __version__}


# Usage router is registered on the main app but hidden from its OpenAPI docs.
# It remains callable and is documented in the admin sub-app Swagger instead.
app.include_router(usage_router, include_in_schema=False)

# Admin sub-application: exposes usage endpoints with their own Swagger UI.
# Accessible at /admin/swagger (and /admin/openapi.json).
_usage_enabled = True
try:
    _usage_config = Configuration(CONFIG_PATH)
    _usage_enabled = _usage_config.usage_enabled
except (AttributeError, FileNotFoundError):
    pass

app.add_middleware(UsageMiddleware, enabled=_usage_enabled)

admin_app = FastAPI(
    version=__version__,
    docs_url="/admin/swagger",
    redoc_url="/admin/swagger/redoc",
    swagger_ui_oauth2_redirect_url="/swagger/oauth2-redirect",
    openapi_url="/admin/openapi.json",
    title=f"{API_NAME} — Admin API",
    description=f"Admin API for {API_NAME} — usage metering and monitoring.",
    root_path=ROOT_URI,
)
admin_app.include_router(usage_router)
app.mount("/admin", admin_app)


def use_route_names_as_operation_ids(app: FastAPI) -> None:
    """
    Simplify operation IDs so that generated API clients have simpler function
    names.

    Should be called only after all routes have been added.
    """
    for route in app.routes:
        if isinstance(route, APIRoute):
            route.operation_id = route.name  # in this case, 'read_items'


use_route_names_as_operation_ids(app)
