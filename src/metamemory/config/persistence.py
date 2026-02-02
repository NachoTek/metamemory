"""JSON persistence layer for settings with atomic writes and versioning.

Provides SettingsPersistence class for loading and saving configuration
to JSON files with atomic file operations, versioning support, and migrations.
"""

import json
import logging
import os
import platform
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, Optional

from metamemory.config.models import AppSettings


logger = logging.getLogger(__name__)


@dataclass
class ConfigVersion:
    """Configuration version information.
    
    Attributes:
        version: Schema version number
        description: Human-readable description of this version
    """
    version: int
    description: str


# Current config version - bump this when schema changes
CURRENT_CONFIG_VERSION = 1

# Version history for migrations
VERSION_HISTORY: Dict[int, ConfigVersion] = {
    1: ConfigVersion(1, "Initial schema with model, transcription, hardware, UI settings")
}


class SettingsPersistence:
    """Handles atomic JSON persistence of application settings.
    
    Features:
    - Atomic file writes (write to temp, then rename)
    - Config versioning with automatic migrations
    - Smart defaults (merge saved values over defaults)
    - Platform-appropriate config directory
    - Graceful handling of missing/corrupted files
    
    Example:
        >>> persistence = SettingsPersistence()
        >>> settings = persistence.load_settings()
        >>> persistence.save_settings(settings)
    """
    
    def __init__(self, config_dir: Optional[Path] = None):
        """Initialize persistence with optional custom config directory.
        
        Args:
            config_dir: Override for config directory. If None, uses
                platform-appropriate location.
        """
        self._config_dir = config_dir
        self._config_path: Optional[Path] = None
    
    def get_config_path(self) -> Path:
        """Get the path to the config.json file.
        
        Uses platform-appropriate location:
        - Windows: %APPDATA%/metamemory/config.json
        - macOS: ~/Library/Application Support/metamemory/config.json
        - Linux: ~/.config/metamemory/config.json
        
        Returns:
            Path to config.json file.
        """
        if self._config_path is not None:
            return self._config_path
        
        if self._config_dir is not None:
            config_dir = self._config_dir
        else:
            config_dir = self._get_default_config_dir()
        
        # Ensure directory exists
        config_dir.mkdir(parents=True, exist_ok=True)
        
        self._config_path = config_dir / "config.json"
        return self._config_path
    
    def _get_default_config_dir(self) -> Path:
        """Get the default configuration directory for the current platform.
        
        Returns:
            Path to the config directory.
        """
        system = platform.system()
        
        if system == "Windows":
            # Windows: %APPDATA%/metamemory
            app_data = os.environ.get("APPDATA")
            if app_data:
                return Path(app_data) / "metamemory"
            else:
                # Fallback to user profile
                return Path.home() / "AppData" / "Roaming" / "metamemory"
        
        elif system == "Darwin":
            # macOS: ~/Library/Application Support/metamemory
            return Path.home() / "Library" / "Application Support" / "metamemory"
        
        else:
            # Linux and others: ~/.config/metamemory
            xdg_config = os.environ.get("XDG_CONFIG_HOME")
            if xdg_config:
                return Path(xdg_config) / "metamemory"
            else:
                return Path.home() / ".config" / "metamemory"
    
    def get_default_settings(self) -> AppSettings:
        """Get a fresh instance with all default values.
        
        Returns:
            AppSettings with default values.
        """
        return AppSettings.get_defaults()
    
    def load_raw(self) -> Optional[Dict[str, Any]]:
        """Load raw config dictionary from file.
        
        Returns:
            Dictionary with config data, or None if file doesn't exist or is corrupted.
        """
        config_path = self.get_config_path()
        
        if not config_path.exists():
            logger.info(f"Config file not found at {config_path}, using defaults")
            return None
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if not content.strip():
                logger.warning(f"Config file at {config_path} is empty, using defaults")
                return None
            
            data = json.loads(content)
            
            if not isinstance(data, dict):
                logger.warning(f"Config file at {config_path} is not a dictionary, using defaults")
                return None
            
            logger.debug(f"Loaded config from {config_path}")
            return data
            
        except json.JSONDecodeError as e:
            logger.warning(f"Config file at {config_path} has invalid JSON: {e}, using defaults")
            return None
        except Exception as e:
            logger.error(f"Error reading config file at {config_path}: {e}, using defaults")
            return None
    
    def load_settings(self) -> AppSettings:
        """Load settings from file, applying migrations and smart defaults.
        
        If file doesn't exist or is corrupted, returns default settings.
        If config version is outdated, runs migration chain.
        
        Returns:
            AppSettings instance (loaded or defaults).
        """
        raw_data = self.load_raw()
        
        if raw_data is None:
            # No config file or corrupted - return defaults
            logger.info("Using default settings")
            return self.get_default_settings()
        
        # Check version and migrate if needed
        file_version = raw_data.get("config_version", 0)
        
        if file_version < CURRENT_CONFIG_VERSION:
            logger.info(f"Migrating config from version {file_version} to {CURRENT_CONFIG_VERSION}")
            raw_data = self.migrate_config(raw_data, file_version)
        
        # Build settings from dict (handles missing fields with defaults)
        settings = AppSettings.from_dict(raw_data)
        
        # Ensure version is current
        settings.config_version = CURRENT_CONFIG_VERSION
        
        return settings
    
    def save_settings(self, settings: AppSettings) -> bool:
        """Save settings to file atomically.
        
        Uses atomic write pattern: write to temp file, then rename.
        This prevents corruption if the process crashes during write.
        
        Args:
            settings: Settings to save.
        
        Returns:
            True if saved successfully, False otherwise.
        """
        config_path = self.get_config_path()
        
        try:
            # Serialize to JSON
            data = settings.to_dict()
            json_content = json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False)
            
            # Write to temp file in same directory (for atomic rename)
            temp_fd, temp_path = tempfile.mkstemp(
                dir=config_path.parent,
                prefix="config.json.tmp.",
                suffix=".tmp"
            )
            
            try:
                # Write content
                with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
                    f.write(json_content)
                    f.flush()
                    os.fsync(temp_fd)  # Ensure data is written to disk
                
                # Atomic rename
                os.replace(temp_path, config_path)
                
                logger.debug(f"Saved config to {config_path}")
                return True
                
            except Exception:
                # Clean up temp file on error
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass
                raise
                
        except Exception as e:
            logger.error(f"Failed to save config to {config_path}: {e}")
            return False
    
    def migrate_config(self, config_dict: Dict[str, Any], from_version: int) -> Dict[str, Any]:
        """Migrate config dictionary from old version to current.
        
        Migrations are additive - they add new fields with defaults but
        preserve existing user data.
        
        Args:
            config_dict: Config dictionary at from_version.
            from_version: Version number of the config_dict.
        
        Returns:
            Migrated config dictionary at CURRENT_CONFIG_VERSION.
        """
        current_version = from_version
        
        # Chain migrations from from_version to CURRENT_CONFIG_VERSION
        while current_version < CURRENT_CONFIG_VERSION:
            next_version = current_version + 1
            
            # Apply migration for this step
            config_dict = self._apply_migration(config_dict, current_version, next_version)
            config_dict["config_version"] = next_version
            current_version = next_version
        
        return config_dict
    
    def _apply_migration(
        self,
        config_dict: Dict[str, Any],
        from_version: int,
        to_version: int
    ) -> Dict[str, Any]:
        """Apply a single migration step.
        
        Override this method to add custom migration logic for specific
        version transitions.
        
        Args:
            config_dict: Config dictionary at from_version.
            from_version: Source version.
            to_version: Target version.
        
        Returns:
            Migrated config dictionary at to_version.
        """
        # Example migrations (add more as needed):
        
        if from_version == 0 and to_version == 1:
            # Migration from pre-versioned configs to version 1
            # Ensure all required sections exist
            if "model" not in config_dict:
                config_dict["model"] = {}
            if "transcription" not in config_dict:
                config_dict["transcription"] = {}
            if "hardware" not in config_dict:
                config_dict["hardware"] = {}
            if "ui" not in config_dict:
                config_dict["ui"] = {}
        
        # Future migrations go here:
        # elif from_version == 1 and to_version == 2:
        #     # Example: rename a field
        #     if "old_field_name" in config_dict:
        #         config_dict["new_field_name"] = config_dict.pop("old_field_name")
        
        return config_dict
    
    def delete_config(self) -> bool:
        """Delete the config file (for testing/reset purposes).
        
        Returns:
            True if file was deleted or didn't exist, False on error.
        """
        config_path = self.get_config_path()
        
        try:
            if config_path.exists():
                config_path.unlink()
                logger.info(f"Deleted config file at {config_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete config file at {config_path}: {e}")
            return False
    
    def get_config_info(self) -> Dict[str, Any]:
        """Get information about the current config state.
        
        Returns:
            Dictionary with config path, exists status, and version info.
        """
        config_path = self.get_config_path()
        raw = self.load_raw()
        
        return {
            "path": str(config_path),
            "exists": config_path.exists(),
            "version": raw.get("config_version", 0) if raw else None,
            "current_version": CURRENT_CONFIG_VERSION,
            "needs_migration": (raw.get("config_version", 0) < CURRENT_CONFIG_VERSION) if raw else False
        }
