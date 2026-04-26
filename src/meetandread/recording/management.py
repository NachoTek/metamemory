"""Recording file enumeration and deletion utilities.

Provides stem-based file discovery and cleanup across the recordings/
and transcripts/ directories. Used by the History tab delete action and
by scrub file management.
"""

import logging
from pathlib import Path
from typing import List, Tuple

from meetandread.audio.storage.paths import (
    get_recordings_dir,
    get_transcripts_dir,
)

logger = logging.getLogger(__name__)


def enumerate_recording_files(stem: str) -> List[Path]:
    """Find all files associated with a recording stem.

    Searches both the recordings/ and transcripts/ directories for files
    whose names start with the given stem. Matches include:

    - ``recordings/{stem}.wav``
    - ``recordings/{stem}.pcm.part``
    - ``recordings/{stem}.pcm.part.json``
    - ``transcripts/{stem}.md``
    - ``transcripts/{stem}_scrub_*.md``  (sidecars from scrub operations)

    Files that do not exist on disk are silently skipped.

    Args:
        stem: Recording stem (e.g. ``"recording-2026-02-01-143045"``).

    Returns:
        List of Path objects for every matching file that exists on disk.
    """
    recordings_dir = get_recordings_dir()
    transcripts_dir = get_transcripts_dir()

    candidates: List[Path] = [
        # Recordings directory
        recordings_dir / f"{stem}.wav",
        recordings_dir / f"{stem}.pcm.part",
        recordings_dir / f"{stem}.pcm.part.json",
        # Transcripts directory
        transcripts_dir / f"{stem}.md",
    ]

    # Scrub sidecars: transcripts/{stem}_scrub_*.md
    if transcripts_dir.exists():
        candidates.extend(transcripts_dir.glob(f"{stem}_scrub_*.md"))

    # Filter to files that actually exist
    found = [p for p in candidates if p.is_file()]

    logger.debug(
        "Enumerated %d files for stem %s: %s",
        len(found),
        stem,
        [p.name for p in found],
    )

    return found


def delete_recording(stem: str) -> Tuple[int, List[str]]:
    """Delete all files associated with a recording stem.

    Uses :func:`enumerate_recording_files` to discover files, then removes
    each one. Missing or already-deleted files are skipped without error.

    Args:
        stem: Recording stem (e.g. ``"recording-2026-02-01-143045"``).

    Returns:
        Tuple of ``(count_deleted, list_of_deleted_paths)`` where each path
        is a string representation of the deleted file.
    """
    files = enumerate_recording_files(stem)
    deleted: List[str] = []

    for path in files:
        try:
            path.unlink()
            deleted.append(str(path))
            logger.info("Deleted recording file: %s", path)
        except OSError as exc:
            logger.warning("Failed to delete %s: %s", path, exc)

    logger.info(
        "Deleted %d/%d files for stem %s",
        len(deleted),
        len(files),
        stem,
    )

    return len(deleted), deleted
