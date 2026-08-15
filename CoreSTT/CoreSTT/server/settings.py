from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional, Tuple


BASE_TUNING_DEFAULTS = {
    "beam_size": 3,
    "beam_size_realtime": 1,
    "batch_size": 1,
    "realtime_batch_size": 1,
    "realtime_processing_pause": 0.6,
    "min_length_of_recording": 0.2,
    "post_speech_silence_duration": 0.7,
    "early_transcription_on_silence": 0.2,
}

TUNING_PROFILES = {
    "custom": {
        "description": "Use explicit CLI/default values.",
        "settings": {},
    },
    "parakeet-low-latency": {
        "description": "Parakeet profile tuned for frequent interim updates.",
        "settings": {
            "batch_size": 1,
            "realtime_batch_size": 1,
            "realtime_processing_pause": 0.04,
            "min_length_of_recording": 0.18,
            "post_speech_silence_duration": 0.45,
            "early_transcription_on_silence": 0.15,
        },
    },
    "parakeet-balanced": {
        "description": "Parakeet profile balancing latency and final stability.",
        "settings": {
            "batch_size": 8,
            "realtime_batch_size": 4,
            "realtime_processing_pause": 0.06,
            "min_length_of_recording": 0.2,
            "post_speech_silence_duration": 0.55,
            "early_transcription_on_silence": 0.2,
        },
    },
    "parakeet-accurate-final": {
        "description": "Parakeet profile favoring calmer segmentation and final quality.",
        "settings": {
            "batch_size": 16,
            "realtime_batch_size": 8,
            "realtime_processing_pause": 0.1,
            "min_length_of_recording": 0.3,
            "post_speech_silence_duration": 0.7,
            "early_transcription_on_silence": 0.35,
        },
    },
}

ACTIVE_RUNTIME_SETTINGS = {
    "diagnostic_logging_enabled",
    "log_level",
    "max_active_speakers",
    "max_audio_packet_bytes",
    "max_final_queue_depth_per_session",
    "max_global_inference_queue_depth",
    "max_realtime_queue_age_ms",
    "max_sessions",
    "realtime_degradation_threshold_ms",
    "resource_log_interval_seconds",
    "resource_monitoring_enabled",
}

NEW_SESSION_RUNTIME_SETTINGS = {
    "audio_queue_size",
    "early_transcription_on_silence",
    "initial_prompt",
    "initial_prompt_realtime",
    "max_audio_queue_seconds_per_session",
    "min_gap_between_recordings",
    "min_length_of_recording",
    "openwakeword_inference_framework",
    "openwakeword_model_paths",
    "post_speech_silence_duration",
    "pre_recording_buffer_duration",
    "realtime_batch_size",
    "realtime_boundary_detector_sensitivity",
    "realtime_boundary_followup_delays",
    "realtime_callback",
    "realtime_max_audio_seconds",
    "realtime_min_audio_seconds",
    "realtime_processing_pause",
    "realtime_transcription_use_syllable_boundaries",
    "resource_log_interval_seconds",
    "resource_metrics_include_cuda",
    "resource_monitoring_enabled",
    "silero_sensitivity",
    "vad_energy_threshold",
    "wake_word_activation_delay",
    "wake_word_buffer_duration",
    "wake_word_followup_window",
    "wake_word_timeout",
    "wake_words",
    "wake_words_sensitivity",
    "wakeword_backend",
    "webrtc_sensitivity",
}

STARTUP_ONLY_SETTINGS = {
    "batch_size",
    "beam_size",
    "beam_size_realtime",
    "compute_type",
    "cpu_threads",
    "default_domain",
    "device",
    "domain_profiles_path",
    "download_root",
    "gpu_device_index",
    "host",
    "language",
    "model",
    "model_warmup",
    "normalize_audio",
    "num_workers",
    "port",
    "realtime_model",
    "realtime_transcription_enabled",
    "realtime_transcription_engine",
    "realtime_transcription_engine_options",
    "single_gpu_inference_gate",
    "transcription_engine",
    "transcription_engine_options",
    "tuning_description",
    "tuning_profile",
    "use_main_model_for_realtime",
    "use_recorder_backed_realtime_session",
    "vad_filter",
    "vad_filter_final",
    "vad_filter_realtime",
}

INT_SETTINGS = {
    "audio_queue_size",
    "batch_size",
    "beam_size",
    "beam_size_realtime",
    "cpu_threads",
    "gpu_device_index",
    "max_active_speakers",
    "max_audio_packet_bytes",
    "max_final_queue_depth_per_session",
    "max_global_inference_queue_depth",
    "max_realtime_queue_age_ms",
    "max_sessions",
    "num_workers",
    "port",
    "realtime_batch_size",
    "realtime_degradation_threshold_ms",
    "resource_log_interval_seconds",
    "webrtc_sensitivity",
}

FLOAT_SETTINGS = {
    "early_transcription_on_silence",
    "max_audio_queue_seconds_per_session",
    "min_gap_between_recordings",
    "min_length_of_recording",
    "post_speech_silence_duration",
    "pre_recording_buffer_duration",
    "realtime_boundary_detector_sensitivity",
    "realtime_max_audio_seconds",
    "realtime_min_audio_seconds",
    "realtime_processing_pause",
    "silero_sensitivity",
    "vad_energy_threshold",
    "wake_word_activation_delay",
    "wake_word_buffer_duration",
    "wake_word_followup_window",
    "wake_word_timeout",
    "wake_words_sensitivity",
}

BOOL_SETTINGS = {
    "diagnostic_logging_enabled",
    "model_warmup",
    "normalize_audio",
    "realtime_transcription_enabled",
    "realtime_transcription_use_syllable_boundaries",
    "resource_metrics_include_cuda",
    "resource_monitoring_enabled",
    "single_gpu_inference_gate",
    "use_main_model_for_realtime",
    "use_recorder_backed_realtime_session",
    "vad_filter",
    "vad_filter_final",
    "vad_filter_realtime",
}

OPTIONAL_STRING_SETTINGS = {
    "download_root",
    "default_domain",
    "domain_profiles_path",
    "initial_prompt",
    "initial_prompt_realtime",
    "openwakeword_model_paths",
    "realtime_transcription_engine",
}

DICT_SETTINGS = {
    "realtime_transcription_engine_options",
    "transcription_engine_options",
}

TUPLE_FLOAT_SETTINGS = {"realtime_boundary_followup_delays"}


@dataclass
class ServerSettings:
    host: str = "0.0.0.0"
    port: int = 8010
    tuning_profile: str = "custom"
    tuning_description: str = TUNING_PROFILES["custom"]["description"]
    model: str = "small.en"
    realtime_model: str = "tiny.en"
    language: str = "en"
    transcription_engine: str = "faster_whisper"
    realtime_transcription_engine: Optional[str] = None
    transcription_engine_options: Optional[Dict[str, Any]] = None
    realtime_transcription_engine_options: Optional[Dict[str, Any]] = None
    domain_profiles_path: str = "domain_profiles.json"
    default_domain: Optional[str] = None
    download_root: Optional[str] = None
    compute_type: str = "default"
    cpu_threads: Optional[int] = None
    diagnostic_logging_enabled: bool = False
    num_workers: int = 1
    single_gpu_inference_gate: bool = True
    device: str = "cuda"
    gpu_device_index: int = 0
    beam_size: int = 3
    beam_size_realtime: int = 1
    batch_size: int = 1
    realtime_batch_size: int = 1
    vad_filter_final: bool = True
    vad_filter_realtime: bool = False
    vad_filter: Optional[bool] = None
    normalize_audio: bool = False
    realtime_callback: str = "update"
    min_length_of_recording: float = 0.2
    min_gap_between_recordings: float = 0.0
    post_speech_silence_duration: float = 0.7
    silero_sensitivity: float = 0.05
    webrtc_sensitivity: int = 3
    realtime_processing_pause: float = 0.6
    realtime_transcription_enabled: bool = False
    realtime_transcription_use_syllable_boundaries: bool = False
    realtime_boundary_detector_sensitivity: float = 0.6
    realtime_boundary_followup_delays: Tuple[float, ...] = (0.05, 0.2)
    early_transcription_on_silence: float = 0.2
    initial_prompt: Optional[str] = None
    initial_prompt_realtime: Optional[str] = None
    wakeword_backend: str = ""
    openwakeword_model_paths: Optional[str] = None
    openwakeword_inference_framework: str = "onnx"
    wake_words: str = ""
    wake_words_sensitivity: float = 0.5
    wake_word_activation_delay: float = 0.0
    wake_word_timeout: float = 5.0
    wake_word_buffer_duration: float = 0.1
    wake_word_followup_window: float = 0.0
    use_main_model_for_realtime: bool = False
    use_recorder_backed_realtime_session: bool = False
    audio_queue_size: int = 128
    max_audio_packet_bytes: int = 512 * 1024
    log_level: str = "INFO"
    max_sessions: int = 10
    max_active_speakers: int = 10
    max_audio_queue_seconds_per_session: float = 30.0
    pre_recording_buffer_duration: float = 0.75
    max_realtime_queue_age_ms: int = 1500
    max_final_queue_depth_per_session: int = 8
    max_global_inference_queue_depth: int = 64
    realtime_degradation_threshold_ms: int = 1500
    resource_monitoring_enabled: bool = True
    resource_log_interval_seconds: int = 30
    resource_metrics_include_cuda: bool = True
    realtime_min_audio_seconds: float = 0.8
    realtime_max_audio_seconds: float = 5.0
    vad_energy_threshold: float = 250.0
    model_warmup: bool = True

    def __post_init__(self):
        if self.vad_filter is not None:
            if not isinstance(self.vad_filter, bool):
                raise ValueError("vad_filter must be a boolean")
            self.vad_filter_final = self.vad_filter
            self.vad_filter_realtime = self.vad_filter
        if self.model != "small.en":
            raise ValueError("model is fixed to small.en for final transcription")
        if self.realtime_model != "tiny.en":
            raise ValueError("realtime_model is fixed to tiny.en for realtime transcription")
        if self.use_main_model_for_realtime:
            raise ValueError(
                "use_main_model_for_realtime is disabled because realtime and final use separate fixed models"
            )
        if self.cpu_threads is not None and self.cpu_threads <= 0:
            raise ValueError("cpu_threads must be a positive integer or None")
        if self.num_workers <= 0:
            raise ValueError("num_workers must be a positive integer")
        if self.resource_log_interval_seconds <= 0:
            raise ValueError("resource_log_interval_seconds must be a positive integer")

    def public_dict(self):
        data = asdict(self)
        data.pop("transcription_engine_options", None)
        data.pop("realtime_transcription_engine_options", None)
        data["wake_word_enabled"] = self.wake_word_enabled()
        # Deprecated compatibility alias for clients that predate split VAD settings.
        data["vad_filter"] = self.vad_filter_final
        return data

    def wake_word_enabled(self):
        return bool(str(self.wakeword_backend or "").strip() and str(self.wake_words or "").strip())


def runtime_settings_contract():
    return {
        "activeSessionSafe": sorted(ACTIVE_RUNTIME_SETTINGS),
        "newSessionOnly": sorted(NEW_SESSION_RUNTIME_SETTINGS),
        "startupOnly": sorted(STARTUP_ONLY_SETTINGS),
    }


def coerce_setting_value(name, value):
    if name in BOOL_SETTINGS:
        if not isinstance(value, bool):
            raise ValueError(f"{name} must be a boolean")
        return value
    if name in INT_SETTINGS:
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{name} must be an integer")
        return value
    if name in FLOAT_SETTINGS:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{name} must be a number")
        return float(value)
    if name in TUPLE_FLOAT_SETTINGS:
        if not isinstance(value, (list, tuple)):
            raise ValueError(f"{name} must be a list of numbers")
        return tuple(float(item) for item in value)
    if name in DICT_SETTINGS:
        if value is not None and not isinstance(value, dict):
            raise ValueError(f"{name} must be a JSON object or null")
        return value
    if name in OPTIONAL_STRING_SETTINGS:
        if value is not None and not isinstance(value, str):
            raise ValueError(f"{name} must be a string or null")
        return value
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a string")
    return value
