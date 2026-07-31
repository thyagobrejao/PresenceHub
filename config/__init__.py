"""Configuration layer for PresenceHub.

Handles loading, validation, and access to YAML configuration with
environment variable overrides and sensible defaults.
"""

from config.defaults import DEFAULT_CONFIG
from config.loader import ConfigLoader, load_config

__all__ = [
    "ConfigLoader",
    "DEFAULT_CONFIG",
    "load_config",
]
