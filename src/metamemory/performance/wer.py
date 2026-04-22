"""Word Error Rate (WER) calculator using word-level Levenshtein distance.

Computes WER as (S + D + I) / N where:
- S = substitutions, D = deletions, I = insertions
- N = number of words in the reference

All text is normalized (lowercased, punctuation stripped) before comparison.
"""

import re
from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class WERDetail:
    """Detailed WER breakdown."""
    wer: float
    substitutions: int
    deletions: int
    insertions: int
    reference_length: int
    hypothesis_length: int


def _normalize_text(text: str) -> List[str]:
    """Normalize text to a list of lowercase words with punctuation stripped.

    Args:
        text: Raw text string.

    Returns:
        List of cleaned, lowercased word tokens.
    """
    # Strip punctuation and normalize whitespace
    cleaned = re.sub(r"[^\w\s]", "", text.lower())
    return cleaned.split()


def _levenshtein_align(ref: List[str], hyp: List[str]) -> Tuple[int, int, int]:
    """Compute word-level Levenshtein distance and return (S, D, I) counts.

    Uses dynamic programming to find minimum edit distance, then backtracks
    to count substitutions, deletions, and insertions separately.

    Args:
        ref: Reference word list (ground truth).
        hyp: Hypothesis word list (transcription output).

    Returns:
        Tuple of (substitutions, deletions, insertions).
    """
    n = len(ref)
    m = len(hyp)

    # DP table: dp[i][j] = edit distance between ref[:i] and hyp[:j]
    dp = [[0] * (m + 1) for _ in range(n + 1)]

    for i in range(n + 1):
        dp[i][0] = i  # deletions
    for j in range(m + 1):
        dp[0][j] = j  # insertions

    for i in range(1, n + 1):
        for j in range(1, m + 1):
            if ref[i - 1] == hyp[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]  # match, no cost
            else:
                dp[i][j] = 1 + min(
                    dp[i - 1][j - 1],  # substitution
                    dp[i - 1][j],       # deletion
                    dp[i][j - 1],       # insertion
                )

    # Backtrack to count operation types
    substitutions = 0
    deletions = 0
    insertions = 0

    i, j = n, m
    while i > 0 or j > 0:
        if i > 0 and j > 0 and ref[i - 1] == hyp[j - 1]:
            i -= 1
            j -= 1
        elif i > 0 and j > 0 and dp[i][j] == dp[i - 1][j - 1] + 1:
            substitutions += 1
            i -= 1
            j -= 1
        elif i > 0 and dp[i][j] == dp[i - 1][j] + 1:
            deletions += 1
            i -= 1
        else:
            insertions += 1
            j -= 1

    return substitutions, deletions, insertions


def calculate_wer(reference: str, hypothesis: str) -> float:
    """Calculate Word Error Rate between reference and hypothesis texts.

    Args:
        reference: Ground truth text.
        hypothesis: Transcription output text.

    Returns:
        WER as a float between 0.0 (perfect) and potentially > 1.0
        (if insertions exceed reference length). Returns 0.0 when both
        texts are empty, and 1.0 when reference is empty but hypothesis is not.
    """
    ref_words = _normalize_text(reference)
    hyp_words = _normalize_text(hypothesis)

    if not ref_words and not hyp_words:
        return 0.0
    if not ref_words:
        return 1.0

    s, d, i = _levenshtein_align(ref_words, hyp_words)
    return (s + d + i) / len(ref_words)


def calculate_wer_details(reference: str, hypothesis: str) -> WERDetail:
    """Calculate detailed WER breakdown with operation counts.

    Args:
        reference: Ground truth text.
        hypothesis: Transcription output text.

    Returns:
        WERDetail with wer, substitutions, deletions, insertions, and word counts.
    """
    ref_words = _normalize_text(reference)
    hyp_words = _normalize_text(hypothesis)

    if not ref_words and not hyp_words:
        return WERDetail(
            wer=0.0, substitutions=0, deletions=0, insertions=0,
            reference_length=0, hypothesis_length=0,
        )
    if not ref_words:
        return WERDetail(
            wer=1.0, substitutions=0, deletions=0, insertions=len(hyp_words),
            reference_length=0, hypothesis_length=len(hyp_words),
        )

    s, d, i = _levenshtein_align(ref_words, hyp_words)
    return WERDetail(
        wer=(s + d + i) / len(ref_words),
        substitutions=s,
        deletions=d,
        insertions=i,
        reference_length=len(ref_words),
        hypothesis_length=len(hyp_words),
    )
