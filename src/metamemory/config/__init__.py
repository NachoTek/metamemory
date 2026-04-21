"""Configuration module for metamemory.

Provides type-safe settings management with JSON persistence, versioning,
and smart defaults. Only user-modified settings are persisted.

Quick Start:
    >>> from metamemory.config import get_config, set_config, save_config
    >>> 
    >>> # Get model size
    >>> model_size = get_config('model.realtime_model_size')
    >>> 
    >>> # Change setting
    >>> set_config('model.realtime_model_size', 'base')
    >>> save_config()

Settings Categories:
    - model: Model selection (realtime_model_size)
    - transcription: Transcription behavior (enabled, confidence_threshold, etc.)
    - hardware: Hardware detection and recommendations
    - ui: UI behavior and appearance

Classes:
    AppSettings: Root container for all settings.
    ModelSettings: Model size configuration.
    TranscriptionSettings: Transcription behavior.
    HardwareSettings: Hardware detection settings.
    UISettings: UI appearance and behavior.
    ConfigManager: Main API for getting/setting/saving.
    SettingsPersistence: Low-level JSON persistence.

Functions:
    get_config: Get a config value or entire settings.
    set_config: Set a config value.
    save_config: Save config if modified.
"""

from metamemory.config.manager import (
    ConfigManager,
    get_config,
    get_config_manager,
    save_config,
    set_config,
)
from metamemory.config.models import (
    AppSettings,
    HardwareSettings,
    ModelSettings,
    TranscriptionSettings,
    UISettings,
)
from metamemory.config.persistence import (
    CURRENT_CONFIG_VERSION,
    ConfigVersion,
    SettingsPersistence,
)

__all__ = [
    # Models
    "AppSettings",
    "ModelSettings",
    "TranscriptionSettings",
    "HardwareSettings",
    "UISettings",
    # Manager
    "ConfigManager",
    "get_config_manager",
    # Convenience functions
    "get_config",
    "set_config",
    "save_config",
    # Persistence
    "SettingsPersistence",
    "ConfigVersion",
    "CURRENT_CONFIG_VERSION",
]
