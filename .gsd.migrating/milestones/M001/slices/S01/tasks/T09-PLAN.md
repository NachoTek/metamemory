# T09: Fix CLI fake recording duration

**Slice:** S01 — **Milestone:** M001

## Description

Fix the CLI fake recording duration so `--seconds N` produces an ~N second WAV even when the fake source can emit audio faster than real-time.

Purpose: UAT expects `python -m metamemory.audio.cli record --fake <wav> --seconds 5` to yield an output WAV ~5 seconds long; currently it can produce a 1:1 copy of the full input file.
Output: Session-level frame cap wired from CLI + regression test.
