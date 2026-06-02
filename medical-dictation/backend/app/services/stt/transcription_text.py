"""Text cleanup and hallucination filtering for STT output."""

import logging
import re
from collections import Counter

logger = logging.getLogger(__name__)

DEFAULT_HALLUCINATION_PHRASES = [
    "thank you",
    "thanks for watching",
    "subscribe",
    "like and subscribe",
    "thank you for watching",
    "the end",
    "bye",
    "goodbye",
    "see you next time",
    "please subscribe",
    "MobyDick",
    "www.",
    ".com",
    "copyright",
    "all rights reserved",
    "subtitles by",
    "captions by",
    "translated by",
    "music",
    "applause",
    "laughter",
    "http",
    ".org",
]


def filter_hallucinations(text: str, config) -> str:
    """Filter common Whisper hallucinations and prompt leakage."""
    if not text or len(text.strip()) == 0:
        return ""

    text_lower = text.lower().strip()
    hallucination_phrases = getattr(
        config,
        "HALLUCINATION_PHRASES",
        DEFAULT_HALLUCINATION_PHRASES,
    )
    normalized_text = text_lower.strip(" .,!?:;\"'")

    if normalized_text in [p.lower().strip(" .,!?:;\"'") for p in hallucination_phrases]:
        logger.debug("Filtered hallucination (exact match, text_length=%s)", len(text))
        return ""

    if len(text) < 15:
        for phrase in ["thank you", "subscribe", "www.", ".com", "copyright"]:
            if phrase in text_lower:
                logger.debug("Filtered hallucination (short + phrase, text_length=%s)", len(text))
                return ""

    instruction_leak_patterns = [
        "transcribe only the words spoken",
        "do not invent names",
        "prefer silence over guessing",
        "preserve dictated wording",
    ]
    if any(pattern in text_lower for pattern in instruction_leak_patterns):
        logger.debug("Filtered hallucination (prompt leakage, text_length=%s)", len(text))
        return ""

    words = text.split()
    if len(words) >= 3:
        word_counts = Counter(w.lower() for w in words if len(w) > 2)
        if word_counts:
            _most_common_word, count = word_counts.most_common(1)[0]
            if count / len(words) > 0.5:
                logger.debug("Filtered hallucination (repetition, text_length=%s)", len(text))
                return ""

    sentences = [
        re.sub(r"[^a-z0-9]+", " ", sentence.lower()).strip()
        for sentence in re.split(r"[.!?]+", text)
        if sentence.strip()
    ]
    if len(sentences) >= 2:
        sentence_counts = Counter(sentences)
        if sentence_counts.most_common(1)[0][1] > 1:
            logger.debug("Filtered hallucination (repeated sentence, text_length=%s)", len(text))
            return ""

    text_stripped = text.strip().rstrip(".,;:!?")
    if len(text_stripped) < 2:
        logger.debug("Filtered hallucination (too short, text_length=%s)", len(text))
        return ""

    if all(not c.isalnum() for c in text_stripped):
        logger.debug("Filtered hallucination (punctuation only, text_length=%s)", len(text))
        return ""

    if re.search(r"\b(\w)\s+\1\s+\1\b", text_lower):
        logger.debug("Filtered hallucination (single char repetition, text_length=%s)", len(text))
        return ""

    return text


def clean_text(text: str) -> str:
    """Collapse spacing, remove leading punctuation, and strip whitespace."""
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"^[,;:]+\s*", "", text)
    return text.strip()
