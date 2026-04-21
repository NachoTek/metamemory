# Codebase Map

Generated: 2026-04-21T12:17:09Z | Files: 62 | Described: 0/62
<!-- gsd:codebase-meta {"generatedAt":"2026-04-21T12:17:09Z","fingerprint":"b66613285210e6997ef5ce8938798a40df920657","fileCount":62,"truncated":false} -->

### (root)/
- `.gitignore`
- `check_audio.py`
- `checkpoint-hv-02-12.md`
- `HYBRID_TRANSCRIPTION_SUMMARY.md`
- `ISSUES.md`
- `pytest.ini`
- `README.md`
- `requirements.txt`
- `run.bat`
- `test_low_confidence.py`
- `test_transcription.py`

### src/metamemory/
- `src/metamemory/__init__.py`
- `src/metamemory/main.py`

### src/metamemory/audio/
- `src/metamemory/audio/__init__.py`
- `src/metamemory/audio/cli.py`
- `src/metamemory/audio/session.py`

### src/metamemory/audio/capture/
- `src/metamemory/audio/capture/__init__.py`
- `src/metamemory/audio/capture/devices.py`
- `src/metamemory/audio/capture/fake_module.py`
- `src/metamemory/audio/capture/sounddevice_source.py`

### src/metamemory/audio/storage/
- `src/metamemory/audio/storage/__init__.py`
- `src/metamemory/audio/storage/paths.py`
- `src/metamemory/audio/storage/pcm_part.py`
- `src/metamemory/audio/storage/recovery.py`
- `src/metamemory/audio/storage/wav_finalize.py`

### src/metamemory/config/
- `src/metamemory/config/__init__.py`
- `src/metamemory/config/manager.py`
- `src/metamemory/config/models.py`
- `src/metamemory/config/persistence.py`

### src/metamemory/hardware/
- `src/metamemory/hardware/__init__.py`
- `src/metamemory/hardware/detector.py`
- `src/metamemory/hardware/recommender.py`

### src/metamemory/recording/
- `src/metamemory/recording/__init__.py`
- `src/metamemory/recording/controller.py`

### src/metamemory/transcription/
- `src/metamemory/transcription/__init__.py`
- `src/metamemory/transcription/accumulating_processor.py`
- `src/metamemory/transcription/audio_buffer.py`
- `src/metamemory/transcription/confidence.py`
- `src/metamemory/transcription/engine.py`
- `src/metamemory/transcription/enhancement.py`
- `src/metamemory/transcription/local_agreement.py`
- `src/metamemory/transcription/post_processor.py`
- `src/metamemory/transcription/streaming_pipeline.py`
- `src/metamemory/transcription/transcript_store.py`
- `src/metamemory/transcription/vad_processor.py`

### src/metamemory/widgets/
- `src/metamemory/widgets/__init__.py`
- `src/metamemory/widgets/floating_panels.py`
- `src/metamemory/widgets/main_widget.py`

### tests/
- `tests/manual_integration_test.py`
- `tests/test_audio_session.py`
- `tests/test_audio_storage.py`
- `tests/test_cli_fake_duration.py`
- `tests/test_confidence.py`
- `tests/test_config.py`
- `tests/test_hardware.py`
- `tests/test_streaming_integration.py`
- `tests/test_transcription_engine.py`
- `tests/test_transcription_pipeline.py`

### tests/fixtures/
- `tests/fixtures/SAMPLE-Audio1.mp3`
- `tests/fixtures/SAMPLE-Audio1.wav`
- `tests/fixtures/SAMPLE-Transcript1.txt`
- `tests/fixtures/TEST-OUTPUT-Transcript.md`
