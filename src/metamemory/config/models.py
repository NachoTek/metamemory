"""Settings dataclasses for metamemory configuration.

Provides type-safe configuration models with serialization support.
All settings use dataclasses with from_dict/to_dict methods for JSON persistence.
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, Tuple, Any, Dict


@dataclass
class ModelSettings:
    """Configuration for Whisper model selection.
    
    Attributes:
        realtime_model_size: Model size for real-time transcription.
            Options: "tiny", "base", "small", "auto"
            Default: "auto" (triggers hardware detection on first run)
        enhancement_model_size: Model size for background enhancement (Phase 3).
            Options: "small", "medium", "large"
            Default: "medium"
    """
    realtime_model_size: str = field(
        default="auto",
        metadata={"description": "Model size for real-time transcription: tiny, base, small, or auto"}
    )
    enhancement_model_size: str = field(
        default="medium",
        metadata={"description": "Model size for enhancement: small, medium, or large"}
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ModelSettings":
        """Create from dictionary, using defaults for missing fields."""
        return cls(
            realtime_model_size=data.get("realtime_model_size", cls.realtime_model_size),
            enhancement_model_size=data.get("enhancement_model_size", cls.enhancement_model_size)
        )


@dataclass
class TranscriptionSettings:
    """Configuration for transcription behavior.
    
    Attributes:
        enabled: Whether transcription is enabled.
            Default: True
        confidence_threshold: Threshold for triggering enhancement (Phase 3).
            Range: 0.0 to 1.0
            Default: 0.7
        min_chunk_size_sec: Minimum audio chunk size for VAD/processing.
            Default: 1.0 (seconds)
        agreement_threshold: Number of consecutive agreements for local agreement buffer.
            Default: 2
    """
    enabled: bool = field(
        default=True,
        metadata={"description": "Whether transcription is enabled"}
    )
    confidence_threshold: float = field(
        default=0.7,
        metadata={"description": "Confidence threshold for enhancement trigger (0.0-1.0)"}
    )
    min_chunk_size_sec: float = field(
        default=0.5,  # Reduced from 1.0s for lower latency (target < 2s total)
        metadata={"description": "Minimum audio chunk size in seconds"}
    )
    agreement_threshold: int = field(
        default=2,
        metadata={"description": "Consecutive agreements for local agreement buffer"}
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TranscriptionSettings":
        """Create from dictionary, using defaults for missing fields."""
        return cls(
            enabled=data.get("enabled", cls.enabled),
            confidence_threshold=data.get("confidence_threshold", cls.confidence_threshold),
            min_chunk_size_sec=data.get("min_chunk_size_sec", cls.min_chunk_size_sec),
            agreement_threshold=data.get("agreement_threshold", cls.agreement_threshold)
        )


@dataclass
class HardwareSettings:
    """Configuration for hardware detection and model recommendations.
    
    Attributes:
        auto_detect_on_startup: Whether to auto-detect hardware on first run.
            Default: True
        last_detected_ram_gb: Last detected RAM in GB (cached).
            Default: None
        last_detected_cpu_count: Last detected CPU core count (cached).
            Default: None
        recommended_model: Cached model recommendation from hardware detection.
            Default: None
        user_override_model: User's explicit model override (if set, ignores recommendation).
            Default: None
    """
    auto_detect_on_startup: bool = field(
        default=True,
        metadata={"description": "Auto-detect hardware capabilities on first run"}
    )
    last_detected_ram_gb: Optional[float] = field(
        default=None,
        metadata={"description": "Cached RAM detection result in GB"}
    )
    last_detected_cpu_count: Optional[int] = field(
        default=None,
        metadata={"description": "Cached CPU core count detection result"}
    )
    recommended_model: Optional[str] = field(
        default=None,
        metadata={"description": "Cached model recommendation from hardware detection"}
    )
    user_override_model: Optional[str] = field(
        default=None,
        metadata={"description": "User's explicit model size override"}
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HardwareSettings":
        """Create from dictionary, using defaults for missing fields."""
        return cls(
            auto_detect_on_startup=data.get("auto_detect_on_startup", cls.auto_detect_on_startup),
            last_detected_ram_gb=data.get("last_detected_ram_gb"),
            last_detected_cpu_count=data.get("last_detected_cpu_count"),
            recommended_model=data.get("recommended_model"),
            user_override_model=data.get("user_override_model")
        )


@dataclass
class UISettings:
    """Configuration for UI behavior and appearance.
    
    Attributes:
        show_confidence_legend: Whether to show the confidence color legend.
            Default: True
        transcript_auto_scroll: Whether transcript panel auto-scrolls.
            Default: True
        widget_position: Last known widget position as (x, y) tuple.
            Default: None (will use default positioning)
        widget_dock_edge: Which edge the widget is docked to.
            Options: "left", "right", "top", "bottom", None
            Default: None
    """
    show_confidence_legend: bool = field(
        default=True,
        metadata={"description": "Show confidence color coding legend in UI"}
    )
    transcript_auto_scroll: bool = field(
        default=True,
        metadata={"description": "Auto-scroll transcript panel to show new content"}
    )
    widget_position: Optional[Tuple[int, int]] = field(
        default=None,
        metadata={"description": "Last widget position as (x, y) tuple"}
    )
    widget_dock_edge: Optional[str] = field(
        default=None,
        metadata={"description": "Widget dock edge: left, right, top, bottom, or None"}
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = asdict(self)
        # Handle tuple serialization
        if result.get("widget_position") is not None:
            result["widget_position"] = list(result["widget_position"])
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UISettings":
        """Create from dictionary, using defaults for missing fields."""
        pos = data.get("widget_position")
        if pos is not None and isinstance(pos, list):
            pos = tuple(pos)
        
        return cls(
            show_confidence_legend=data.get("show_confidence_legend", cls.show_confidence_legend),
            transcript_auto_scroll=data.get("transcript_auto_scroll", cls.transcript_auto_scroll),
            widget_position=pos,
            widget_dock_edge=data.get("widget_dock_edge")
        )


@dataclass
class AppSettings:
    """Root container for all application settings.
    
    This is the top-level settings object that contains all configuration
    categories. It handles versioning for migration support.
    
    Attributes:
        config_version: Configuration schema version for migrations.
            Current: 1
        model: Model selection settings.
        transcription: Transcription behavior settings.
        hardware: Hardware detection and recommendation settings.
        ui: UI behavior and appearance settings.
    """
    config_version: int = field(
        default=1,
        metadata={"description": "Configuration schema version for migrations"}
    )
    model: ModelSettings = field(default_factory=ModelSettings)
    transcription: TranscriptionSettings = field(default_factory=TranscriptionSettings)
    hardware: HardwareSettings = field(default_factory=HardwareSettings)
    ui: UISettings = field(default_factory=UISettings)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "config_version": self.config_version,
            "model": self.model.to_dict(),
            "transcription": self.transcription.to_dict(),
            "hardware": self.hardware.to_dict(),
            "ui": self.ui.to_dict()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AppSettings":
        """Create from dictionary, using defaults for missing/invalid fields."""
        # Handle nested settings with defaults if missing
        model_data = data.get("model", {})
        transcription_data = data.get("transcription", {})
        hardware_data = data.get("hardware", {})
        ui_data = data.get("ui", {})
        
        return cls(
            config_version=data.get("config_version", cls.config_version),
            model=ModelSettings.from_dict(model_data) if isinstance(model_data, dict) else ModelSettings(),
            transcription=TranscriptionSettings.from_dict(transcription_data) if isinstance(transcription_data, dict) else TranscriptionSettings(),
            hardware=HardwareSettings.from_dict(hardware_data) if isinstance(hardware_data, dict) else HardwareSettings(),
            ui=UISettings.from_dict(ui_data) if isinstance(ui_data, dict) else UISettings()
        )

    @classmethod
    def get_defaults(cls) -> "AppSettings":
        """Get a fresh instance with all default values."""
        return cls()
