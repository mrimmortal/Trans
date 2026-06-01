"""Application service for local text-to-speech synthesis."""

from app.services.tts.base import TTSProvider


class TTSService:
    """Use-case boundary for local text-to-speech synthesis."""

    def __init__(self, provider: TTSProvider):
        self._provider = provider

    def synthesize(self, text: str, voice: str | None = None, lang: str | None = None) -> bytes:
        clean_text = text.strip()
        if not clean_text:
            raise ValueError("text must not be empty")

        clean_voice = voice.strip() if voice else None
        clean_lang = lang.strip() if lang else None
        return self._provider.synthesize(clean_text, voice=clean_voice, lang=clean_lang)
