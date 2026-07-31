"""Configuration loader with YAML file support, env var overrides, and deep merge.

Loads config.yaml, merges with defaults, applies environment variable overrides,
and provides typed access to configuration values.
"""

from __future__ import annotations

import os
from copy import deepcopy
from pathlib import Path
from typing import Any

import structlog
import yaml

from config.defaults import DEFAULT_CONFIG
from core.exceptions import InvalidConfigurationError

logger = structlog.get_logger(__name__)


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge two dictionaries, with override values taking precedence.

    Args:
        base: Base dictionary (defaults).
        override: Override dictionary (user config).

    Returns:
        Merged dictionary.
    """
    result = deepcopy(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _env_override(config: dict[str, Any], prefix: str = "PH_") -> dict[str, Any]:
    """Override configuration values from environment variables.

    Environment variables use the prefix 'PH_' followed by uppercase,
    underscore-separated keys. Nested keys use double underscore.

    Examples:
        PH_MQTT_HOST=mosquitto      -> config["mqtt"]["host"]
        PH_PRESENCE_TIMEOUT=600      -> config["presence"]["timeout"]
        PH_DETECTORS_ARP_ENABLED=false -> config["detectors"]["arp"]["enabled"]

    Args:
        config: The configuration dictionary to override.
        prefix: Environment variable prefix.

    Returns:
        Configuration with environment variable overrides applied.
    """
    for env_key, env_value in os.environ.items():
        if not env_key.startswith(prefix):
            continue

        # Remove prefix and split by double underscore for nesting
        config_path = env_key[len(prefix) :].lower().split("__")

        # Navigate and set the value
        target = config
        for part in config_path[:-1]:
            if part not in target or not isinstance(target[part], dict):
                target[part] = {}
            target = target[part]

        # Cast to appropriate type
        final_key = config_path[-1]
        existing = target.get(final_key)
        if existing is not None:
            target[final_key] = _cast_env_value(env_value, type(existing))
        else:
            target[final_key] = env_value

    return config


def _cast_env_value(value: str, target_type: type) -> Any:
    """Cast an environment variable string to the appropriate type.

    Args:
        value: Raw environment variable value.
        target_type: Expected Python type.

    Returns:
        The value cast to the target type.
    """
    if target_type is bool:
        return value.lower() in ("true", "1", "yes", "on")
    if target_type is int:
        return int(value)
    if target_type is float:
        return float(value)
    if target_type is list:
        return [item.strip() for item in value.split(",") if item.strip()]
    return value


class ConfigLoader:
    """Loads and manages PresenceHub configuration.

    Configuration is built from three layers (in priority order):
        1. Default values (config/defaults.py)
        2. YAML config file (config/config.yaml)
        3. Environment variables (PH_* prefix)

    Usage:
        config = ConfigLoader.load("config/config.yaml")
        mqtt_host = config["mqtt"]["host"]
    """

    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    @classmethod
    def load(cls, config_path: str | Path | None = None) -> ConfigLoader:
        """Load configuration from file, defaults, and environment.

        Args:
            config_path: Path to YAML configuration file.
                         If None, only defaults and env vars are used.

        Returns:
            Configured ConfigLoader instance.

        Raises:
            InvalidConfigurationError: If the config file cannot be loaded.
        """
        config = deepcopy(DEFAULT_CONFIG)

        # Layer 2: YAML file
        if config_path:
            path = Path(config_path)
            if path.exists():
                try:
                    with open(path) as f:
                        user_config = yaml.safe_load(f) or {}
                    config = _deep_merge(config, user_config)
                    logger.info("config_loaded", path=str(path))
                except yaml.YAMLError as exc:
                    raise InvalidConfigurationError(f"Failed to parse {path}: {exc}") from exc
                except OSError as exc:
                    raise InvalidConfigurationError(f"Failed to read {path}: {exc}") from exc
            else:
                logger.warning("config_file_not_found", path=str(path))

        # Layer 3: Environment variables
        config = _env_override(config)

        logger.info("config_initialized", sections=list(config.keys()))
        return cls(config)

    def get(self, *keys: str, default: Any = None) -> Any:
        """Get a nested configuration value using dot-path keys.

        Args:
            *keys: Path components to the config value.
            default: Default value if the path doesn't exist.

        Returns:
            The configuration value, or default if not found.
        """
        target: Any = self._data
        for key in keys:
            if isinstance(target, dict):
                target = target.get(key)
            else:
                return default
            if target is None:
                return default
        return target

    def __getitem__(self, key: str) -> Any:
        return self._data[key]

    def __contains__(self, key: str) -> bool:
        return key in self._data

    def to_dict(self) -> dict[str, Any]:
        """Return a deep copy of the full configuration dictionary."""
        return deepcopy(self._data)

    def __repr__(self) -> str:
        return f"ConfigLoader(sections={list(self._data.keys())})"


def load_config(config_path: str | Path | None = None) -> ConfigLoader:
    """Convenience function to load configuration.

    Args:
        config_path: Path to YAML configuration file.

    Returns:
        Configured ConfigLoader instance.
    """
    return ConfigLoader.load(config_path)
