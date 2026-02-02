"""Hardware detection and model recommendation module.

Provides system hardware detection using psutil and intelligent model size
recommendations based on detected specs.
"""

from metamemory.hardware.detector import HardwareDetector, SystemSpecs
from metamemory.hardware.recommender import (
    ModelRecommender,
    ModelInfo,
    recommend_model_size,
    get_model_info,
    get_all_model_info,
)

__all__ = [
    "HardwareDetector",
    "SystemSpecs",
    "ModelRecommender",
    "ModelInfo",
    "recommend_model_size",
    "get_model_info",
    "get_all_model_info",
]
