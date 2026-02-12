"""Streaming pipeline for real-time transcription.

Orchestrates all transcription components into a unified pipeline:
- AudioRingBuffer: Thread-safe audio buffering
- VADChunkingProcessor: Intelligent audio segmentation
- WhisperTranscriptionEngine: Whisper model inference (whisper.cpp backend)

HYBRID TRANSCRIPTION DESIGN:
- Real-time transcription: Each chunk is committed immediately (no agreement buffer)
- Confidence scores are preserved for UI color styling
- Post-processing happens after recording stops (see PostProcessingQueue)

This class runs transcription in a background thread to avoid blocking
the audio capture or UI threads.

Compatible with whisper.cpp via pywhispercpp (CPU-only, no PyTorch DLLs).
"""

import threading
import time
import queue
import logging
import asyncio
from concurrent.futures import Future
logger = logging.getLogger(__name__)
from dataclasses import dataclass
from typing import Optional, List, Callable, Any, Dict
from pathlib import Path
import numpy as np

from metamemory.config.models import AppSettings, TranscriptionSettings, EnhancementSettings
from metamemory.transcription.audio_buffer import AudioRingBuffer
from metamemory.transcription.vad_processor import VADChunkingProcessor
from metamemory.transcription.engine import WhisperTranscriptionEngine, TranscriptionSegment
from metamemory.transcription.enhancement import (
    EnhancementQueue, EnhancementWorkerPool, EnhancementProcessor, 
    TranscriptUpdater, EnhancementConfig
)
from metamemory.transcription.confidence import should_enhance, ConfidenceLevel


@dataclass
class PipelineResult:
    """Result from the transcription pipeline.
    
    Attributes:
        text: Transcribed text
        confidence: Confidence score (0-100)
        start_time: Start timestamp in seconds from recording start
        end_time: End timestamp
        words: List of word-level data with timestamps and confidence
        is_realtime: Whether this is from real-time transcription (True) or post-processing (False)
        chunk_id: Unique identifier for this chunk (for post-processing correlation)
        is_enhanced: Whether this segment was enhanced with large model (True for bold formatting)
        original_text: Original text before enhancement (if enhanced)
        enhancement_error: Error message if enhancement failed
    """
    text: str
    confidence: int
    start_time: float
    end_time: float
    words: List[Any]  # List of WordInfo or similar
    is_realtime: bool = True
    chunk_id: int = 0
    is_enhanced: bool = False
    original_text: str = ""
    enhancement_error: Optional[str] = None


class RealTimeTranscriptionProcessor:
    """Orchestrates real-time transcription from audio capture to text output.
    
    This class integrates all transcription components and runs inference
    in a background thread to maintain low latency and avoid blocking.
    
    Threading Model:
    - Audio capture thread: Calls feed_audio() from AudioSession consumer
    - Processing thread: Runs inference in background (_processing_loop)
    - UI thread: Calls get_results() to retrieve new segments
    
    All component access is thread-safe through internal locking.
    
    Example:
        config = TranscriptionSettings(min_chunk_size_sec=1.0, agreement_threshold=2)
        processor = RealTimeTranscriptionProcessor(config)
        
        # Load model (can be done before starting)
        processor.load_model(lambda progress: print(f"Loading: {progress}%"))
        
        # Start processing
        processor.start()
        
        # Feed audio from capture callback
        processor.feed_audio(audio_chunk)
        
        # Get results in UI update loop
        results = processor.get_results()
        
        # Stop when done
        processor.stop()
    """
    
    def __init__(self, config: AppSettings, model_size: str = "tiny"):
        """Initialize the transcription processor.
        
        HYBRID TRANSCRIPTION: 
        - Real-time: Each chunk is committed immediately (no agreement buffer blocking)
        - Confidence scores preserved for UI color styling
        - Post-processing happens after recording stops with stronger model
        
        Args:
            config: Complete application settings including enhancement configuration
            model_size: Whisper model size (tiny for real-time, base/small for post-process)
        """
        self._config = config.transcription  # Use transcription settings
        self._enhancement_config = config.enhancement  # Use enhancement settings
        self._model_size = model_size
        
        # Core components
        self._audio_buffer = AudioRingBuffer(max_seconds=30, sample_rate=16000)
        self._vad_processor = VADChunkingProcessor(
            min_chunk_size_sec=self._config.min_chunk_size_sec,
            sample_rate=16000
        )
        
        # Enhancement components
        self._enhancement_queue = EnhancementQueue(max_size=100)
        enhancement_config = EnhancementConfig(
            confidence_threshold=self._enhancement_config.confidence_threshold,
            num_workers=self._enhancement_config.num_workers,
            enhancement_model=self._enhancement_config.enhancement_model
        )
        self._enhancement_worker_pool = EnhancementWorkerPool(
            num_workers=self._enhancement_config.num_workers,
            dynamic_scaling=self._enhancement_config.dynamic_scaling,
            cpu_usage_threshold=self._enhancement_config.cpu_usage_threshold
        )
        self._enhancement_processor = EnhancementProcessor(config=enhancement_config)
        self._transcript_updater = TranscriptUpdater()
        
        # Track enhancement status
        self._is_processing_enhancement = False
        self._enhancement_completed_segments = 0
        self._enhancement_failed_segments = 0
        
        # NO LocalAgreementBuffer - we commit immediately for real-time display
        # The agreement buffer was designed for re-transcribing accumulated audio
        # We transcribe each chunk once and commit immediately
        
        # Engine is created but model not loaded yet
        self._engine: Optional[WhisperTranscriptionEngine] = None
        self._model_device: str = "cpu"
        self._model_compute_type: str = "int8"
        
        # Threading
        self._processing_thread: Optional[threading.Thread] = None
        self._is_running = False
        self._stop_event = threading.Event()
        self._result_queue: queue.Queue[PipelineResult] = queue.Queue()
        self._buffer_lock = threading.Lock()
        
        # State tracking
        self._recording_start_time: Optional[float] = None
        self._total_samples_processed = 0
        self._last_vad_was_speech = False
        self._chunk_counter = 0  # For tracking chunks
        
        # Callback for model loading progress
        self._load_progress_callback: Optional[Callable[[int], None]] = None
        
        # Word-level confidence callback for enhanced granularity
        self._on_word_confidence: Optional[Callable[[str, int, Dict], None]] = None
        
        # Enhancement event loop for async processing
        self._enhancement_event_loop: Optional[asyncio.AbstractEventLoop] = None
        self._enhancement_thread: Optional[threading.Thread] = None
        self._enhancement_stop_event = threading.Event()
    
    def set_model_config(self, model_size: str, device: str = "cpu", 
                         compute_type: str = "int8") -> None:
        """Configure model parameters before loading.
        
        Args:
            model_size: Whisper model size ("tiny", "base", "small", "medium", "large")
            device: Device to run on ("cpu", "cuda", etc.)
            compute_type: Compute type ("int8", "float16", "float32")
        """
        self._model_size = model_size
        self._model_device = device
        self._model_compute_type = compute_type
    
    def load_model(self, progress_callback: Optional[Callable[[int], None]] = None) -> None:
        """Load the Whisper model.
        
        This can take 5-10 seconds depending on model size and hardware.
        Call before start() for immediate transcription availability.
        
        Args:
            progress_callback: Optional callback(int: 0-100) for loading progress
        """
        self._load_progress_callback = progress_callback
        
        if progress_callback:
            progress_callback(0)
        
        # Create and load the engine
        self._engine = WhisperTranscriptionEngine(
            model_size=self._model_size,
            device=self._model_device,
            compute_type=self._model_compute_type
        )
        
        if progress_callback:
            progress_callback(50)
        
        self._engine.load_model()
        
        if progress_callback:
            progress_callback(100)
    
    def is_model_loaded(self) -> bool:
        """Check if the Whisper model is loaded and ready.
        
        Returns:
            True if model is loaded, False otherwise
        """
        if self._engine is None:
            return False
        return self._engine.is_model_loaded()
    
    def start(self) -> None:
        """Start the transcription processing thread.
        
        Raises:
            RuntimeError: If called when already running
        """
        if self._is_running:
            raise RuntimeError("Processor is already running")
        
        # Reset state
        self._recording_start_time = time.time()
        self._total_samples_processed = 0
        self._last_vad_was_speech = False
        self._enhancement_completed_segments = 0
        self._enhancement_failed_segments = 0
        
        # Clear any previous results
        while not self._result_queue.empty():
            try:
                self._result_queue.get_nowait()
            except queue.Empty:
                break
        
        # Start processing thread
        self._is_running = True
        self._stop_event.clear()
        self._processing_thread = threading.Thread(
            target=self._processing_loop,
            daemon=True,
            name="TranscriptionProcessor"
        )
        self._processing_thread.start()
        
        # Start enhancement processing in background
        self.start_enhancement_processing()
    
    def stop(self) -> None:
        """Stop the transcription processing thread.
        
        Waits up to 5 seconds for the processing thread to finish.
        Also waits up to 30 seconds for enhancement processing to complete.
        """
        if not self._is_running:
            return
        
        self._is_running = False
        self._stop_event.set()
        
        if self._processing_thread:
            self._processing_thread.join(timeout=5.0)
            self._processing_thread = None
        
        # Stop enhancement processing
        self.stop_enhancement_processing(timeout=30.0)
    
    def feed_audio(self, chunk: np.ndarray) -> None:
        """Feed audio data from the capture thread.
        
        This method is thread-safe and can be called from any thread,
        typically from the AudioSession consumer thread.
        
        Args:
            chunk: Audio samples as float32 numpy array at 16kHz mono
        """
        with self._buffer_lock:
            self._audio_buffer.append(chunk)
            
            # Update VAD state (we assume speech if we got audio)
            # In a full implementation, this would come from a real VAD
            self._vad_processor.feed_audio(chunk, vad_is_speech=True)
    
    def get_results(self) -> List[PipelineResult]:
        """Get new transcription results (non-blocking).
        
        Call this from the UI thread periodically to retrieve
        new transcribed segments.
        
        Returns:
            List of PipelineResult objects since last call
        """
        results = []
        try:
            while True:
                result = self._result_queue.get_nowait()
                results.append(result)
        except queue.Empty:
            pass
        return results
    
    def _processing_loop(self) -> None:
        """Background thread that processes audio chunks.
        
        This runs continuously while is_running is True, checking
        for audio in the buffer and running Whisper inference.
        """
        while self._is_running and not self._stop_event.is_set():
            # Check if we have enough audio to process
            should_process = False
            chunk_to_process = None
            
            with self._buffer_lock:
                # Check if we should extract a chunk
                if self._vad_processor.should_process():
                    chunk_to_process = self._vad_processor.get_chunk()
                    should_process = chunk_to_process is not None
            
            if should_process and chunk_to_process is not None and self._engine is not None:
                # Ensure model is loaded
                if not self._engine.is_model_loaded():
                    self._engine.load_model()
                
                # Run transcription (this is the slow part - 0.5-2s)
                try:
                    print(f"DEBUG: Transcribing chunk of {len(chunk_to_process)} samples...")
                    segments = self._engine.transcribe_chunk(chunk_to_process)
                    print(f"DEBUG: Transcription returned {len(segments)} segments")
                    
                    # Process segments through agreement buffer
                    self._process_segments(segments, chunk_to_process)
                    
                    # Update tracking
                    self._total_samples_processed += len(chunk_to_process)
                    
                except Exception as e:
                    # Log error but continue processing
                    print(f"Transcription error: {e}")
                
                # Small sleep to prevent CPU spinning
                time.sleep(0.01)
            else:
                # Wait a bit longer if no audio to process
                time.sleep(0.05)
    
    def _process_segments(self, segments: List[TranscriptionSegment], 
                         audio_chunk: np.ndarray) -> None:
        """Process transcription segments and update results.
        
        HYBRID TRANSCRIPTION: 
        - Commits immediately (no agreement buffer blocking)
        - Preserves confidence scores for UI color styling
        - Stores results in queue for UI consumption
        
        Args:
            segments: Transcription segments from Whisper
            audio_chunk: The audio chunk that was transcribed
        """
        if not segments:
            return
        
        # Get the text from all segments
        full_text = " ".join([seg.text for seg in segments]).strip()
        
        print(f"DEBUG: Segment texts: {[seg.text for seg in segments]}")
        print(f"DEBUG: Full text: '{full_text}'")
        
        if not full_text:
            print(f"DEBUG: Empty full_text, returning")
            return
        
        # IMMEDIATE COMMIT - no agreement buffer blocking for real-time display
        # Each transcribed chunk flows immediately to the UI
        committed_text = full_text
        
        # Calculate average confidence for the segment
        if segments:
            avg_confidence = sum(seg.confidence for seg in segments) / len(segments)
        else:
            avg_confidence = 0
            
        # Check if this segment should be enhanced
        should_enhance_flag = should_enhance({
            'confidence': avg_confidence,
            'text': committed_text,
            'id': f"chunk_{self._chunk_counter}"
        }, 
        threshold=self._enhancement_config.confidence_threshold)
        
        logger.info(f"[ENHANCEMENT CHECK] chunk={self._chunk_counter}, text='{committed_text[:30]}', confidence={avg_confidence}%, threshold={self._enhancement_config.confidence_threshold*100}%, should_enhance={should_enhance_flag}")
        
        # Queue for enhancement if eligible
        if should_enhance_flag:
            enhancement_segment = {
                'id': f"chunk_{self._chunk_counter}",
                'text': committed_text,
                'confidence': avg_confidence,
                'start': segments[0].start if segments else 0,
                'end': segments[-1].end if segments else 0
            }
            
            if not self._enhancement_queue.enqueue(enhancement_segment):
                logger.warning(f"Failed to enqueue segment {enhancement_segment['id']} for enhancement")
        print(f"DEBUG: Immediate commit (no agreement buffer): '{committed_text}'")
        
        # Calculate timing
        chunk_duration = len(audio_chunk) / 16000  # 16kHz sample rate
        end_time = self._total_samples_processed / 16000
        start_time = end_time - chunk_duration
        
        # Calculate average confidence across all segments
        avg_confidence = sum(seg.confidence for seg in segments) / len(segments)
        
        # Collect all words with their individual confidence scores
        all_words = []
        for seg in segments:
            if hasattr(seg, 'words') and seg.words:
                all_words.extend(seg.words)
        
        # If no word-level data, create words from the segment text
        if not all_words:
            words_list = committed_text.split()
            word_duration = chunk_duration / max(1, len(words_list))
            for i, word_text in enumerate(words_list):
                word_start = start_time + (i * word_duration)
                word_end = word_start + word_duration
                # Create a simple word info dict with confidence
                word_info = {
                    'word': word_text,
                    'start': word_start,
                    'end': word_end,
                    'confidence': int(avg_confidence)
                }
                all_words.append(word_info)
        
        # Increment chunk counter for tracking
        self._chunk_counter += 1
        
        # Create result with full metadata
        result = PipelineResult(
            text=committed_text,
            confidence=int(avg_confidence),
            start_time=max(0, start_time),
            end_time=end_time,
            words=all_words,
            is_realtime=True,
            chunk_id=self._chunk_counter
        )
        
        # Queue for UI consumption
        self._result_queue.put(result)
        print(f"DEBUG: Queued result chunk #{self._chunk_counter} with {len(all_words)} words")
    
    def get_stats(self) -> dict:
        """Get processing statistics.
        
        Returns:
            Dictionary with processing statistics
        """
        with self._buffer_lock:
            buffer_duration = self._audio_buffer.get_total_duration()
        
        return {
            "is_running": self._is_running,
            "is_model_loaded": self.is_model_loaded(),
            "model_size": self._model_size,
            "buffer_duration_sec": buffer_duration,
            "total_samples_processed": self._total_samples_processed,
            "pending_results": self._result_queue.qsize(),
        }
    
    def reset(self) -> None:
        """Reset the processor for a new recording session.
        
        Clears all buffers and state, but keeps the loaded model.
        """
        with self._buffer_lock:
            # Clear audio buffer
            self._audio_buffer = AudioRingBuffer(max_seconds=30, sample_rate=16000)
            
            # Reset VAD processor
            self._vad_processor = VADChunkingProcessor(
                min_chunk_size_sec=self._config.min_chunk_size_sec,
                sample_rate=16000
            )
        
        # NO agreement buffer to reset - we commit immediately
        
        # Clear results queue
        while not self._result_queue.empty():
            try:
                self._result_queue.get_nowait()
            except queue.Empty:
                break
        
        # Reset state
        self._recording_start_time = None
        self._total_samples_processed = 0
        self._last_vad_was_speech = False
    
    def start_enhancement_processing(self) -> None:
        """Start the background enhancement processing thread.
        
        This should be called when recording starts to begin processing
        queued segments in the background.
        """
        if self._enhancement_thread is not None and self._enhancement_thread.is_alive():
            logger.warning("Enhancement processing thread already running")
            return
        
        self._enhancement_stop_event.clear()
        self._enhancement_thread = threading.Thread(
            target=self._enhancement_processing_loop,
            daemon=True,
            name="EnhancementProcessor"
        )
        self._enhancement_thread.start()
        
        # Register completion callback
        self._enhancement_worker_pool.add_completion_callback(self._on_enhancement_complete)
        
        # Start worker pool
        self._enhancement_worker_pool.start()
        
        logger.info("Started enhancement processing thread")
    
    def stop_enhancement_processing(self, timeout: float = 30.0) -> None:
        """Stop the background enhancement processing thread.
        
        Args:
            timeout: Maximum time to wait for pending enhancement tasks (default: 30s)
        """
        if self._enhancement_thread is None:
            return
        
        self._enhancement_stop_event.set()
        
        # Wait for processing thread to stop
        self._enhancement_thread.join(timeout=2.0)
        self._enhancement_thread = None
        
        # Stop worker pool
        if self._enhancement_worker_pool.is_running:
            # Run async stop in event loop
            if self._enhancement_event_loop:
                asyncio.run_coroutine_threadsafe(
                    self._enhancement_worker_pool.stop(timeout=timeout),
                    self._enhancement_event_loop
                )
        
        logger.info(f"Stopped enhancement processing (completed: {self._enhancement_completed_segments}, failed: {self._enhancement_failed_segments})")
    
    def _enhancement_processing_loop(self) -> None:
        """Background thread that processes enhancement queue.
        
        This runs continuously, pulling segments from the enhancement queue
        and submitting them to the worker pool for processing.
        """
        # Create event loop for this thread
        self._enhancement_event_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._enhancement_event_loop)
        
        logger.info("Enhancement processing loop started")
        
        try:
            while not self._enhancement_stop_event.is_set():
                # Check if there are segments to enhance
                segment = self._enhancement_queue.dequeue()
                
                if segment is not None:
                    logger.debug(f"Dequeued segment {segment['id']} for enhancement")
                    
                    # Process segment asynchronously
                    future = asyncio.run_coroutine_threadsafe(
                        self._enhancement_worker_pool.process_segment_async(
                            segment,
                            self._enhancement_processor
                        ),
                        self._enhancement_event_loop
                    )
                    
                    # Handle future errors
                    def future_done_callback(f: Future):
                        try:
                            f.result()
                        except Exception as e:
                            logger.error(f"Enhancement future error: {e}")
                    
                    future.add_done_callback(future_done_callback)
                else:
                    # No segments to process, sleep briefly
                    time.sleep(0.05)
                    
        except Exception as e:
            logger.error(f"Enhancement processing loop error: {e}")
        finally:
            # Close event loop
            self._enhancement_event_loop.close()
            self._enhancement_event_loop = None
            logger.info("Enhancement processing loop stopped")
    
    def _on_enhancement_complete(self, result: Dict[str, Any]) -> None:
        """
        Handle completion of segment enhancement.
        
        Called by the worker pool when a segment enhancement completes.
        Queues the enhanced segment for UI display with bold formatting.
        
        Args:
            result: Enhancement result dictionary containing:
                - id: Segment ID
                - enhanced_text: Enhanced transcription (if successful)
                - original_text: Original transcription
                - confidence: Confidence score
                - enhanced: Whether enhancement succeeded
                - error: Error message (if failed)
        """
        segment_id = result.get('id', 'unknown')
        
        if result.get('enhanced', False):
            # Enhancement successful
            enhanced_text = result.get('enhanced_text', result.get('original_text', ''))
            original_text = result.get('original_text', '')
            confidence = result.get('confidence', 0)
            
            # Create PipelineResult for enhanced segment
            # Use is_enhanced=True to trigger bold formatting in UI
            enhanced_result = PipelineResult(
                text=enhanced_text,
                confidence=int(confidence),
                start_time=result.get('start', 0.0),
                end_time=result.get('end', 0.0),
                words=result.get('words', []),
                is_realtime=False,  # Enhanced segments are post-processed
                chunk_id=int(segment_id.replace('chunk_', '')) if 'chunk_' in segment_id else 0,
                is_enhanced=True,  # Bold formatting flag
                original_text=original_text,
                enhancement_error=None
            )
            
            # Queue for UI consumption
            self._result_queue.put(enhanced_result)
            
            self._enhancement_completed_segments += 1
            logger.debug(f"Enhancement complete for segment {segment_id}: '{enhanced_text}' (bold)")
        else:
            # Enhancement failed
            error_msg = result.get('error', 'Unknown error')
            original_text = result.get('original_text', result.get('text', ''))
            
            # Queue original segment with error flag
            failed_result = PipelineResult(
                text=original_text,
                confidence=result.get('confidence', 0),
                start_time=0.0,
                end_time=0.0,
                words=[],
                is_realtime=False,
                chunk_id=int(segment_id.replace('chunk_', '')) if 'chunk_' in segment_id else 0,
                is_enhanced=False,
                original_text=original_text,
                enhancement_error=error_msg
            )
            
            self._result_queue.put(failed_result)
            self._enhancement_failed_segments += 1
            logger.warning(f"Enhancement failed for segment {segment_id}: {error_msg}")
    
    def get_enhancement_status(self) -> Dict[str, Any]:
        """Get current enhancement processing status.
        
        Returns:
            Dict[str, Any]: Dictionary with enhancement statistics
        """
        worker_pool_status = self._enhancement_worker_pool.get_status()
        queue_status = self._enhancement_queue.get_status()
        
        return {
            'is_processing': self._enhancement_thread is not None and self._enhancement_thread.is_alive(),
            'completed_segments': self._enhancement_completed_segments,
            'failed_segments': self._enhancement_failed_segments,
            'worker_pool': worker_pool_status,
            'queue': queue_status
        }
