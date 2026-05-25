# Automatic English Accent Support Design

## Goal

Improve recognition for multiple English accents without adding user-facing controls or hardcoded transcript phrase replacements.

## Design

Accent support is automatic and backend-only. The transcription config exposes an `ACCENT_SUPPORT_ENABLED` flag, defaults to a multilingual English-capable Whisper model when no explicit `MODEL_SIZE` is provided, and adds accent-aware instruction text to the Whisper initial prompt.

The feature keeps `language="en"` so output remains English. It does not rewrite recognized words after transcription. Any future correction should come from model/prompt/config tuning, not sample-specific substitutions.

## Verification

Tests cover config defaults, prompt composition, and the `language` / `initial_prompt` arguments passed to Faster-Whisper.
