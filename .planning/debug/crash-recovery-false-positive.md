# Crash Recovery False Positive - Investigation

## Problem Statement
Crash recovery prompts on every startup, even when no crash leftovers exist.

## Investigation Trace

### 1. Recovery Detection Flow
**File:** `src/metamemory/main.py:16-28`
- `check_and_offer_recovery()` called at startup (line 124)
- Calls `has_partial_recordings(recordings_dir)` (line 28)
- If True, shows recovery dialog

### 2. Partial Recording Detection
**File:** `src/metamemory/audio/storage/recovery.py:151-160`
```python
def has_partial_recordings(recordings_dir: Path) -> bool:
    """Check if there are any partial recordings needing recovery."""
    return len(find_part_files(recordings_dir)) > 0
```

**File:** `src/metamemory/audio/storage/recovery.py:15-36`
```python
def find_part_files(recordings_dir: Path) -> List[Path]:
    """Find all .pcm.part files in the recordings directory."""
    return sorted(recordings_dir.glob("*.pcm.part"))
```

**Issue:** The detection logic simply looks for ANY `.pcm.part` files, without distinguishing between:
- Actual crash leftovers (incomplete recordings)
- Successfully completed recordings (finalized but not cleaned up)

### 3. Normal Recording Finalization Flow
**File:** `src/metamemory/audio/session.py:326-329`
```python
wav_path = finalize_stem(
    stem=self._stem,
    recordings_dir=output_dir or get_recordings_dir(),
)
```

**File:** `src/metamemory/audio/storage/wav_finalize.py:79-113`
```python
def finalize_stem(
    stem: str,
    recordings_dir: Path,
    delete_part: bool = False,  # ← DEFAULT IS FALSE
) -> Path:
    """Finalize a recording by stem name."""
    # ... creates WAV file ...
    result = finalize_part_to_wav(part_path, wav_path)

    if delete_part:  # ← NEVER EXECUTED BY DEFAULT
        metadata_path = part_path.with_suffix(".part.json")
        part_path.unlink(missing_ok=True)
        metadata_path.unlink(missing_ok=True)

    return result
```

## Root Cause Analysis

### What happens during normal operation:
1. Recording starts, creates `recording-xxx.pcm.part` and `recording-xxx.pcm.part.json`
2. Recording stops, `finalize_stem()` is called with default `delete_part=False`
3. WAV file created: `recording-xxx.wav`
4. **BUT `.pcm.part` files are NOT deleted** - they remain in the directory

### What happens on next startup:
1. App launches, calls `check_and_offer_recovery()`
2. `has_partial_recordings()` finds the old `.pcm.part` files
3. Prompts user for recovery (FALSE POSITIVE)
4. User either:
   - Recovers (creates duplicate WAV: `recording-xxx.recovered.wav`)
   - Declines (`.pcm.part` files remain)
5. Cycle repeats on every startup

## Evidence from Recovery Code

**File:** `src/metamemory/audio/storage/recovery.py:80-90`
```python
if delete_original:
    # Delete original files
    part_path.unlink(missing_ok=True)
    metadata_path.unlink(missing_ok=True)
else:
    # Backup original files
    part_backup = recordings_dir / f"{stem}.pcm.part{backup_suffix}"
    metadata_backup = recordings_dir / f"{stem}.pcm.part.json{backup_suffix}"

    shutil.move(str(part_path), str(part_backup))
    shutil.move(str(metadata_path), str(metadata_backup))
```

The recovery code DOES clean up `.pcm.part` files, but only after recovery, not during normal finalization.

## Impact Assessment

**Severity:** Major - UX breaking bug
- Recovery dialog appears every launch even when no crash occurred
- Users may create duplicate `.recovered.wav` files
- Clutters recordings directory with stale `.pcm.part` files
- Confuses users about whether app crashed or not

## Solution Options

### Option 1: Delete `.pcm.part` after successful finalization (RECOMMENDED)
**Change:** `src/metamemory/audio/session.py:326-329`
```python
wav_path = finalize_stem(
    stem=self._stem,
    recordings_dir=output_dir or get_recordings_dir(),
    delete_part=True,  # ← ADD THIS PARAMETER
)
```

**Pros:**
- Clean separation: `.pcm.part` only exists for active or crashed recordings
- Detection logic works correctly
- No directory clutter

**Cons:**
- None identified

### Option 2: Detect if corresponding WAV exists
**Change:** `src/metamemory/audio/storage/recovery.py:15-36`
```python
def find_part_files(recordings_dir: Path) -> List[Path]:
    """Find all .pcm.part files WITHOUT corresponding .wav files."""
    part_files = []
    for part_path in recordings_dir.glob("*.pcm.part"):
        wav_path = part_path.with_suffix(".wav")
        if not wav_path.exists():
            part_files.append(part_path)
    return sorted(part_files)
```

**Pros:**
- Keeps `.pcm.part` files for potential debugging
- Non-breaking change

**Cons:**
- Still leaves clutter
- `.pcm.part` files accumulate over time
- More complex detection logic

## Recommended Fix

**Option 1** is the correct solution because:
1. `.pcm.part` files are temporary working files, not meant to persist
2. The WAV file is the final, complete recording
3. Matches the pattern used in recovery (which deletes originals by default)
4. Simpler and cleaner design

## Files to Modify

1. **src/metamemory/audio/session.py:326-329** - Add `delete_part=True` parameter
2. (Optional) Add documentation about cleanup behavior

## Testing Strategy

1. Start recording, stop normally
2. Verify `.pcm.part` and `.part.json` files are deleted
3. Only `.wav` file remains
4. Restart app - no recovery prompt
5. Simulate crash (kill app during recording)
6. Restart app - recovery prompt appears correctly
