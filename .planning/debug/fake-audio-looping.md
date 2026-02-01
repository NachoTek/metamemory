# Fake Audio Looping Bug Investigation

## Problem
User reported that `python -m metamemory.audio.cli record --fake tests/fixtures/test_audio.wav --seconds 5` creates a 3+ hour recording instead of 5 seconds.

## Setup
- Test file: 7 seconds long
- Expected duration: 5 seconds
- Actual duration: 3 hours 2 min 53 sec
- No progress shown during recording

## Root Cause Analysis

### Primary Issue: Hardcoded `loop=True`
**Location:** `src/metamemory/audio/session.py:367`

```python
source = FakeAudioModule(
    wav_path=source_config.fake_path,
    blocksize=1024,
    queue_size=10,
    loop=True,  # <-- HARDCODED TO TRUE
)
```

When `loop=True`, the fake source continuously generates audio frames from the file in an infinite loop. This causes two problems:

1. The fake source never naturally stops
2. The session's drain loop continues consuming frames

### Secondary Issue: Drain Loop Consumes Active Sources
**Location:** `src/metamemory/audio/session.py:409-426`

The drain loop runs after the main consumer loop exits and continues reading frames:

```python
# Drain remaining frames
for _ in range(50):  # Brief drain period
    ...
    frames = wrapper.read_and_process(timeout=0.01)
    if frames is not None:
        frames_list.append(frames)
    ...
    # Write to disk
```

**The bug:** When the fake source has `loop=True`, the drain loop reads frames on every iteration because the source is still actively generating frames.

**Time calculation:**
- 50 iterations × 0.01s sleep = 0.5s theoretical max
- BUT: each iteration reads ~64ms of audio (1024 frames at 16kHz)
- So drain loop processes ~3.2 seconds of audio during stop()
- This alone doesn't explain 3+ hours, but shows the drain is active

### Why the Recording Extended to 3+ Hours

**Investigation reveals:**
1. The CLI correctly calls `time.sleep(5)` and then `session.stop()`
2. The session sets `_stop_event` and waits for consumer thread to join (5s timeout)
3. The consumer thread exits the main loop when stop event is set
4. The drain loop begins processing remaining frames

**Key insight:** The drain loop continues for 50 iterations, and on each iteration:
- If the fake source still has frames in its internal queue, they get consumed
- If `loop=True` and the source's read thread is still running, new frames appear in the queue
- Each iteration reads up to 1024 frames (64ms at 16kHz)

**However:** Even with worst-case scenario, this should only be a few extra seconds, not 3+ hours.

**Missing piece:** The user's report of "3 hours 2 min 53 sec" suggests something else is happening. Possibilities:
- The fake source's internal queue is being pre-filled with many iterations of the file
- There's an interaction with the WAV file reading that causes excessive buffering
- The 7-second file is being read and queued multiple times before the drain

**Hypothesis:** In `_read_loop()`, the fake source opens the WAV file and reads blocks into the internal queue. With `loop=True`, if the queue empties slowly (because consumer is sleeping), the source can queue many cycles of the 7-second file. During stop(), the drain loop then consumes all these queued frames.

**Calculation:**
- Queue size: 10 blocks × 1024 frames = 10,240 frames
- At 16kHz: 10,240 / 16,000 = 0.64 seconds of buffered audio
- Still doesn't explain 3+ hours

**Alternative hypothesis:** The WAV file's `readframes()` might be reading more than expected per call, or the file is being opened multiple times in the loop, causing excessive data accumulation.

## Technical Details

### FakeAudioModule Behavior
- Reads WAV file in blocks of `blocksize` (1024 frames)
- Converts to float32 and pushes to internal queue
- With `loop=True`: rewinds file and continues reading at end
- Internal thread runs independently, filling queue even when consumer is slow

### AudioSession Stop Sequence
1. `session.stop()` called
2. `_stop_event.set()`
3. `_consumer_thread.join(timeout=5.0)` waits for thread
4. Consumer thread exits main loop when stop event set
5. Consumer thread runs drain loop (50 iterations)
6. Sources stopped
7. Writer closed and WAV finalized

### Race Condition
The fake source's `_read_loop` thread and the session's consumer thread are both accessing the queue during stop():
- Consumer drain loop reads frames
- Source thread might still be adding frames (if not stopped yet)
- Sources are only stopped AFTER drain completes (line 314)

**Critical timing issue:** Sources are stopped AFTER the drain loop, not before. This means the drain loop competes with the source's read thread for frames.

## Suggested Fixes

### Fix 1: Add `loop` parameter to SourceConfig
**File:** `src/metamemory/audio/session.py:78-90`

```python
@dataclass
class SourceConfig:
    type: str
    device_id: Optional[int] = None
    gain: float = 1.0
    fake_path: Optional[str] = None
    loop: bool = False  # ADD THIS
```

**File:** `src/metamemory/audio/session.py:363-368`

```python
source = FakeAudioModule(
    wav_path=source_config.fake_path,
    blocksize=1024,
    queue_size=10,
    loop=source_config.loop,  # USE THE PARAMETER
)
```

**File:** `src/metamemory/audio/cli.py:158`

```python
sources.append(SourceConfig(type='fake', fake_path=str(fake_path), loop=False))
```

### Fix 2: Stop Sources Before Drain
**File:** `src/metamemory/audio/session.py:290-315`

Reorder to stop sources first, then drain:

```python
def stop(self) -> Path:
    if self._state != SessionState.RECORDING:
        raise SessionError(f"Cannot stop from state {self._state.name}")
    
    self._state = SessionState.STOPPING
    self._stop_event.set()
    
    # Stop all sources FIRST (so no new frames are generated)
    for wrapper in self._sources:
        wrapper.stop()
    
    # Wait for consumer thread to finish
    if self._consumer_thread:
        self._consumer_thread.join(timeout=5.0)
    
    # Calculate final stats
    if self._start_time:
        self._stats.duration_seconds = time.time() - self._start_time
    
    # Close writer
    if self._writer:
        self._writer.close()
    
    # Finalize to WAV
    if not self._stem:
        raise SessionError("No stem available for finalization")
    
    output_dir = self._config.output_dir if self._config else None
    wav_path = finalize_stem(
        stem=self._stem,
        recordings_dir=output_dir or get_recordings_dir(),
    )
    
    self._state = SessionState.FINALIZED
    
    return wav_path
```

### Fix 3: Limit Drain Duration
**File:** `src/metamemory/audio/session.py:409-426`

Add time limit to drain loop:

```python
# Drain remaining frames
drain_start = time.time()
drain_timeout = 1.0  # Max 1 second drain
for _ in range(50):
    if not self._writer:
        break
    
    # Check drain timeout
    if time.time() - drain_start > drain_timeout:
        break
    
    frames_list = []
    for wrapper in self._sources:
        frames = wrapper.read_and_process(timeout=0.01)
        if frames is not None:
            frames_list.append(frames)
    
    if not frames_list:
        break
    
    mixed = self._mix_frames(frames_list)
    int16_bytes = self._float32_to_int16_bytes(mixed)
    self._writer.write_frames_i16(int16_bytes)
    self._stats.frames_recorded += len(mixed)
```

## Recommended Approach

**Apply fixes in order:**
1. Fix 1 (add `loop` parameter) - Primary fix, addresses root cause
2. Fix 2 (stop sources before drain) - Prevents race condition
3. Fix 3 (limit drain duration) - Safety net to prevent excessive drain

Fix 1 alone should resolve the reported issue, as it allows the CLI to explicitly set `loop=False` when creating the fake source.
