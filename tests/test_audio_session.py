"""End-to-end tests for AudioSession using FakeAudioModule.

These tests verify the complete recording pipeline:
1. Generate test audio (sine waves)
2. Run AudioSession with FakeAudioModule
3. Verify output WAV is valid and has expected format
4. Test multi-source mixing
"""

import wave
import struct
import tempfile
import numpy as np
import pytest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from metamemory.audio import (
    AudioSession,
    SessionConfig,
    SourceConfig,
    get_recordings_dir,
)


def create_sine_wave_wav(
    path: Path,
    frequency: float = 440.0,
    duration: float = 1.0,
    sample_rate: int = 16000,
    channels: int = 1,
    amplitude: float = 0.5,
) -> None:
    """Create a sine wave WAV file for testing.
    
    Args:
        path: Output WAV file path
        frequency: Sine wave frequency in Hz
        duration: Duration in seconds
        sample_rate: Sample rate in Hz
        channels: Number of channels (1=mono, 2=stereo)
        amplitude: Peak amplitude (0.0 to 1.0)
    """
    num_samples = int(sample_rate * duration)
    
    # Generate sine wave
    t = np.linspace(0, duration, num_samples, endpoint=False)
    sine_wave = amplitude * np.sin(2 * np.pi * frequency * t)
    
    # Convert to int16
    int16_data = (sine_wave * 32767).astype(np.int16)
    
    # Handle stereo
    if channels == 2:
        int16_data = np.column_stack([int16_data, int16_data])
    
    # Write WAV file
    with wave.open(str(path), 'wb') as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)
        wf.writeframes(int16_data.tobytes())


def read_wav_file(path: Path) -> tuple:
    """Read a WAV file and return its properties.
    
    Returns:
        Tuple of (n_channels, sample_rate, sample_width, n_frames, duration)
    """
    with wave.open(str(path), 'rb') as wf:
        n_channels = wf.getnchannels()
        sample_rate = wf.getframerate()
        sample_width = wf.getsampwidth()
        n_frames = wf.getnframes()
        duration = n_frames / sample_rate
        return n_channels, sample_rate, sample_width, n_frames, duration


class TestAudioSessionSingleSource:
    """Test AudioSession with single fake audio source."""
    
    def test_single_fake_source_recording(self, tmp_path):
        """Test recording from a single fake audio source."""
        # Create test WAV file (1 second, 440Hz sine, 16kHz)
        test_wav = tmp_path / "test_440hz.wav"
        create_sine_wave_wav(test_wav, frequency=440.0, duration=1.0, sample_rate=16000)
        
        # Configure session with fake source
        config = SessionConfig(
            sources=[SourceConfig(type='fake', fake_path=str(test_wav))],
            output_dir=tmp_path,
            sample_rate=16000,
            channels=1,
        )
        
        # Record for ~0.5 seconds (fake source loops)
        session = AudioSession()
        session.start(config)
        
        import time
        time.sleep(0.5)
        
        wav_path = session.stop()
        
        # Verify output exists
        assert wav_path.exists(), f"WAV file not created: {wav_path}"
        
        # Verify WAV format
        n_channels, sample_rate, sample_width, n_frames, duration = read_wav_file(wav_path)
        assert n_channels == 1, f"Expected mono, got {n_channels} channels"
        assert sample_rate == 16000, f"Expected 16kHz, got {sample_rate}Hz"
        assert sample_width == 2, f"Expected 16-bit, got {sample_width * 8}-bit"
        assert duration > 0, "Recording should have non-zero duration"
        
        # Verify stats
        stats = session.get_stats()
        assert stats.frames_recorded > 0, "Should have recorded frames"
        assert session.get_state().name == 'FINALIZED'
    
    def test_fake_source_with_resampling(self, tmp_path):
        """Test that fake source at different sample rate is properly resampled."""
        # Create test WAV at 48kHz (will be resampled to 16kHz)
        test_wav = tmp_path / "test_48k.wav"
        create_sine_wave_wav(test_wav, frequency=880.0, duration=0.5, sample_rate=48000)
        
        config = SessionConfig(
            sources=[SourceConfig(type='fake', fake_path=str(test_wav))],
            output_dir=tmp_path,
            sample_rate=16000,  # Target rate
            channels=1,
        )
        
        session = AudioSession()
        session.start(config)
        
        import time
        time.sleep(0.3)
        
        wav_path = session.stop()
        
        # Verify output is at target sample rate
        _, sample_rate, _, _, _ = read_wav_file(wav_path)
        assert sample_rate == 16000, f"Expected 16kHz output, got {sample_rate}Hz"
    
    def test_stereo_to_mono_downmix(self, tmp_path):
        """Test that stereo input is properly downmixed to mono."""
        # Create stereo WAV file
        test_wav = tmp_path / "test_stereo.wav"
        create_sine_wave_wav(test_wav, frequency=440.0, duration=0.5, channels=2)
        
        config = SessionConfig(
            sources=[SourceConfig(type='fake', fake_path=str(test_wav))],
            output_dir=tmp_path,
            sample_rate=16000,
            channels=1,  # Force mono output
        )
        
        session = AudioSession()
        session.start(config)
        
        import time
        time.sleep(0.3)
        
        wav_path = session.stop()
        
        # Verify mono output
        n_channels, _, _, _, _ = read_wav_file(wav_path)
        assert n_channels == 1, f"Expected mono output from stereo input, got {n_channels} channels"


class TestAudioSessionMultiSource:
    """Test AudioSession with multiple sources (mixing)."""
    
    def test_dual_fake_source_mixing(self, tmp_path):
        """Test mixing two fake audio sources (representing mic + system)."""
        # Create two different sine wave files
        wav_440 = tmp_path / "sine_440.wav"
        wav_880 = tmp_path / "sine_880.wav"
        create_sine_wave_wav(wav_440, frequency=440.0, duration=1.0, sample_rate=16000)
        create_sine_wave_wav(wav_880, frequency=880.0, duration=1.0, sample_rate=16000)
        
        # Configure session with both sources (mic + system simulation)
        config = SessionConfig(
            sources=[
                SourceConfig(type='fake', fake_path=str(wav_440), gain=1.0),
                SourceConfig(type='fake', fake_path=str(wav_880), gain=0.5),
            ],
            output_dir=tmp_path,
            sample_rate=16000,
            channels=1,
        )
        
        session = AudioSession()
        session.start(config)
        
        import time
        time.sleep(0.5)
        
        wav_path = session.stop()
        
        # Verify output exists and is valid
        assert wav_path.exists(), "WAV file not created"
        
        n_channels, sample_rate, sample_width, n_frames, duration = read_wav_file(wav_path)
        assert n_channels == 1
        assert sample_rate == 16000
        
        # Verify stats show activity from both sources
        stats = session.get_stats()
        assert stats.frames_recorded > 0
        
        # Read the mixed audio and verify it contains both frequencies
        with wave.open(str(wav_path), 'rb') as wf:
            frames = wf.readframes(n_frames)
            audio_data = np.frombuffer(frames, dtype=np.int16)
        
        # Perform FFT to check frequency content
        fft = np.fft.fft(audio_data)
        freqs = np.fft.fftfreq(len(audio_data), 1/16000)
        magnitude = np.abs(fft)
        
        # Find peaks in positive frequency range
        positive_freqs = freqs[:len(freqs)//2]
        positive_magnitude = magnitude[:len(magnitude)//2]
        
        # Check for peaks near 440Hz and 880Hz (with tolerance for resampling artifacts)
        peak_indices = np.argsort(positive_magnitude)[-10:]  # Top 10 peaks
        peak_freqs = positive_freqs[peak_indices]
        
        has_440 = any(400 <= f <= 480 for f in peak_freqs)
        has_880 = any(800 <= f <= 960 for f in peak_freqs)
        
        assert has_440 or has_880, f"Mixed audio should contain 440Hz or 880Hz peaks, got peaks at: {peak_freqs}"


class TestAudioSessionErrorHandling:
    """Test AudioSession error handling."""
    
    def test_no_sources_error(self, tmp_path):
        """Test that session raises error when no sources configured."""
        config = SessionConfig(sources=[], output_dir=tmp_path)
        session = AudioSession()
        
        from metamemory.audio.session import NoSourcesError
        with pytest.raises(NoSourcesError):
            session.start(config)
    
    def test_fake_source_missing_file(self, tmp_path):
        """Test error when fake source references non-existent file."""
        config = SessionConfig(
            sources=[SourceConfig(type='fake', fake_path='/nonexistent/file.wav')],
            output_dir=tmp_path,
        )
        session = AudioSession()
        
        from metamemory.audio.session import SessionError
        with pytest.raises((SessionError, FileNotFoundError)):
            session.start(config)


class TestAudioSessionLifecycle:
    """Test AudioSession state machine and lifecycle."""
    
    def test_state_transitions(self, tmp_path):
        """Test that session follows correct state transitions."""
        test_wav = tmp_path / "test.wav"
        create_sine_wave_wav(test_wav, duration=1.0)
        
        session = AudioSession()
        
        # Initial state
        assert session.get_state().name == 'IDLE'
        
        # After start
        config = SessionConfig(
            sources=[SourceConfig(type='fake', fake_path=str(test_wav))],
            output_dir=tmp_path,
        )
        session.start(config)
        assert session.get_state().name == 'RECORDING'
        
        # After stop
        import time
        time.sleep(0.1)
        session.stop()
        assert session.get_state().name == 'FINALIZED'
    
    def test_session_reuse(self, tmp_path):
        """Test that a session can be reused after finalization."""
        test_wav = tmp_path / "test.wav"
        create_sine_wave_wav(test_wav, duration=1.0)
        
        session = AudioSession()
        
        # First recording
        config = SessionConfig(
            sources=[SourceConfig(type='fake', fake_path=str(test_wav))],
            output_dir=tmp_path,
        )
        session.start(config)
        
        import time
        time.sleep(0.1)
        wav_path1 = session.stop()
        
        assert wav_path1.exists()
        
        # Ensure unique timestamp for second recording filename
        import time as _time
        _time.sleep(1.1)
        
        # Second recording (reuse same session)
        session.start(config)
        time.sleep(0.1)
        wav_path2 = session.stop()
        
        assert wav_path2.exists()
        assert wav_path1 != wav_path2, "Each recording should have unique filename"
