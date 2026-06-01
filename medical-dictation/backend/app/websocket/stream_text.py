"""Streaming transcript cleanup helpers."""

import re


def sanitize_stream_text(text: str, recent_emitted_words: list[str]) -> str:
    """Clean boundary artifacts caused by audio overlap in streaming mode."""
    text = text.strip()
    if not text:
        return ""

    text = re.sub(r"\s+\w+-$", "", text).strip()
    text = re.sub(r"\b(?:pause|paused)\b", "", text, flags=re.IGNORECASE)
    text = remove_adjacent_repeated_phrases(text)
    if not text:
        return ""

    words = text.split()
    normalized_words = boundary_tokens(text)
    recent = recent_emitted_words

    max_overlap = min(len(normalized_words), len(recent), 8)
    overlap_count = 0
    remove_word_count = 0
    for size in range(max_overlap, 0, -1):
        if token_sequences_match(recent[-size:], normalized_words[:size]):
            overlap_count = size
            remove_word_count = word_count_for_boundary_tokens(words, size)
            break

    if not overlap_count:
        max_repeated_prefix = min(len(normalized_words), len(recent))
        for size in range(max_repeated_prefix, 7, -1):
            if tokens_contain_sequence(recent, normalized_words[:size]):
                overlap_count = size
                remove_word_count = word_count_for_boundary_tokens(words, size)
                break

    if overlap_count:
        text = " ".join(words[remove_word_count:]).strip()

    return cleanup_stream_text(text) if text else ""


def remember_emitted_text(recent_emitted_words: list[str], text: str) -> list[str]:
    """Return a short normalized tail to remove duplicate overlap text later."""
    words = boundary_tokens(text)
    return (recent_emitted_words + words)[-240:]


def remove_adjacent_repeated_phrases(text: str) -> str:
    """Remove repeated 1-3 word phrases created around pauses."""
    words = text.split()
    output: list[str] = []
    for word in words:
        output.append(word)
        for size in range(3, 0, -1):
            if len(output) < size * 2:
                continue
            first = [normalize_boundary_word(w) for w in output[-size * 2 : -size]]
            second = [normalize_boundary_word(w) for w in output[-size:]]
            if first == second and all(first):
                del output[-size:]
                break

    return " ".join(output)


def cleanup_stream_text(text: str) -> str:
    text = re.sub(r"\s{2,}", " ", text)
    text = re.sub(r"\s+([.,;:])", r"\1", text)
    return text.strip()


def normalize_boundary_word(word: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", word.lower())


def boundary_tokens(text: str) -> list[str]:
    tokens: list[str] = []
    for word in text.split():
        for part in re.split(r"[-/]+", word):
            normalized = normalize_boundary_word(part)
            if normalized:
                tokens.append(normalized)
    return tokens


def word_count_for_boundary_tokens(words: list[str], token_count: int) -> int:
    consumed_tokens = 0
    for index, word in enumerate(words, start=1):
        consumed_tokens += len(boundary_tokens(word))
        if consumed_tokens >= token_count:
            return index
    return min(token_count, len(words))


def tokens_contain_sequence(tokens: list[str], sequence: list[str]) -> bool:
    if not sequence or len(sequence) > len(tokens):
        return False
    for start in range(0, len(tokens) - len(sequence) + 1):
        if token_sequences_match(tokens[start : start + len(sequence)], sequence):
            return True
    return False


def token_sequences_match(left: list[str], right: list[str]) -> bool:
    if len(left) != len(right):
        return False
    return all(tokens_match(a, b) for a, b in zip(left, right))


def tokens_match(left: str, right: str) -> bool:
    if left == right:
        return True
    if min(len(left), len(right)) < 4:
        return False
    if abs(len(left) - len(right)) > 1:
        return False

    previous = list(range(len(right) + 1))
    for i, left_char in enumerate(left, start=1):
        current = [i]
        for j, right_char in enumerate(right, start=1):
            cost = 0 if left_char == right_char else 1
            current.append(
                min(
                    current[j - 1] + 1,
                    previous[j] + 1,
                    previous[j - 1] + cost,
                )
            )
        previous = current

    return previous[-1] <= 1
