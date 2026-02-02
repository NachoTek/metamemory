"""Whisper transcription engine using faster-whisper.

Provides real-time transcription with confidence scoring and word-level
timestamps. Uses faster-whisper for 4x speed improvement over openai-whisper.
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import numpy as np
import logging

# Import faster-whisper
from faster_whisper import WhisperModel


logger = logging.getLogger(__name__)


@dataclass
class WordInfo:
    """Word-level transcription information."""
    text: str
    start: float  # timestamp in seconds
    end: float
    confidence: int  # 0-100 scale


@dataclass
class TranscriptionSegment:
    """Transcription segment with metadata."""
    text: str
    confidence: int  # 0-100 scale
    start: float  # timestamp in seconds
    end: float
    words: List[WordInfo]


class WhisperTranscriptionEngine:
    """Whisper-based transcription engine with confidence extraction.
    
    Wraps faster-whisper for real-time transcription with:
    - Configurable model sizes (tiny/base/small)
    - Confidence score normalization (0-100 scale)
    - Word-level timestamps
    - Built-in VAD for speech detection
    
    Example:
        engine = WhisperTranscriptionEngine(model_size='base')
        engine.load_model()  # Load model (can take 5-10 seconds)
        
        # Transcribe audio chunk
        audio = np.zeros(16000 * 2, dtype=np.float32)  # 2 seconds of audio
        segments = engine.transcribe_chunk(audio)
        
        for segment in segments:
            print(f"{segment.text} (confidence: {segment.confidence}%)")
    """
    
    def __init__(
        self,
        model_size: str = "base",
        device: str = "cpu",
        compute_type: str = "int8",
    ):
        """Initialize the transcription engine.
        
        Args:
            model_size: Whisper model size ('tiny', 'base', 'small', 'medium', 'large')
            device: Device to use ('cpu', 'cuda')
            compute_type: Computation type ('int8', 'float16', 'float32')
        """
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        
        self._model: Optional[WhisperModel] = None
        self._model_loaded = False
        
        # Configuration for transcription
        self.beam_size = 5
        self.word_timestamps = True
        self.vad_filter = True
        self.vad_parameters = {
            "min_silence_duration_ms": 500,
            "speech_pad_ms": 200,
        }
        
        # Confidence normalization parameters
        # Whisper log_probs: -1.0 = high, -3.0 = low
        self._conf_high_logprob = -1.0
        self._conf_low_logprob = -3.0
        self._conf_high_score = 95
        self._conf_low_score = 30
    
    def load_model(self) -> None:
        """Load the Whisper model.
        
        This can take 5-10 seconds depending on model size and hardware.
        Should be called before starting transcription.
        """
        if self._model_loaded:
            return
        
        logger.info(f"Loading Whisper model: {self.model_size} (device={self.device}, compute={self.compute_type})")
        
        try:
            self._model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
            )
            self._model_loaded = True
            logger.info(f"Model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise
    
    def is_model_loaded(self) -> bool:
        """Check if the model has been loaded.
        
        Returns:
            True if model is loaded and ready for transcription
        """
        return self._model_loaded and self._model is not None
    
    def transcribe_chunk(self, audio_np: np.ndarray) -> List[TranscriptionSegment]:
        """Transcribe an audio chunk.
        
        Args:
            audio_np: Audio samples as float32 numpy array (mono, 16kHz)
            
        Returns:
            List of transcription segments with confidence scores
            
        Raises:
            RuntimeError: If model is not loaded
        """
        if not self.is_model_loaded():
            raise RuntimeError("Model not loaded. Call load_model() first.")
        
        if len(audio_np) == 0:
            return []
        
        # Ensure audio is float32
        if audio_np.dtype != np.float32:
            audio_np = audio_np.astype(np.float32)
        
        # Transcribe with faster-whisper
        segments, info = self._model.transcribe(
            audio_np,
            beam_size=self.beam_size,
            word_timestamps=self.word_timestamps,
            vad_filter=self.vad_filter,
            vad_parameters=self.vad_parameters,
            condition_on_previous_text=True,
        )
        
        # Convert to our segment format
        results = []
        for segment in segments:
            # Normalize confidence from avg_log_prob
            confidence = self._normalize_confidence(segment.avg_log_prob)
            
            # Extract word-level info
            words = []
            if segment.words:
                for word in segment.words:
                    words.append(WordInfo(
                        text=word.word,
                        start=word.start,
                        end=word.end,
                        confidence=confidence,  # Use segment confidence for words
                    ))
            
            results.append(TranscriptionSegment(
                text=segment.text.strip(),
                confidence=confidence,
                start=segment.start,
                end=segment.end,
                words=words,
            ))
        
        return results
    
    def _normalize_confidence(self, avg_log_prob: float) -> int:
        """Convert Whisper's avg_log_prob to 0-100 scale.
        
        Whisper log probabilities:
        - -1.0 to -1.5: High confidence
        - -2.0: Medium confidence
        - -3.0 or lower: Low confidence
        
        Args:
            avg_log_prob: Average log probability from Whisper
            
        Returns:
            Confidence score 0-100
        """
        # Clamp to range
        if avg_log_prob > self._conf_high_logprob:
            return self._conf_high_score
        elif avg_log_prob < self._conf_low_logprob:
            return self._conf_low_score
        
        # Linear interpolation
        # Map [low_logprob, high_logprob] to [low_score, high_score]
        normalized = (avg_log_prob - self._conf_low_logprob) / (
            self._conf_high_logprob - self._conf_low_logprob
        )
        return int(self._conf_low_score + normalized * (self._conf_high_score - self._conf_low_score))
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the loaded model.
        
        Returns:
            Dictionary with model size, device, compute type, etc.
        """
        return {
            "model_size": self.model_size,
            "device": self.device,
            "compute_type": self.compute_type,
            "loaded": self._model_loaded,
            "beam_size": self.beam_size,
            "vad_filter": self.vad_filter,
        }
