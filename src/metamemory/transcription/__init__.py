"""Real-time transcription engine with faster-whisper.

Provides the core transcription pipeline:
- AudioRingBuffer: Thread-safe audio buffering
- VADChunkingProcessor: Intelligent audio segmentation
- LocalAgreementBuffer: Prevents text flickering
- WhisperTranscriptionEngine: Whisper model inference with confidence
"""

from metamemory.transcription.audio_buffer import AudioRingBuffer
from metamemory.transcription.vad_processor import VADChunkingProcessor
from metamemory.transcription.local_agreement import LocalAgreementBuffer
from metamemory.transcription.engine import (
    WhisperTranscriptionEngine,
    TranscriptionSegment,
    WordInfo,
)

__all__ = [
    "AudioRingBuffer",
    "VADChunkingProcessor",
    "LocalAgreementBuffer",
    "WhisperTranscriptionEngine",
    "TranscriptionSegment",
    "WordInfo",
]
