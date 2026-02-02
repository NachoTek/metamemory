"""VAD-based audio chunking processor for intelligent segmentation.

Provides intelligent audio segmentation using Voice Activity Detection (VAD)
with minimum chunk size enforcement. This prevents word splitting while
maintaining low latency.
"""

import numpy as np
from typing import Optional, List


class VADChunkingProcessor:
    """VAD-based chunking processor with minimum chunk size enforcement.
    
    Accumulates audio in an internal buffer and extracts chunks when:
    1. Buffer reaches minimum chunk size, OR
    2. VAD detects speech end (speech -> silence transition)
    
    This hybrid approach prevents word splitting while keeping latency low.
    
    Reference: RESEARCH.md Pattern 1 (line 76-101)
    
    Example:
        processor = VADChunkingProcessor(min_chunk_size_sec=1.0)
        
        # Feed audio with VAD state
        for chunk in audio_stream:
            vad_is_speech = vad_detector(chunk)
            processor.feed_audio(chunk, vad_is_speech)
            
            # Check if we have a complete chunk to process
            if processor.should_process():
                chunk_to_transcribe = processor.get_chunk()
                # ... transcribe chunk_to_transcribe ...
    """
    
    def __init__(self, min_chunk_size_sec: float = 1.0, sample_rate: int = 16000):
        """Initialize the VAD chunking processor.
        
        Args:
            min_chunk_size_sec: Minimum chunk size in seconds (default 1.0)
            sample_rate: Sample rate in Hz (default 16000)
        """
        self.min_chunk_size_sec = min_chunk_size_sec
        self.sample_rate = sample_rate
        self.min_chunk_samples = int(min_chunk_size_sec * sample_rate)
        
        # Internal audio buffer
        self._buffer: List[np.ndarray] = []
        self._buffer_samples = 0
        
        # VAD state tracking
        self._prev_vad_speech = False
        self._speech_ended = False
    
    def feed_audio(self, chunk: np.ndarray, vad_is_speech: bool) -> None:
        """Add audio chunk with its VAD classification.
        
        Args:
            chunk: Audio samples as float32 array
            vad_is_speech: True if VAD detected speech in this chunk
        """
        self._buffer.append(chunk)
        self._buffer_samples += len(chunk)
        
        # Detect speech end (speech -> silence transition)
        if self._prev_vad_speech and not vad_is_speech:
            self._speech_ended = True
        
        self._prev_vad_speech = vad_is_speech
    
    def should_process(self) -> bool:
        """Check if we have enough audio to process a chunk.
        
        Returns:
            True if buffer has min_chunk_samples OR speech just ended
        """
        # Process if we have minimum chunk size
        if self._buffer_samples >= self.min_chunk_samples:
            return True
        
        # Process if speech ended (even if below minimum)
        if self._speech_ended and self._buffer_samples > 0:
            return True
        
        return False
    
    def get_chunk(self) -> Optional[np.ndarray]:
        """Extract a chunk for transcription.
        
        Extracts exactly min_chunk_samples if available, otherwise extracts
        all available audio (for speech end case). Keeps remainder in buffer
        for next chunk.
        
        Returns:
            Audio chunk as numpy array, or None if should_process() is False
        """
        if not self.should_process():
            return None
        
        # Determine how much to extract
        if self._buffer_samples >= self.min_chunk_samples:
            extract_samples = self.min_chunk_samples
        else:
            # Speech end case - extract all remaining audio
            extract_samples = self._buffer_samples
        
        # Concatenate buffer into single array
        if len(self._buffer) == 1:
            audio = self._buffer[0]
        else:
            audio = np.concatenate(self._buffer)
        
        # Extract chunk
        chunk = audio[:extract_samples]
        
        # Keep remainder for next iteration
        remainder = audio[extract_samples:]
        if len(remainder) > 0:
            self._buffer = [remainder]
            self._buffer_samples = len(remainder)
        else:
            self._buffer = []
            self._buffer_samples = 0
        
        # Reset speech end flag
        self._speech_ended = False
        
        return chunk
    
    def is_speech_end(self) -> bool:
        """Check if VAD detected speech end in last feed_audio call.
        
        Returns:
            True if speech -> silence transition detected
        """
        return self._speech_ended
    
    def get_buffer_duration(self) -> float:
        """Get current duration of audio in buffer.
        
        Returns:
            Duration in seconds
        """
        return self._buffer_samples / self.sample_rate
    
    def clear(self) -> None:
        """Clear the internal buffer and reset state."""
        self._buffer = []
        self._buffer_samples = 0
        self._prev_vad_speech = False
        self._speech_ended = False
