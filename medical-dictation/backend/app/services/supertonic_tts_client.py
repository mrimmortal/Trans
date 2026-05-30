"""Supertonic 3 text-to-speech client."""

from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Callable


class SupertonicConfigError(Exception):
    """Raised when TTS provider configuration or dependency setup is invalid."""


class SupertonicSynthesisError(Exception):
    """Raised when Supertonic cannot synthesize usable audio."""


class SupertonicTTSClient:
    """Small adapter around the Supertonic Python SDK."""

    def __init__(self, config: Any, tts_factory: Callable[..., Any] | None = None):
        self._config = config
        self._tts_factory = tts_factory
        self._tts = None

    def synthesize(self, text: str, voice: str | None = None, lang: str | None = None) -> bytes:
        self._ensure_supertonic_provider()

        clean_text = text.strip()
        if not clean_text:
            raise ValueError("text must not be empty")

        voice_name = self._clean_optional_value(voice) or self._config.SUPERTONIC_VOICE
        lang_code = self._clean_optional_value(lang) or self._config.SUPERTONIC_LANG

        tts = self._get_tts()
        output_path = self._create_temp_wav_path()

        try:
            voice_style = tts.get_voice_style(voice_name=voice_name)
            wav, _duration = tts.synthesize(
                text=clean_text,
                lang=lang_code,
                voice_style=voice_style,
                total_steps=8,
            )
            tts.save_audio(wav, str(output_path))
            audio_bytes = output_path.read_bytes()
        except SupertonicSynthesisError:
            raise
        except Exception as exc:
            raise SupertonicSynthesisError("Supertonic synthesis failed") from exc
        finally:
            output_path.unlink(missing_ok=True)

        if not audio_bytes:
            raise SupertonicSynthesisError("Supertonic returned empty audio")

        return audio_bytes

    def _ensure_supertonic_provider(self) -> None:
        provider = getattr(self._config, "TTS_PROVIDER", "")
        if provider.strip().lower() != "supertonic":
            raise SupertonicConfigError(f"Unsupported TTS_PROVIDER: {provider}")

    def _get_tts(self) -> Any:
        if self._tts is not None:
            return self._tts

        factory = self._tts_factory or self._load_supertonic_tts_class()

        try:
            self._tts = factory(auto_download=True)
        except ImportError as exc:
            raise SupertonicConfigError("Supertonic is not installed") from exc
        except Exception as exc:
            raise SupertonicSynthesisError("Supertonic model could not be loaded or downloaded") from exc

        return self._tts

    def _load_supertonic_tts_class(self) -> Callable[..., Any]:
        try:
            from supertonic import TTS
        except ImportError as exc:
            raise SupertonicConfigError("Supertonic is not installed") from exc

        return TTS

    def _clean_optional_value(self, value: str | None) -> str:
        return value.strip() if value else ""

    def _create_temp_wav_path(self) -> Path:
        with NamedTemporaryFile(prefix="supertonic-", suffix=".wav", delete=False) as file:
            return Path(file.name)
