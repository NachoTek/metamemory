"""Hardware detection and model recommendation module.

Provides system hardware detection using psutil and intelligent model size
recommendations based on detected specs.
"""

from metamemory.hardware.detector import HardwareDetector, SystemSpecs

__all__ = [
    "HardwareDetector",
    "SystemSpecs",
]
