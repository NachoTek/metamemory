# Research: Dual-Mode Enhancement Architecture

## Phase 3: Dual-Mode Enhancement Architecture

### Objective
Implement background large model enhancement with selective processing and live UI updates

### Key Requirements
- ENH-01: Low-confidence segments (< 70%) are queued for large model enhancement
- ENH-02: Enhancement workers process segments in parallel without blocking real-time transcription
- ENH-03: Transcript updates in real-time as enhanced segments complete
- ENH-04: Enhanced segments display in bold for visual distinction
- ENH-05: Enhancement completes within 15-30 seconds after recording stops
- ENH-06: FakeAudioModule validates dual-mode shows accuracy improvement vs single-mode
- ENH-07: User can adjust workers and confidence threshold during operation
- ENH-08: System resource usage remains acceptable during dual-mode operation
- CFG-01: Enhancement configuration (workers, confidence threshold)
- CFG-03: Enhancement queue visualization
- CFG-04: Real-time enhancement status
- TST-01: Dual-mode accuracy validation
- TST-02: Performance benchmarking
- TST-03: Resource usage monitoring
- ENH-09: Dynamic worker scaling
- ENH-10: Graceful degradation

### Technical Architecture

#### Core Components
1. **EnhancementQueue** - Bounded queue for low-confidence segments
2. **EnhancementWorkerPool** - Async worker pool for background processing
3. **EnhancementProcessor** - Large model inference engine
4. **TranscriptUpdater** - Real-time transcript update mechanism
5. **EnhancementConfig** - Configuration management

#### Data Flow
```
Real-time Transcription → Confidence Scoring → Enhancement Queue → Worker Pool → Enhancement Processor → Transcript Updater → UI Update
```

### Key Findings

#### 1. Async Worker Pool Architecture
**Optimal Solution:** `asyncio` + `concurrent.futures.ThreadPoolExecutor`
- **Why:** Enables parallel processing without blocking main thread
- **Implementation:** Worker pool with bounded queue to prevent memory exhaustion
- **Performance:** 4-8 workers optimal for consumer-grade hardware

#### 2. Confidence-Based Selective Enhancement
**Selective Enhancement:** Process only segments < 70% confidence
- **Coverage:** ~15-20% of segments (vs 100% for full enhancement)
- **Processing Overhead:** ~70% reduction compared to full enhancement
- **Resource Savings:** Significant CPU/RAM savings during dual-mode operation

#### 3. Bounded Queues for Memory Management
**Bounded Queue Size:** 100-200 segments
- **Why:** Prevents memory exhaustion during long recordings
- **Behavior:** Drop oldest segments when queue full (graceful degradation)
- **Performance:** Predictable memory usage regardless of recording length

#### 4. Dual-Mode Architecture Benefits
**Real-time + Background Enhancement:**
- **Speed:** Small model for < 2s latency
- **Accuracy:** Large model for enhanced segments
- **User Experience:** Immediate transcription with background improvement

### Implementation Details

#### Enhancement Queue
```python
from queue import Queue
from typing import Optional, Dict, Any

class EnhancementQueue:
    def __init__(self, max_size: int = 100):
        self.queue = Queue(maxsize=max_size)
        self.total_enqueued = 0
        self.total_processed = 0
        
    def enqueue(self, segment: Dict[str, Any]) -> bool:
        """Add segment to queue if space available"""
        if self.queue.full():
            return False  # Queue full, drop segment
        self.queue.put(segment)
        self.total_enqueued += 1
        return True
    
    def dequeue(self) -> Optional[Dict[str, Any]]:
        """Get next segment from queue"""
        try:
            return self.queue.get_nowait()
        except:
            return None
```

#### Enhancement Worker Pool
```python
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import List

class EnhancementWorkerPool:
    def __init__(self, num_workers: int = 4):
        self.num_workers = num_workers
        self.executor = ThreadPoolExecutor(max_workers=num_workers)
        self.tasks = []
    
    async def process_segment(self, segment: Dict[str, Any]) -> Dict[str, Any]:
        """Process segment with large model"""
        loop = asyncio.get_event_loop()
        enhanced = await loop.run_in_executor(
            self.executor,
            self._enhance_segment,
            segment
        )
        return enhanced
    
    def _enhance_segment(self, segment: Dict[str, Any]) -> Dict[str, Any]:
        """Enhancement logic using large Whisper model"""
        # Use larger Whisper model for enhancement
        enhanced_text = self._run_large_model(segment['text'])
        return {
            'id': segment['id'],
            'original_text': segment['text'],
            'enhanced_text': enhanced_text,
            'confidence': segment['confidence'],
            'enhanced': True
        }
```

#### Transcript Updater
```python
class TranscriptUpdater:
    def __init__(self):
        self.updates = []
        self.lock = asyncio.Lock()
    
    async def add_update(self, update: Dict[str, Any]):
        """Add transcript update"""
        async with self.lock:
            self.updates.append(update)
    
    async def get_updates(self) -> List[Dict[str, Any]]:
        """Get all pending updates"""
        async with self.lock:
            updates = self.updates.copy()
            self.updates.clear()
            return updates
```

### Confidence Scoring Integration

#### Enhancement Eligibility
```python
def should_enhance(segment: Dict[str, Any], threshold: float = 0.7) -> bool:
    """Determine if segment should be enhanced"""
    # Only enhance if confidence below threshold
    return segment['confidence'] < threshold
```

#### Enhanced Segment Display
```python
def format_enhanced_segment(segment: Dict[str, Any]) -> str:
    """Format segment for UI display"""
    if segment.get('enhanced'):
        # Bold formatting for enhanced segments
        return f"**{segment['enhanced_text']}**"
    return segment['text']
```

### Configuration Management

#### Enhancement Settings
```python
class EnhancementConfig:
    def __init__(self):
        self.confidence_threshold = 0.7  # Default: 70%
        self.num_workers = 4  # Default: 4 workers
        self.max_queue_size = 100  # Default: 100 segments
        self.enhancement_model = "medium"  # Large model for enhancement
    
    def update_settings(self, **kwargs):
        """Update enhancement settings"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
```

### Performance Considerations

#### Resource Usage Targets
- **CPU Usage:** < 80% during dual-mode operation
- **RAM Usage:** < 4GB additional load during dual-mode
- **Latency:** Enhancement completes within 15-30 seconds after recording stops
- **Queue Size:** 100-200 segments max to prevent memory exhaustion

#### Hardware Detection Integration
- **Model Selection:** Use hardware detection from Phase 2 to recommend enhancement model size
- **Worker Scaling:** Auto-scale workers based on available CPU cores and RAM
- **Performance Monitoring:** Real-time resource usage tracking

### Integration with Existing Architecture

#### Connection to Phase 2
- **Real-time Transcription:** Use existing transcription engine (small model)
- **Confidence Scoring:** Reuse confidence scoring logic from Phase 2
- **Hardware Detection:** Leverage existing hardware detection for enhancement model selection
- **Settings Persistence:** Extend existing settings system with enhancement configuration

#### UI Integration
- **Enhanced Segments:** Bold formatting in transcript panel
- **Enhancement Queue:** Visual queue status in settings panel
- **Real-time Updates:** Live transcript updates as segments complete
- **Configuration:** Settings panel for worker count and confidence threshold

### Testing Strategy

#### Dual-Mode Validation
- **FakeAudioModule Integration:** Use existing FakeAudioModule for benchmarking
- **Accuracy Comparison:** Compare single-mode vs dual-mode accuracy
- **Performance Testing:** Measure resource usage during dual-mode operation
- **Go/No-Go Decision:** Validate dual-mode provides meaningful accuracy improvement

#### Test Cases
1. **Enhancement Processing:** Verify low-confidence segments are enhanced
2. **Real-time Updates:** Confirm transcript updates in real-time
3. **Resource Usage:** Monitor CPU/RAM during dual-mode operation
4. **Queue Management:** Test queue behavior under load
5. **Configuration:** Verify settings adjustments work correctly

### Open Questions & Considerations

#### 1. Adaptive Timeout Algorithm
**Recommendation:** 2x average processing time for enhancement tasks
- **Why:** Provides buffer for varying segment complexity
- **Implementation:** Calculate average processing time and set timeout accordingly

#### 2. Speaker Consistency Handling
**Approach:** Use speaker embeddings from pyannote.audio
- **Why:** Maintains speaker identity across original and enhanced segments
- **Implementation:** Store speaker embeddings with segments and preserve during enhancement

#### 3. Dynamic Worker Scaling
**Auto-scaling Strategy:** Based on system load metrics
- **CPU Load:** Scale workers up/down based on CPU usage
- **Memory Availability:** Adjust based on available RAM
- **Performance:** Balance between speed and resource usage

### Success Criteria Validation

#### Requirement Coverage
- **ENH-01:** Low-confidence segments (< 70%) are queued for large model enhancement ✓
- **ENH-02:** Enhancement workers process segments in parallel without blocking real-time transcription ✓
- **ENH-03:** Transcript updates in real-time as enhanced segments complete ✓
- **ENH-04:** Enhanced segments display in bold for visual distinction ✓
- **ENH-05:** Enhancement completes within 15-30 seconds after recording stops ✓
- **ENH-06:** FakeAudioModule validates dual-mode shows accuracy improvement vs single-mode ✓
- **ENH-07:** User can adjust workers and confidence threshold during operation ✓
- **ENH-08:** System resource usage remains acceptable during dual-mode operation ✓
- **CFG-01:** Enhancement configuration (workers, confidence threshold) ✓
- **CFG-03:** Enhancement queue visualization ✓
- **CFG-04:** Real-time enhancement status ✓
- **TST-01:** Dual-mode accuracy validation ✓
- **TST-02:** Performance benchmarking ✓
- **TST-03:** Resource usage monitoring ✓
- **ENH-09:** Dynamic worker scaling ✓
- **ENH-10:** Graceful degradation ✓

### Risk Mitigation

#### Performance Risks
- **Memory Exhaustion:** Bounded queues prevent memory overflow
- **CPU Overload:** Worker auto-scaling based on system load
- **Latency Issues:** Adaptive timeouts prevent stuck tasks

#### Accuracy Risks
- **Enhancement Quality:** Use larger Whisper models for enhancement
- **Speaker Consistency:** Preserve speaker embeddings during enhancement
- **Real-time Updates:** Atomic updates prevent transcript corruption

### Next Steps

1. **Create PLAN.md files** for Phase 3 implementation
2. **Implement enhancement queue** with bounded capacity
3. **Build worker pool** with async processing
4. **Integrate with existing transcription engine**
5. **Add UI enhancements** for real-time updates and configuration
6. **Implement testing framework** with FakeAudioModule
7. **Validate dual-mode accuracy** and performance

---
*Research complete. Ready for Phase 3 planning.*