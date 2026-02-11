"""
Enhancement module for dual-mode transcription processing.

This module implements the enhancement architecture for processing low-confidence
segments using background workers without blocking real-time transcription.
"""

import asyncio
import logging
from queue import Queue
from typing import Dict, Any, Optional, List
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


class EnhancementQueue:
    """Bounded queue for low-confidence segments waiting for enhancement."""
    
    def __init__(self, max_size: int = 100):
        """
        Initialize the enhancement queue with bounded capacity.
        
        Args:
            max_size: Maximum number of segments to hold in queue (default: 100)
        """
        self.queue = Queue(maxsize=max_size)
        self.total_enqueued = 0
        self.total_processed = 0
        self.dropped_segments = 0
        
    def enqueue(self, segment: Dict[str, Any]) -> bool:
        """
        Add segment to queue if space available.
        
        Args:
            segment: Dictionary containing segment data with at least 'id' and 'text'
            
        Returns:
            bool: True if segment was enqueued, False if queue was full
        """
        if self.queue.full():
            self.dropped_segments += 1
            logger.warning(f"Enhancement queue full, dropped segment {segment['id']}")
            return False
            
        self.queue.put(segment)
        self.total_enqueued += 1
        logger.debug(f"Enqueued segment {segment['id']} (queue size: {self.queue.qsize()}")
        return True
    
    def dequeue(self) -> Optional[Dict[str, Any]]:
        """
        Get next segment from queue.
        
        Returns:
            Optional[Dict[str, Any]]: Segment dictionary or None if queue is empty
        """
        try:
            segment = self.queue.get_nowait()
            self.total_processed += 1
            logger.debug(f"Dequeued segment {segment['id']} (queue size: {self.queue.qsize()}")
            return segment
        except:
            return None
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current queue status.
        
        Returns:
            Dict[str, Any]: Dictionary with queue statistics
        """
        return {
            'size': self.queue.qsize(),
            'max_size': self.queue.maxsize,
            'total_enqueued': self.total_enqueued,
            'total_processed': self.total_processed,
            'dropped_segments': self.dropped_segments,
            'is_full': self.queue.full(),
            'is_empty': self.queue.empty()
        }


class EnhancementWorkerPool:
    """Async worker pool for background enhancement processing."""
    
    def __init__(self, num_workers: int = 4):
        """
        Initialize the worker pool with specified number of workers.
        
        Args:
            num_workers: Number of parallel workers to use (default: 4)
        """
        self.num_workers = num_workers
        self.executor = ThreadPoolExecutor(max_workers=num_workers)
        self.tasks = []
        self.is_running = False
        self.pending_tasks = 0
        
    async def process_segment(self, segment: Dict[str, Any], 
                            processor: 'EnhancementProcessor') -> Dict[str, Any]:
        """
        Process a segment using the enhancement processor.
        
        Args:
            segment: Segment dictionary to process
            processor: EnhancementProcessor instance to use for processing
            
        Returns:
            Dict[str, Any]: Enhanced segment with results
        """
        loop = asyncio.get_event_loop()
        
        try:
            enhanced = await loop.run_in_executor(
                self.executor,
                processor.enhance,
                segment
            )
            return enhanced
        except Exception as e:
            logger.error(f"Error processing segment {segment['id']}: {e}")
            return {
                'id': segment['id'],
                'error': str(e),
                'original_text': segment['text'],
                'confidence': segment['confidence']
            }
    
    def start(self):
        """Start the worker pool."""
        self.is_running = True
        logger.info(f"Started EnhancementWorkerPool with {self.num_workers} workers")
    
    def stop(self):
        """Stop the worker pool and clean up resources."""
        self.is_running = False
        self.executor.shutdown(wait=True)
        logger.info("Stopped EnhancementWorkerPool")
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current worker pool status.
        
        Returns:
            Dict[str, Any]: Dictionary with worker pool statistics
        """
        return {
            'num_workers': self.num_workers,
            'is_running': self.is_running,
            'pending_tasks': self.pending_tasks,
            'active_threads': len(self.executor._threads) if hasattr(self.executor, '_threads') else 0
        }


class EnhancementProcessor:
    """Large model inference engine for segment enhancement."""
    
    def __init__(self, model_name: str = "medium"):
        """
        Initialize the enhancement processor with specified model.
        
        Args:
            model_name: Name of Whisper model to use for enhancement (default: "medium")
        """
        self.model_name = model_name
        self.model = None
        self.load_model()
        
    def load_model(self):
        """Load the Whisper model for enhancement."""
        try:
            import whisper
            logger.info(f"Loading Whisper {self.model_name} model for enhancement...")
            self.model = whisper.load_model(self.model_name)
            logger.info(f"Successfully loaded Whisper {self.model_name} model")
        except ImportError:
            logger.warning("whisper library not available, enhancement will be disabled")
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
    
    def enhance(self, segment: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhance the segment using large Whisper model.
        
        Args:
            segment: Segment dictionary containing text and confidence
            
        Returns:
            Dict[str, Any]: Enhanced segment with improved text
        """
        if not self.model:
            # If model not available, return original segment
            return {
                'id': segment['id'],
                'original_text': segment['text'],
                'enhanced_text': segment['text'],
                'confidence': segment['confidence'],
                'enhanced': False,
                'message': 'Enhancement model not available'
            }
        
        try:
            # Use Whisper to enhance the segment
            result = self.model.transcribe(segment['text'])
            
            enhanced_segment = {
                'id': segment['id'],
                'original_text': segment['text'],
                'enhanced_text': result['text'],
                'confidence': result.get('confidence', segment['confidence']),
                'enhanced': True,
                'model': self.model_name
            }
            
            logger.debug(f"Enhanced segment {segment['id']}")
            return enhanced_segment
            
        except Exception as e:
            logger.error(f"Error enhancing segment {segment['id']}: {e}")
            return {
                'id': segment['id'],
                'original_text': segment['text'],
                'enhanced_text': segment['text'],
                'confidence': segment['confidence'],
                'enhanced': False,
                'error': str(e)
            }


class TranscriptUpdater:
    """Real-time transcript update mechanism for enhanced segments."""
    
    def __init__(self):
        """Initialize the transcript updater."""
        self.updates = []
        self.lock = asyncio.Lock()
        
    async def add_update(self, update: Dict[str, Any]):
        """
        Add transcript update.
        
        Args:
            update: Dictionary containing update information
        """
        async with self.lock:
            self.updates.append(update)
    
    async def get_updates(self) -> List[Dict[str, Any]]:
        """
        Get all pending updates.
        
        Returns:
            List[Dict[str, Any]]: List of pending updates
        """
        async with self.lock:
            updates = self.updates.copy()
            self.updates.clear()
            return updates
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current update status.
        
        Returns:
            Dict[str, Any]: Dictionary with update statistics
        """
        return {
            'pending_updates': len(self.updates)
        }