"""Tests for recording file enumeration and deletion utilities."""

import pytest
from pathlib import Path

from meetandread.recording.management import (
    delete_recording,
    enumerate_recording_files,
)


@pytest.fixture
def recording_dirs(tmp_path):
    """Create recordings/ and transcripts/ directories under tmp_path."""
    recordings = tmp_path / "recordings"
    transcripts = tmp_path / "transcripts"
    recordings.mkdir()
    transcripts.mkdir()
    return recordings, transcripts


@pytest.fixture(autouse=True)
def patch_dirs(monkeypatch, recording_dirs):
    """Redirect path resolution to temp directories."""
    recordings_dir, transcripts_dir = recording_dirs

    monkeypatch.setattr(
        "meetandread.recording.management.get_recordings_dir",
        lambda: recordings_dir,
    )
    monkeypatch.setattr(
        "meetandread.recording.management.get_transcripts_dir",
        lambda: transcripts_dir,
    )


class TestEnumerateRecordingFiles:
    """Tests for enumerate_recording_files."""

    def test_enumerate_finds_md_and_wav(self, recording_dirs):
        """Both .md and .wav exist — both returned."""
        recordings_dir, transcripts_dir = recording_dirs
        stem = "recording-2026-04-01-120000"

        wav = recordings_dir / f"{stem}.wav"
        md = transcripts_dir / f"{stem}.md"
        wav.write_text("audio")
        md.write_text("# transcript")

        found = enumerate_recording_files(stem)

        found_names = {p.name for p in found}
        assert f"{stem}.wav" in found_names
        assert f"{stem}.md" in found_names
        assert len(found) == 2

    def test_enumerate_skips_missing(self, recording_dirs):
        """Only .wav exists — enumeration returns just that file."""
        recordings_dir, transcripts_dir = recording_dirs
        stem = "recording-2026-04-01-120000"

        wav = recordings_dir / f"{stem}.wav"
        wav.write_text("audio")

        found = enumerate_recording_files(stem)

        assert len(found) == 1
        assert found[0].name == f"{stem}.wav"

    def test_enumerate_finds_sidecars(self, recording_dirs):
        """Scrub sidecar files matching {stem}_scrub_*.md are included."""
        recordings_dir, transcripts_dir = recording_dirs
        stem = "recording-2026-04-01-120000"

        md = transcripts_dir / f"{stem}.md"
        md.write_text("# transcript")

        sidecar1 = transcripts_dir / f"{stem}_scrub_v1.md"
        sidecar2 = transcripts_dir / f"{stem}_scrub_v2.md"
        sidecar1.write_text("# scrub v1")
        sidecar2.write_text("# scrub v2")

        found = enumerate_recording_files(stem)

        found_names = {p.name for p in found}
        assert f"{stem}.md" in found_names
        assert f"{stem}_scrub_v1.md" in found_names
        assert f"{stem}_scrub_v2.md" in found_names
        assert len(found) == 3

    def test_enumerate_finds_pcm_parts(self, recording_dirs):
        """PCM part and metadata files are included."""
        recordings_dir, transcripts_dir = recording_dirs
        stem = "recording-2026-04-01-120000"

        pcm = recordings_dir / f"{stem}.pcm.part"
        meta = recordings_dir / f"{stem}.pcm.part.json"
        pcm.write_bytes(b"\x00\x01")
        meta.write_text("{}")

        found = enumerate_recording_files(stem)

        found_names = {p.name for p in found}
        assert f"{stem}.pcm.part" in found_names
        assert f"{stem}.pcm.part.json" in found_names


class TestDeleteRecording:
    """Tests for delete_recording."""

    def test_delete_removes_all(self, recording_dirs):
        """All associated files are deleted."""
        recordings_dir, transcripts_dir = recording_dirs
        stem = "recording-2026-04-01-120000"

        wav = recordings_dir / f"{stem}.wav"
        md = transcripts_dir / f"{stem}.md"
        wav.write_text("audio")
        md.write_text("# transcript")

        count, deleted = delete_recording(stem)

        assert count == 2
        assert len(deleted) == 2
        assert not wav.exists()
        assert not md.exists()

    def test_delete_partial(self, recording_dirs):
        """Only some files exist — deletes what's there, skips the rest."""
        recordings_dir, transcripts_dir = recording_dirs
        stem = "recording-2026-04-01-120000"

        wav = recordings_dir / f"{stem}.wav"
        wav.write_text("audio")
        # No .md, no .pcm.part

        count, deleted = delete_recording(stem)

        assert count == 1
        assert not wav.exists()
