"""Performance monitoring and benchmarking for MetaMemory.

Provides:
- Word Error Rate (WER) calculation via word-level Levenshtein distance
- Live resource monitoring (RAM/CPU) with threshold detection
- Benchmark runner for transcription accuracy and latency measurement
"""

from metamemory.performance.wer import calculate_wer, calculate_wer_details
from metamemory.performance.monitor import ResourceMonitor, ResourceSnapshot
from metamemory.performance.benchmark import BenchmarkRunner, BenchmarkResult

__all__ = [
    "calculate_wer",
    "calculate_wer_details",
    "ResourceMonitor",
    "ResourceSnapshot",
    "BenchmarkRunner",
    "BenchmarkResult",
]
