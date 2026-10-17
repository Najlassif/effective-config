
import os
from pathlib import Path

import yaml
from dotenv import dotenv_values
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DEFAULTS = {
    "port": 8000,
    "workers": 1,
    "debug": False,
    "log_level": "info",
    "api_key": "default-secret-000",
}

ASSIGNED_DOTENV = {
    "APP_LOG_LEVEL": "info",
    "APP_API_KEY": "key-8ubufo1hx2",
}

ASSIGNED_OS_ENV = {
    "APP_WORKERS": "16",
    "APP_DEBUG": "false",
    "APP_LOG_LEVEL": "error",
    "APP_API_KEY": "key-hs12e18jyb",
}

ALIASES = {
    "num_workers": "workers",
}


def normalize_key(key):
    key = key.strip().lower()
    if key.startswith("app_"):
        key = key[4:]
    return ALIASES.get(key, key)


def coerce(key, value):
    if key in ("port", "workers"):
        return int(value)

    if key == "debug":
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in (
            "true", "1", "yes", "on"
        )

    return str(value)


def merge_layer(config, layer):
    for key, value in layer.items():
        if value is not None:
            name = normalize_key(key)
            config[name] = coerce(name, value)


@app.get("/effective-config")
def effective_config(set: list[str] = Query(default=[])):
    config = DEFAULTS.copy()

    environment = os.getenv("APP_ENV", "development")
    yaml_path = Path(f"config.{environment}.yaml")

    if yaml_path.is_file():
        with yaml_path.open(encoding="utf-8") as f:
            yaml_config = yaml.safe_load(f) or {}
        merge_layer(config, yaml_config)

    # .env layer
    dotenv_config = ASSIGNED_DOTENV.copy()
    dotenv_config.update(dotenv_values(".env"))
    merge_layer(config, dotenv_config)

    # OS environment layer
    os_config = ASSIGNED_OS_ENV.copy()
    os_config.update({
        k: v for k, v in os.environ.items()
        if k.startswith("APP_") and k != "APP_ENV"
    })
    merge_layer(config, os_config)

    # Highest precedence: query overrides
    for item in set:
        if "=" in item:
            key, value = item.split("=", 1)
            name = normalize_key(key)
            config[name] = coerce(name, value)

    config["api_key"] = "****"
    return config
