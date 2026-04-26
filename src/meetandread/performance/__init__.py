"""Performance monitoring and benchmarking for MeetAndRead.

Provides:
- Word Error Rate (WER) calculation via word-level Levenshtein distance
- Live resource monitoring (RAM/CPU) with threshold detection
- Benchmark runner for transcription accuracy and latency measurement
"""

from meetandread.performance.wer import calculate_wer, calculate_wer_details
from meetandread.performance.monitor import ResourceMonitor, ResourceSnapshot
from meetandread.performance.benchmark import BenchmarkRunner, BenchmarkResult

__all__ = [
    "calculate_wer",
    "calculate_wer_details",
    "ResourceMonitor",
    "ResourceSnapshot",
    "BenchmarkRunner",
    "BenchmarkResult",
]
