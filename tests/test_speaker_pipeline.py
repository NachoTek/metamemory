"""Tests for speaker diarization pipeline.

Proves sherpa-onnx works on Windows by:
1. Downloading required models (segmentation + embedding)
2. Creating a synthetic WAV file
3. Running OfflineSpeakerDiarization end-to-end

The test is gated behind the --run-slow flag since model downloads
are ~30 MB and diarization takes several seconds on CPU.
"""

import struct
import tempfile
import wave
from pathlib import Path

import numpy as np
import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_synth_wav(
    path: Path,
    duration_s: float = 5.0,
    sample_rate: int = 16000,
    frequency: float = 440.0,
) -> Path:
    """Create a simple sine-wave WAV file at 16 kHz, 16-bit, mono.

    This is a synthetic audio file — it won't produce meaningful diarization
    segments, but it proves the sherpa-onnx pipeline runs without errors.
    """
    n_samples = int(duration_s * sample_rate)
    t = np.linspace(0, duration_s, n_samples, dtype=np.float32)
    # Generate a sine wave at half amplitude to avoid clipping
    audio = (0.5 * np.sin(2 * np.pi * frequency * t)).astype(np.float32)

    # Convert to 16-bit PCM
    pcm = (audio * 32767).astype(np.int16)

    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)
        wf.writeframes(pcm.tobytes())

    return path


# ---------------------------------------------------------------------------
# Fixture: models
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def downloaded_models(tmp_path_factory):
    """Download diarization models once per module, cached in a temp dir."""
    from metamemory.speaker.model_downloader import ensure_all_models

    cache_dir = tmp_path_factory.mktemp("diarization-models")
    return ensure_all_models(cache_dir=cache_dir)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_model_download_and_diarize(downloaded_models, tmp_path):
    """End-to-end: download models, create synth WAV, run diarization."""
    import sherpa_onnx

    seg_dir = downloaded_models["segmentation_dir"]
    emb_path = downloaded_models["embedding_model"]

    # Verify model files exist
    segmentation_onnx = seg_dir / "model.onnx"
    assert segmentation_onnx.exists(), f"Missing segmentation model: {segmentation_onnx}"
    assert emb_path.exists(), f"Missing embedding model: {emb_path}"

    # Create a synthetic WAV file
    wav_path = tmp_path / "test_synth.wav"
    _create_synth_wav(wav_path, duration_s=5.0)

    # Read the WAV back as float32
    import soundfile as sf
    audio, sr = sf.read(str(wav_path), dtype="float32")
    # Ensure mono
    if audio.ndim > 1:
        audio = audio[:, 0]

    # Build the diarization config
    config = sherpa_onnx.OfflineSpeakerDiarizationConfig(
        segmentation=sherpa_onnx.OfflineSpeakerSegmentationModelConfig(
            pyannote=sherpa_onnx.OfflineSpeakerSegmentationPyannoteModelConfig(
                model=str(segmentation_onnx),
            ),
        ),
        embedding=sherpa_onnx.SpeakerEmbeddingExtractorConfig(
            model=str(emb_path),
        ),
        clustering=sherpa_onnx.FastClusteringConfig(
            num_clusters=-1,
            threshold=0.5,
        ),
        min_duration_on=0.3,
        min_duration_off=0.5,
    )

    assert config.validate(), "Diarization config validation failed — check model paths"

    # Create the diarizer and process
    sd = sherpa_onnx.OfflineSpeakerDiarization(config)

    # Resample if needed
    if sr != sd.sample_rate:
        import soxr
        audio = soxr.resample(audio, sr, sd.sample_rate)
        sr = sd.sample_rate

    assert sr == sd.sample_rate, f"Sample rate mismatch: {sr} vs {sd.sample_rate}"

    result = sd.process(audio).sort_by_start_time()

    # On synthetic audio with no real speech, the result may be empty or
    # contain a single segment. The key assertion is that no exception was
    # raised — this proves the full pipeline works on Windows.
    # If segments are returned, validate their structure.
    for segment in result:
        assert hasattr(segment, "start"), "Segment missing 'start'"
        assert hasattr(segment, "end"), "Segment missing 'end'"
        assert hasattr(segment, "speaker"), "Segment missing 'speaker'"
        assert segment.start >= 0.0
        assert segment.end >= segment.start


def test_speaker_embedding_extractor(downloaded_models):
    """Verify SpeakerEmbeddingExtractor + Manager work on Windows."""
    import sherpa_onnx

    emb_path = downloaded_models["embedding_model"]

    extractor_config = sherpa_onnx.SpeakerEmbeddingExtractorConfig(
        model=str(emb_path),
    )
    extractor = sherpa_onnx.SpeakerEmbeddingExtractor(extractor_config)

    # Create a synthetic audio chunk (2 seconds of noise at 16 kHz)
    sample_rate = 16000
    rng = np.random.default_rng(42)
    audio = (rng.standard_normal(sample_rate * 2) * 0.1).astype(np.float32)

    # Feed audio via an OnlineStream
    stream = extractor.create_stream()
    stream.accept_waveform(sample_rate, audio)
    stream.input_finished()

    # Wait until enough audio is buffered for embedding extraction
    assert extractor.is_ready(stream), (
        "Extractor not ready — synthetic audio may be too short for the model"
    )

    embedding = extractor.compute(stream)
    assert embedding is not None, "Embedding extraction returned None"
    assert len(embedding) > 0, "Embedding is empty"

    # Test SpeakerEmbeddingManager for adding/searching speakers
    manager = sherpa_onnx.SpeakerEmbeddingManager(dim=len(embedding))
    added = manager.add("test_speaker", embedding)
    assert added, "Failed to add speaker embedding to manager"

    # Verify lookup — search returns the best matching speaker name
    result = manager.search(embedding, threshold=0.0)
    assert result == "test_speaker", f"Expected 'test_speaker', got '{result}'"

    # Verify score against the known speaker
    score = manager.score("test_speaker", embedding)
    assert score > 0.9, f"Self-similarity too low: {score}"
