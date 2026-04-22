"""Speaker identification and diarization module.

Provides post-recording speaker diarization using sherpa-onnx
(OfflineSpeakerDiarization + SpeakerEmbeddingExtractor + SpeakerEmbeddingManager).

When a recording stops, the saved WAV is diarized to label speakers (SPK_0, SPK_1, …),
embeddings are extracted per speaker, and known speakers are auto-identified via cosine
similarity against stored voice signatures.
"""

import logging

logger = logging.getLogger(__name__)
