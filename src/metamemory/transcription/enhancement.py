"""
Enhancement module for dual-mode transcription processing.

This module implements the enhancement architecture for processing low-confidence
segments using background workers without blocking real-time transcription.
"""

import asyncio
import logging
from queue import Queue
from typing import Dict, Any, Optional, List, Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
import numpy as np
import time
import psutil

logger = logging.getLogger(__name__)


@dataclass
class EnhancementConfig:
    """Configuration for enhancement processing."""
    confidence_threshold: float = 0.7  # Default: 70%
    num_workers: int = 4  # Default: 4 workers
    max_queue_size: int = 100  # Default: 100 segments
    enhancement_model: str = "medium"  # Large model for enhancement
    
    def update_settings(self, **kwargs):
        """Update enhancement settings."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)


class EnhancementQueue:
    """Bounded queue for low-confidence segments waiting for enhancement."""
    
    def __init__(self, max_size: int = 100, confidence_threshold: float = 0.7):
        """
        Initialize the enhancement queue with bounded capacity.
        
        Args:
            max_size: Maximum number of segments to hold in queue (default: 100)
            confidence_threshold: Confidence threshold for enhancement (default: 0.7)
        """
        self.queue = Queue(maxsize=max_size)
        self.total_enqueued = 0
        self.total_processed = 0
        self.dropped_segments = 0
        self.confidence_threshold = confidence_threshold
        
    def should_enhance(self, segment: Dict[str, Any]) -> bool:
        """
        Determine if segment should be enhanced based on confidence threshold.
        
        Args:
            segment: Segment dictionary containing at least 'confidence' key
            
        Returns:
            bool: True if segment confidence is below threshold and should be enhanced
        """
        confidence = segment.get('confidence')
        threshold_score = self.confidence_threshold * 100
        
        # Handle edge cases
        if confidence is None:
            logger.debug(f"Segment {segment.get('id')} has no confidence, skipping enhancement")
            return False
        
        # Check if confidence is below threshold
        if confidence < threshold_score:
            logger.debug(f"Segment {segment.get('id')} confidence {confidence}% < threshold {threshold_score}%, eligible for enhancement")
            return True
        else:
            logger.debug(f"Segment {segment.get('id')} confidence {confidence}% >= threshold {threshold_score}%, not eligible for enhancement")
            return False
    
    def enqueue(self, segment: Dict[str, Any]) -> bool:
        """
        Add segment to queue if space available and meets enhancement criteria.
        
        Args:
            segment: Dictionary containing segment data with at least 'id', 'text', and 'confidence'
            
        Returns:
            bool: True if segment was enqueued, False if queue was full or not eligible
        """
        # Check if segment should be enhanced
        if not self.should_enhance(segment):
            return False
            
        if self.queue.full():
            self.dropped_segments += 1
            logger.warning(f"Enhancement queue full, dropped segment {segment['id']}")
            return False
            
        self.queue.put(segment)
        self.total_enqueued += 1
        logger.info(f"[ENHANCEMENT ENQUEUE] Enqueued segment {segment['id']} (queue size: {self.queue.qsize()})")
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
            logger.info(f"[ENHANCEMENT DEQUEUE] Dequeued segment {segment['id']} (queue size: {self.queue.qsize()})")
            return segment
        except:
            logger.debug("[ENHANCEMENT DEQUEUE] Queue is empty")
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
            'is_empty': self.queue.empty(),
            'confidence_threshold': self.confidence_threshold
        }
    
    def set_confidence_threshold(self, threshold: float):
        """Update the confidence threshold for enhancement eligibility.
        
        Args:
            threshold: New confidence threshold (0.0-1.0)
        """
        if 0.0 <= threshold <= 1.0:
            self.confidence_threshold = threshold
            logger.info(f"Updated enhancement confidence threshold to {threshold}")
        else:
            logger.warning(f"Invalid confidence threshold {threshold}, must be between 0.0 and 1.0")


class EnhancementWorkerPool:
    """Async worker pool for background enhancement processing.

    Features:
    - Parallel processing using asyncio + ThreadPoolExecutor
    - Dynamic worker scaling based on system load (CPU and RAM)
    - Completion callbacks for real-time transcript updates
    - Error handling with retry logic
    - Graceful degradation under resource constraints
    - Performance metrics and completion timing
    - Context tracking for recording vs post-stop scenarios
    """

    def __init__(self, num_workers: int = 4,
                 min_workers: int = 2,
                 max_workers: int = 8,
                 dynamic_scaling: bool = True,
                 cpu_usage_threshold: float = 0.8,
                 ram_usage_threshold: float = 0.85,
                 worker_scaling_algorithm: str = "adaptive"):
        """
        Initialize the worker pool with specified number of workers.

        Args:
            num_workers: Initial number of parallel workers (default: 4)
            min_workers: Minimum workers when scaling down (default: 2)
            max_workers: Maximum workers when scaling up (default: 8)
            dynamic_scaling: Enable auto-scaling based on system load (default: True)
            cpu_usage_threshold: CPU usage threshold for scaling (default: 0.8)
            ram_usage_threshold: RAM usage threshold for scaling (default: 0.85)
            worker_scaling_algorithm: Scaling algorithm - "adaptive", "linear", or "none" (default: "adaptive")
        """
        self.num_workers = num_workers
        self.min_workers = min_workers
        self.max_workers = max_workers
        self.dynamic_scaling = dynamic_scaling
        self.cpu_usage_threshold = cpu_usage_threshold
        self.ram_usage_threshold = ram_usage_threshold
        self.worker_scaling_algorithm = worker_scaling_algorithm

        # Initialize executor with current worker count
        self.executor = ThreadPoolExecutor(max_workers=num_workers)

        # Task tracking
        self.pending_tasks = 0
        self.completed_tasks = 0
        self.failed_tasks = 0
        self.retry_count = 0
        self.max_retries = 2

        # Async task tracking
        self.async_tasks: List[asyncio.Task] = []
        self.active_tasks: Dict[str, asyncio.Task] = {}

        # Worker pool state
        self.is_running = False
        self._scaling_lock = asyncio.Lock()

        # Performance metrics
        self.task_start_times: Dict[str, float] = {}
        self.avg_processing_time = 0.0
        self.last_scale_time = 0.0
        self.scale_check_interval = 30.0  # Seconds between scaling checks

        # System load monitoring (CPU and RAM)
        self._cpu_history: List[float] = []
        self._ram_history: List[float] = []
        self._history_max_size = 10  # Keep last 10 readings
        self._current_cpu_usage = 0.0
        self._current_ram_usage = 0.0

        # Scaling decisions log
        self._scaling_decisions: List[Dict[str, Any]] = []
        self._max_scaling_log = 50

        # Completion timing metrics
        self.completion_times: List[float] = []
        self.max_completion_time = 0.0
        self.min_completion_time = float('inf')

        # Context tracking (recording vs post-stop)
        self.recording_active = True
        self.tasks_during_recording = 0
        self.tasks_after_recording = 0

        # Completion callbacks
        self.completion_callbacks: List[Callable[[Dict[str, Any]], None]] = []

        logger.info(f"Initialized EnhancementWorkerPool: {num_workers} workers, scaling={dynamic_scaling}, "
                   f"cpu_threshold={cpu_usage_threshold}, ram_threshold={ram_usage_threshold}")

    async def process_segment(self, segment: Dict[str, Any],
                            processor: 'EnhancementProcessor',
                            retry_count: int = 0) -> Dict[str, Any]:
        """
        Process a segment using the enhancement processor.

        Args:
            segment: Segment dictionary to process
            processor: EnhancementProcessor instance to use for processing
            retry_count: Current retry attempt (internal use)

        Returns:
            Dict[str, Any]: Enhanced segment with results
        """
        segment_id = segment.get('id', 'unknown')
        start_time = time.time()
        self.task_start_times[segment_id] = start_time

        # Track context (during recording vs after stop)
        is_during_recording = self.recording_active
        context_str = "during recording" if is_during_recording else "after recording stopped"

        if is_during_recording:
            self.tasks_during_recording += 1
        else:
            self.tasks_after_recording += 1

        logger.info(f"[ENHANCEMENT PROCESS] Starting segment {segment_id} ({context_str}, retry: {retry_count})")

        # Check if pool is running
        if not self.is_running:
            logger.warning(f"[ENHANCEMENT PROCESS] Worker pool not running, skipping segment {segment_id}")
            return {
                'id': segment_id,
                'error': 'Worker pool not running',
                'original_text': segment.get('text', ''),
                'confidence': segment.get('confidence'),
                'enhanced': False
            }

        # Check if dynamic scaling is needed
        if self.dynamic_scaling:
            await self._maybe_scale_workers()

        self.pending_tasks += 1

        loop = asyncio.get_event_loop()

        try:
            logger.debug(f"Processing segment {segment_id} {context_str} (retry {retry_count}/{self.max_retries})")

            enhanced = await loop.run_in_executor(
                self.executor,
                processor.enhance,
                segment
            )

            # Update metrics
            processing_time = time.time() - start_time
            self._update_completion_metrics(processing_time)
            self._update_avg_processing_time(processing_time)
            self.completed_tasks += 1
            self.pending_tasks -= 1

            # Remove from active tasks tracking
            if segment_id in self.active_tasks:
                del self.active_tasks[segment_id]

            # Mark as enhanced with bold formatting
            if enhanced:
                enhanced['enhanced'] = enhanced.get('enhanced', True)
                enhanced['is_enhanced'] = True  # Additional flag for UI
                enhanced['context'] = 'during_recording' if is_during_recording else 'post_recording'
                enhanced['processing_time'] = processing_time

            logger.info(
                f"Completed segment {segment_id} {context_str} in {processing_time:.2f}s "
                f"(avg: {self.avg_processing_time:.2f}s, enhanced: {enhanced.get('enhanced', False)})"
            )

            # Trigger completion callbacks
            await self._notify_completion_callbacks(enhanced)

            return enhanced

        except Exception as e:
            self.pending_tasks -= 1
            error_msg = str(e)
            logger.error(f"Error processing segment {segment_id} {context_str}: {error_msg}")

            # Retry logic with graceful degradation
            if retry_count < self.max_retries:
                self.retry_count += 1
                logger.info(f"Retrying segment {segment_id} (attempt {retry_count + 1}/{self.max_retries})")
                await asyncio.sleep(0.5 * (retry_count + 1))  # Exponential backoff
                return await self.process_segment(segment, processor, retry_count + 1)
            else:
                self.failed_tasks += 1
                logger.error(f"Max retries exceeded for segment {segment_id}, returning original")

                # Remove from active tasks tracking
                if segment_id in self.active_tasks:
                    del self.active_tasks[segment_id]

                # Graceful degradation: return original segment with error flag
                return {
                    'id': segment_id,
                    'error': error_msg,
                    'original_text': segment.get('text', ''),
                    'enhanced_text': segment.get('text', ''),  # Fallback to original
                    'confidence': segment.get('confidence'),
                    'enhanced': False,
                    'is_enhanced': False,
                    'graceful_degradation': True,
                    'context': 'during_recording' if is_during_recording else 'post_recording'
                }
        finally:
            if segment_id in self.task_start_times:
                del self.task_start_times[segment_id]
    
    async def process_segment_async(self, segment: Dict[str, Any],
                                   processor: 'EnhancementProcessor') -> asyncio.Task:
        """
        Process a segment asynchronously and return the task.
        
        Args:
            segment: Segment dictionary to process
            processor: EnhancementProcessor instance to use for processing
            
        Returns:
            asyncio.Task: Task that will complete with the enhanced segment
        """
        segment_id = segment.get('id', 'unknown')
        
        # Create async task
        task = asyncio.create_task(self.process_segment(segment, processor))
        
        # Track active task
        self.active_tasks[segment_id] = task
        self.async_tasks.append(task)
        
        # Clean up completed tasks periodically
        self._cleanup_completed_tasks()
        
        return task
    
    async def _notify_completion_callbacks(self, result: Dict[str, Any]) -> None:
        """
        Notify all registered completion callbacks.
        
        Args:
            result: Enhancement result dictionary
        """
        for callback in self.completion_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(result)
                else:
                    callback(result)
            except Exception as e:
                logger.error(f"Error in completion callback: {e}")
    
    def add_completion_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """
        Register a callback to be called when enhancement completes.
        
        Args:
            callback: Function to call with enhancement result
        """
        self.completion_callbacks.append(callback)
        logger.debug(f"Added completion callback (total: {len(self.completion_callbacks)})")
    
    def remove_completion_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """
        Remove a completion callback.
        
        Args:
            callback: Function to remove
        """
        if callback in self.completion_callbacks:
            self.completion_callbacks.remove(callback)
            logger.debug(f"Removed completion callback (remaining: {len(self.completion_callbacks)})")
    
    async def _maybe_scale_workers(self) -> None:
        """
        Dynamically scale workers based on system load (CPU and RAM).
        Only scales if enough time has passed since last scale operation.
        Uses smoothed metrics from history to avoid reactive scaling.
        """
        async with self._scaling_lock:
            now = time.time()
            time_since_last_scale = now - self.last_scale_time
            
            # Only check scaling at configured interval
            if time_since_last_scale < self.scale_check_interval:
                return
            
            if self.worker_scaling_algorithm == "none":
                return
            
            # Collect current system metrics
            cpu_usage = psutil.cpu_percent(interval=0.1)
            ram_usage = psutil.virtual_memory().percent / 100.0
            
            # Update history for smoothing
            self._update_resource_history(cpu_usage, ram_usage)
            
            # Get smoothed averages
            avg_cpu = self._get_avg_cpu_usage()
            avg_ram = self._get_avg_ram_usage()
            
            # Store current readings
            self._current_cpu_usage = cpu_usage
            self._current_ram_usage = ram_usage
            
            # Determine scaling action based on algorithm
            scaling_action = self._determine_scaling_action(avg_cpu, avg_ram)
            
            if scaling_action['action'] == 'scale_down':
                new_worker_count = max(self.min_workers, self.num_workers - scaling_action['delta'])
                await self._scale_workers(new_worker_count)
                self._log_scaling_decision('scale_down', new_worker_count, cpu_usage, ram_usage, scaling_action['reason'])
                
            elif scaling_action['action'] == 'scale_up':
                new_worker_count = min(self.max_workers, self.num_workers + scaling_action['delta'])
                await self._scale_workers(new_worker_count)
                self._log_scaling_decision('scale_up', new_worker_count, cpu_usage, ram_usage, scaling_action['reason'])
    
    def _update_resource_history(self, cpu_usage: float, ram_usage: float) -> None:
        """
        Update resource usage history for trend analysis.
        
        Args:
            cpu_usage: Current CPU usage (0.0-1.0)
            ram_usage: Current RAM usage (0.0-1.0)
        """
        self._cpu_history.append(cpu_usage)
        self._ram_history.append(ram_usage)
        
        # Trim to max size
        if len(self._cpu_history) > self._history_max_size:
            self._cpu_history = self._cpu_history[-self._history_max_size:]
        if len(self._ram_history) > self._history_max_size:
            self._ram_history = self._ram_history[-self._history_max_size:]
    
    def _get_avg_cpu_usage(self) -> float:
        """Get smoothed average CPU usage from history."""
        if not self._cpu_history:
            return 0.0
        return sum(self._cpu_history) / len(self._cpu_history)
    
    def _get_avg_ram_usage(self) -> float:
        """Get smoothed average RAM usage from history."""
        if not self._ram_history:
            return 0.0
        return sum(self._ram_history) / len(self._ram_history)
    
    def _determine_scaling_action(self, avg_cpu: float, avg_ram: float) -> Dict[str, Any]:
        """
        Determine scaling action based on resource metrics and algorithm.
        
        Args:
            avg_cpu: Smoothed CPU usage (0-100)
            avg_ram: Smoothed RAM usage (0.0-1.0)
            
        Returns:
            Dict with 'action', 'delta', and 'reason' keys
        """
        # Default: no action
        result = {'action': 'none', 'delta': 0, 'reason': 'Within thresholds'}
        
        # Check for resource pressure (scale down conditions)
        cpu_pressure = avg_cpu > (self.cpu_usage_threshold * 100)
        ram_pressure = avg_ram > self.ram_usage_threshold
        
        if cpu_pressure and ram_pressure:
            # Both resources under pressure - aggressive scale down
            delta = 2 if self.worker_scaling_algorithm == "adaptive" else 1
            result = {
                'action': 'scale_down',
                'delta': delta,
                'reason': f'High resource pressure (CPU: {avg_cpu:.1f}%, RAM: {avg_ram*100:.1f}%)'
            }
        elif cpu_pressure:
            # CPU pressure - moderate scale down
            result = {
                'action': 'scale_down',
                'delta': 1,
                'reason': f'High CPU usage ({avg_cpu:.1f}% > {self.cpu_usage_threshold * 100:.0f}%)'
            }
        elif ram_pressure:
            # RAM pressure - moderate scale down
            result = {
                'action': 'scale_down',
                'delta': 1,
                'reason': f'High RAM usage ({avg_ram*100:.1f}% > {self.ram_usage_threshold * 100:.0f}%)'
            }
        elif avg_cpu < (self.cpu_usage_threshold * 100 * 0.7) and avg_ram < (self.ram_usage_threshold * 0.7):
            # Low resource usage - scale up opportunity
            if self.pending_tasks > self.num_workers:
                # There's queue pressure, scale up
                delta = 2 if self.worker_scaling_algorithm == "adaptive" else 1
                result = {
                    'action': 'scale_up',
                    'delta': delta,
                    'reason': f'Low resource usage with pending tasks (CPU: {avg_cpu:.1f}%, RAM: {avg_ram*100:.1f}%)'
                }
        
        return result
    
    def _log_scaling_decision(self, action: str, new_count: int, cpu: float, ram: float, reason: str) -> None:
        """
        Log a scaling decision for monitoring and debugging.
        
        Args:
            action: 'scale_up' or 'scale_down'
            new_count: New worker count
            cpu: CPU usage at decision time
            ram: RAM usage at decision time
            reason: Human-readable reason for the decision
        """
        decision = {
            'timestamp': time.time(),
            'action': action,
            'from_workers': self.num_workers,
            'to_workers': new_count,
            'cpu_usage': cpu,
            'ram_usage': ram,
            'reason': reason
        }
        
        self._scaling_decisions.append(decision)
        
        # Trim log
        if len(self._scaling_decisions) > self._max_scaling_log:
            self._scaling_decisions = self._scaling_decisions[-self._max_scaling_log:]
        
        # Log to logger
        direction = "up" if action == "scale_up" else "down"
        logger.info(f"[SCALING] Scaled {direction}: {self.num_workers} -> {new_count} workers | "
                   f"CPU: {cpu:.1f}% | RAM: {ram*100:.1f}% | Reason: {reason}")
    
    async def _scale_workers(self, new_worker_count: int) -> None:
        """
        Scale the worker pool to a new worker count.
        
        Args:
            new_worker_count: New number of workers
        """
        if new_worker_count == self.num_workers:
            return
        
        self.last_scale_time = time.time()
        
        # Shutdown old executor
        old_executor = self.executor
        old_executor.shutdown(wait=False)
        
        # Create new executor with new worker count
        self.num_workers = new_worker_count
        self.executor = ThreadPoolExecutor(max_workers=new_worker_count)
        
        # Give old executor time to finish
        await asyncio.sleep(0.1)
    
    def _update_avg_processing_time(self, processing_time: float) -> None:
        """
        Update average processing time using exponential moving average.

        Args:
            processing_time: Processing time for the last task
        """
        if self.avg_processing_time == 0:
            self.avg_processing_time = processing_time
        else:
            # EMA with alpha = 0.1
            self.avg_processing_time = 0.9 * self.avg_processing_time + 0.1 * processing_time

    def _update_completion_metrics(self, processing_time: float) -> None:
        """
        Update completion time metrics.

        Args:
            processing_time: Processing time for the last task
        """
        self.completion_times.append(processing_time)

        # Keep only last 100 completion times to avoid memory growth
        if len(self.completion_times) > 100:
            self.completion_times = self.completion_times[-100:]

        # Update min/max
        self.max_completion_time = max(self.max_completion_time, processing_time)
        self.min_completion_time = min(self.min_completion_time, processing_time)

    def set_recording_state(self, is_recording: bool) -> None:
        """
        Set the recording state for context tracking.

        Args:
            is_recording: True if recording is active, False if stopped
        """
        old_state = "active" if self.recording_active else "stopped"
        self.recording_active = is_recording
        new_state = "active" if self.recording_active else "stopped"
        logger.debug(f"Recording state changed: {old_state} -> {new_state}")

    def get_completion_metrics(self) -> Dict[str, Any]:
        """
        Get completion timing metrics.

        Returns:
            Dict[str, Any]: Dictionary with completion timing statistics
        """
        if not self.completion_times:
            return {
                'avg_completion_time': 0.0,
                'max_completion_time': 0.0,
                'min_completion_time': 0.0,
                'total_completions': 0
            }

        return {
            'avg_completion_time': sum(self.completion_times) / len(self.completion_times),
            'max_completion_time': self.max_completion_time,
            'min_completion_time': self.min_completion_time if self.min_completion_time != float('inf') else 0.0,
            'total_completions': len(self.completion_times),
            'tasks_during_recording': self.tasks_during_recording,
            'tasks_after_recording': self.tasks_after_recording
        }
    
    def _cleanup_completed_tasks(self) -> None:
        """Remove completed tasks from the tracking list."""
        self.async_tasks = [task for task in self.async_tasks if not task.done()]
    
    async def wait_for_completion(self, timeout: float = 30.0) -> None:
        """
        Wait for all pending tasks to complete.
        
        Args:
            timeout: Maximum time to wait in seconds (default: 30)
        """
        if not self.active_tasks:
            return
        
        logger.info(f"Waiting for {len(self.active_tasks)} pending tasks to complete...")
        
        try:
            await asyncio.wait_for(
                asyncio.gather(*self.active_tasks.values(), return_exceptions=True),
                timeout=timeout
            )
            logger.info("All tasks completed successfully")
        except asyncio.TimeoutError:
            logger.warning(f"Timeout waiting for tasks after {timeout}s")
            # Cancel remaining tasks
            for task in self.active_tasks.values():
                if not task.done():
                    task.cancel()
    
    def start(self) -> None:
        """Start the worker pool."""
        if self.is_running:
            logger.warning("Worker pool already running")
            return
            
        self.is_running = True
        self.pending_tasks = 0
        self.completed_tasks = 0
        self.failed_tasks = 0
        self.retry_count = 0
        logger.info(f"Started EnhancementWorkerPool with {self.num_workers} workers")
    
    async def stop(self, timeout: float = 5.0) -> None:
        """
        Stop the worker pool and clean up resources.
        
        Args:
            timeout: Maximum time to wait for pending tasks (default: 5)
        """
        if not self.is_running:
            return
            
        self.is_running = False
        logger.info("Stopping EnhancementWorkerPool...")
        
        # Wait for pending tasks to complete
        if self.active_tasks:
            await self.wait_for_completion(timeout=timeout)
        
        # Shutdown executor
        self.executor.shutdown(wait=True)
        self.active_tasks.clear()
        self.async_tasks.clear()
        
        logger.info(f"Stopped EnhancementWorkerPool (completed: {self.completed_tasks}, failed: {self.failed_tasks}, retries: {self.retry_count})")
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current worker pool status.

        Returns:
            Dict[str, Any]: Dictionary with worker pool statistics
        """
        cpu_usage = psutil.cpu_percent(interval=0.1) if self.dynamic_scaling else 0.0
        ram_info = psutil.virtual_memory() if self.dynamic_scaling else None
        completion_metrics = self.get_completion_metrics()
        resource_metrics = self.get_system_metrics()

        return {
            'num_workers': self.num_workers,
            'min_workers': self.min_workers,
            'max_workers': self.max_workers,
            'is_running': self.is_running,
            'recording_active': self.recording_active,
            'pending_tasks': self.pending_tasks,
            'completed_tasks': self.completed_tasks,
            'failed_tasks': self.failed_tasks,
            'retry_count': self.retry_count,
            'active_tasks': len(self.active_tasks),
            'dynamic_scaling': self.dynamic_scaling,
            'cpu_usage': cpu_usage,
            'cpu_usage_threshold': self.cpu_usage_threshold,
            'ram_usage': ram_info.percent / 100.0 if ram_info else 0.0,
            'ram_usage_threshold': self.ram_usage_threshold,
            'avg_processing_time': self.avg_processing_time,
            'active_threads': len(self.executor._threads) if hasattr(self.executor, '_threads') else 0,
            'completion_metrics': completion_metrics,
            'resource_metrics': resource_metrics
        }
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """
        Get current system resource metrics for performance monitoring.
        
        Returns:
            Dict[str, Any]: Dictionary with CPU, RAM, and system metrics
        """
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            cpu_count = psutil.cpu_count()
            cpu_freq = psutil.cpu_freq()
            
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            return {
                'cpu': {
                    'usage_percent': cpu_percent,
                    'count': cpu_count,
                    'frequency_mhz': cpu_freq.current if cpu_freq else 0,
                    'avg_usage': self._get_avg_cpu_usage()
                },
                'ram': {
                    'total_gb': memory.total / (1024**3),
                    'available_gb': memory.available / (1024**3),
                    'used_gb': memory.used / (1024**3),
                    'usage_percent': memory.percent,
                    'avg_usage': self._get_avg_ram_usage() * 100
                },
                'swap': {
                    'total_gb': swap.total / (1024**3),
                    'used_gb': swap.used / (1024**3),
                    'usage_percent': swap.percent
                },
                'thresholds': {
                    'cpu_threshold': self.cpu_usage_threshold,
                    'ram_threshold': self.ram_usage_threshold,
                    'cpu_pressure': cpu_percent > (self.cpu_usage_threshold * 100),
                    'ram_pressure': memory.percent / 100 > self.ram_usage_threshold
                }
            }
        except Exception as e:
            logger.error(f"Error getting system metrics: {e}")
            return {
                'cpu': {'usage_percent': 0, 'count': 0, 'frequency_mhz': 0, 'avg_usage': 0},
                'ram': {'total_gb': 0, 'available_gb': 0, 'used_gb': 0, 'usage_percent': 0, 'avg_usage': 0},
                'swap': {'total_gb': 0, 'used_gb': 0, 'usage_percent': 0},
                'thresholds': {
                    'cpu_threshold': self.cpu_usage_threshold,
                    'ram_threshold': self.ram_usage_threshold,
                    'cpu_pressure': False,
                    'ram_pressure': False
                },
                'error': str(e)
            }
    
    def get_worker_performance_metrics(self) -> Dict[str, Any]:
        """
        Get worker performance metrics for monitoring.
        
        Returns:
            Dict[str, Any]: Dictionary with worker performance statistics
        """
        return {
            'current_workers': self.num_workers,
            'worker_bounds': {
                'min': self.min_workers,
                'max': self.max_workers
            },
            'task_statistics': {
                'pending': self.pending_tasks,
                'completed': self.completed_tasks,
                'failed': self.failed_tasks,
                'total_retries': self.retry_count
            },
            'performance': {
                'avg_processing_time_sec': self.avg_processing_time,
                'success_rate': self.completed_tasks / max(1, self.completed_tasks + self.failed_tasks),
                'throughput_per_min': self._calculate_throughput()
            },
            'scaling': {
                'algorithm': self.worker_scaling_algorithm,
                'dynamic_scaling_enabled': self.dynamic_scaling,
                'recent_decisions': self._scaling_decisions[-5:] if self._scaling_decisions else []
            }
        }
    
    def _calculate_throughput(self) -> float:
        """Calculate tasks completed per minute."""
        if not self.completion_times:
            return 0.0
        
        # Use recent completion times to estimate throughput
        recent_count = min(len(self.completion_times), 20)
        if recent_count < 2:
            return 0.0
        
        # Estimate based on average processing time
        avg_time = sum(self.completion_times[-recent_count:]) / recent_count
        if avg_time > 0:
            return 60.0 / avg_time  # Tasks per minute per worker
        return 0.0
    
    def get_response_time_metrics(self) -> Dict[str, Any]:
        """
        Get response time tracking metrics.
        
        Returns:
            Dict[str, Any]: Dictionary with response time statistics
        """
        if not self.completion_times:
            return {
                'avg_response_time_ms': 0,
                'min_response_time_ms': 0,
                'max_response_time_ms': 0,
                'p50_response_time_ms': 0,
                'p95_response_time_ms': 0,
                'p99_response_time_ms': 0,
                'sample_count': 0
            }
        
        sorted_times = sorted(self.completion_times)
        count = len(sorted_times)
        
        def percentile(data: List[float], p: float) -> float:
            """Calculate the p-th percentile of data."""
            if not data:
                return 0.0
            k = (len(data) - 1) * p / 100
            f = int(k)
            c = f + 1 if f + 1 < len(data) else f
            return data[f] + (k - f) * (data[c] - data[f]) if c != f else data[f]
        
        return {
            'avg_response_time_ms': sum(sorted_times) / count * 1000,
            'min_response_time_ms': sorted_times[0] * 1000,
            'max_response_time_ms': sorted_times[-1] * 1000,
            'p50_response_time_ms': percentile(sorted_times, 50) * 1000,
            'p95_response_time_ms': percentile(sorted_times, 95) * 1000,
            'p99_response_time_ms': percentile(sorted_times, 99) * 1000,
            'sample_count': count
        }
    
    def check_performance_thresholds(self) -> Dict[str, Any]:
        """
        Check if performance metrics are within acceptable thresholds.
        
        Returns:
            Dict[str, Any]: Dictionary with threshold check results
        """
        warnings = []
        critical = []
        
        # Check CPU usage
        avg_cpu = self._get_avg_cpu_usage()
        if avg_cpu > self.cpu_usage_threshold * 100:
            critical.append(f"CPU usage critical: {avg_cpu:.1f}% (threshold: {self.cpu_usage_threshold * 100:.0f}%)")
        elif avg_cpu > self.cpu_usage_threshold * 100 * 0.9:
            warnings.append(f"CPU usage high: {avg_cpu:.1f}%")
        
        # Check RAM usage
        avg_ram = self._get_avg_ram_usage()
        if avg_ram > self.ram_usage_threshold:
            critical.append(f"RAM usage critical: {avg_ram * 100:.1f}% (threshold: {self.ram_usage_threshold * 100:.0f}%)")
        elif avg_ram > self.ram_usage_threshold * 0.9:
            warnings.append(f"RAM usage high: {avg_ram * 100:.1f}%")
        
        # Check failure rate
        total_tasks = self.completed_tasks + self.failed_tasks
        if total_tasks > 0:
            failure_rate = self.failed_tasks / total_tasks
            if failure_rate > 0.1:
                critical.append(f"High failure rate: {failure_rate * 100:.1f}%")
            elif failure_rate > 0.05:
                warnings.append(f"Elevated failure rate: {failure_rate * 100:.1f}%")
        
        return {
            'healthy': len(critical) == 0,
            'warnings': warnings,
            'critical': critical,
            'cpu_status': 'critical' if avg_cpu > self.cpu_usage_threshold * 100 else ('warning' if avg_cpu > self.cpu_usage_threshold * 100 * 0.9 else 'ok'),
            'ram_status': 'critical' if avg_ram > self.ram_usage_threshold else ('warning' if avg_ram > self.ram_usage_threshold * 0.9 else 'ok')
        }


class EnhancementProcessor:
    """Large model inference engine for segment enhancement using whisper.cpp."""
    
    def __init__(self, config: EnhancementConfig):
        """
        Initialize the enhancement processor with configuration.
        
        Args:
            config: EnhancementConfig instance with model size and settings
        """
        self.config = config
        self.model_name = config.enhancement_model
        self.model = None
        self._model_loaded = False
        
        # Import WhisperTranscriptionEngine for model management
        from .engine import WhisperTranscriptionEngine
        
        # Create engine with enhancement model size
        self.engine = WhisperTranscriptionEngine(model_size=self.model_name)
        
        self.load_model()
    
    def load_model(self):
        """Load the Whisper model for enhancement using whisper.cpp."""
        try:
            logger.info(f"Loading Whisper {self.model_name} model for enhancement...")
            self.engine.load_model()
            self.model = self.engine
            self._model_loaded = True
            logger.info(f"Successfully loaded Whisper {self.model_name} model")
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            self._model_loaded = False
    
    def is_model_loaded(self) -> bool:
        """Check if the enhancement model has been loaded.
        
        Returns:
            True if model is loaded and ready for enhancement
        """
        return self._model_loaded and self.model is not None
    
    def transcribe_segment(self, audio: np.ndarray) -> Dict[str, Any]:
        """
        Transcribe audio segment using large Whisper model for enhancement.
        
        Args:
            audio: Audio samples as float32 numpy array (mono, 16kHz)
            
        Returns:
            Dict[str, Any]: Enhanced transcription segment
        """
        if not self.is_model_loaded():
            logger.warning("Enhancement model not loaded")
            return {
                'text': '',
                'confidence': 0,
                'enhanced': False,
                'error': 'Enhancement model not available'
            }
        
        try:
            # Use the transcription engine to enhance the audio
            segments = self.engine.transcribe_chunk(audio)
            
            if segments and len(segments) > 0:
                segment = segments[0]
                return {
                    'text': segment.text,
                    'confidence': segment.confidence,
                    'start': segment.start,
                    'end': segment.end,
                    'words': [{'text': w.text, 'start': w.start, 'end': w.end, 'confidence': w.confidence} 
                             for w in segment.words] if segment.words else [],
                    'enhanced': True,
                    'model': self.model_name
                }
            else:
                return {
                    'text': '',
                    'confidence': 0,
                    'enhanced': False,
                    'error': 'No transcription produced'
                }
                
        except Exception as e:
            logger.error(f"Error transcribing segment for enhancement: {e}")
            return {
                'text': '',
                'confidence': 0,
                'enhanced': False,
                'error': str(e)
            }
    
    def enhance(self, segment: Dict[str, Any], audio: Optional[np.ndarray] = None) -> Dict[str, Any]:
        """
        Enhance the segment using large Whisper model.
        
        Args:
            segment: Segment dictionary containing text, confidence, and optionally audio
            audio: Optional audio array for enhancement (transcribe_segment if provided)
            
        Returns:
            Dict[str, Any]: Enhanced segment with improved transcription
        """
        if not self.is_model_loaded():
            # If model not available, return original segment
            return {
                'id': segment.get('id'),
                'original_text': segment.get('text', ''),
                'enhanced_text': segment.get('text', ''),
                'original_confidence': segment.get('confidence'),
                'confidence': segment.get('confidence'),
                'enhanced': False,
                'message': 'Enhancement model not available'
            }
        
        try:
            # If audio is provided, use transcribe_segment
            if audio is not None:
                result = self.transcribe_segment(audio)
                
                enhanced_segment = {
                    'id': segment.get('id'),
                    'original_text': segment.get('text', ''),
                    'enhanced_text': result.get('text', segment.get('text', '')),
                    'original_confidence': segment.get('confidence'),
                    'confidence': result.get('confidence', segment.get('confidence')),
                    'enhanced': result.get('enhanced', False),
                    'model': self.model_name,
                    'start': result.get('start', 0.0),
                    'end': result.get('end', 0.0)
                }
                
                if result.get('error'):
                    enhanced_segment['error'] = result['error']
                
                logger.debug(f"Enhanced segment {segment.get('id')} with {self.model_name} model")
                return enhanced_segment
            else:
                # If no audio, just return original segment
                return {
                    'id': segment.get('id'),
                    'original_text': segment.get('text', ''),
                    'enhanced_text': segment.get('text', ''),
                    'original_confidence': segment.get('confidence'),
                    'confidence': segment.get('confidence'),
                    'enhanced': False,
                    'message': 'No audio provided for enhancement'
                }
                
        except Exception as e:
            logger.error(f"Error enhancing segment {segment.get('id')}: {e}")
            return {
                'id': segment.get('id'),
                'original_text': segment.get('text', ''),
                'enhanced_text': segment.get('text', ''),
                'original_confidence': segment.get('confidence'),
                'confidence': segment.get('confidence'),
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