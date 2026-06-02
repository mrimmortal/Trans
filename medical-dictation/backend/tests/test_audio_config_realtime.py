import importlib
import os
import unittest
from contextlib import contextmanager

import app.audio_config as audio_config


CONFIG_ENV_KEYS = (
    "TRANSCRIPTION_PROFILE",
    "MIN_CHUNK_DURATION_SECONDS",
    "MAX_CHUNK_DURATION_SECONDS",
    "OVERLAP_DURATION_SECONDS",
    "SILENCE_TIMEOUT_SECONDS",
    "SILERO_VAD_THRESHOLD",
    "SILERO_MIN_SPEECH_MS",
    "SILERO_MIN_SILENCE_MS",
    "SILERO_SPEECH_PAD_MS",
    "VAD_FILTER",
    "COMPRESSION_RATIO_THRESHOLD",
    "LOG_PROB_THRESHOLD",
    "NO_SPEECH_THRESHOLD",
    "TEMPERATURE",
    "MODEL_SIZE",
    "DEVICE",
    "COMPUTE_TYPE",
    "BEAM_SIZE",
    "ACCENT_SUPPORT_ENABLED",
)


@contextmanager
def loaded_audio_config(env_overrides: dict[str, str] | None = None):
    previous = {key: os.environ.get(key) for key in CONFIG_ENV_KEYS}
    for key in CONFIG_ENV_KEYS:
        os.environ.pop(key, None)
    os.environ.update(env_overrides or {})

    module = importlib.reload(audio_config)
    try:
        yield module.AudioConfig
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        importlib.reload(audio_config)


class AudioConfigRealtimeTests(unittest.TestCase):
    def test_balanced_realtime_defaults_preserve_current_behavior(self):
        with loaded_audio_config() as config:
            self.assertEqual(config.TRANSCRIPTION_PROFILE, "balanced_realtime")
            self.assertEqual(config.MODEL_SIZE, "base")
            self.assertEqual(config.DEVICE, "cpu")
            self.assertEqual(config.COMPUTE_TYPE, "int8")
            self.assertEqual(config.MIN_CHUNK_DURATION_SECONDS, 0.6)
            self.assertEqual(config.SILENCE_TIMEOUT_SECONDS, 0.7)
            self.assertEqual(config.MAX_CHUNK_DURATION_SECONDS, 6.0)
            self.assertEqual(config.OVERLAP_DURATION_SECONDS, 0.5)
            self.assertEqual(config.BEAM_SIZE, 2)

    def test_balanced_alias_resolves_to_balanced_realtime_values(self):
        with loaded_audio_config({"TRANSCRIPTION_PROFILE": "balanced"}) as config:
            self.assertEqual(config.TRANSCRIPTION_PROFILE, "balanced")
            self.assertEqual(config.MODEL_SIZE, "base")
            self.assertEqual(config.DEVICE, "cpu")
            self.assertEqual(config.COMPUTE_TYPE, "int8")
            self.assertEqual(config.MIN_CHUNK_DURATION_SECONDS, 0.6)
            self.assertEqual(config.MAX_CHUNK_DURATION_SECONDS, 6.0)
            self.assertEqual(config.OVERLAP_DURATION_SECONDS, 0.5)
            self.assertEqual(config.BEAM_SIZE, 2)

    def test_profile_defaults_cover_latency_accuracy_pi_and_gpu(self):
        expectations = {
            "low_latency": {
                "model_size": "base",
                "device": "cpu",
                "compute_type": "int8",
                "min_chunk": 0.5,
                "max_chunk": 5.0,
                "overlap": 0.4,
                "silence_timeout": 0.5,
                "beam_size": 1,
            },
            "high_accuracy": {
                "model_size": "base",
                "device": "cpu",
                "compute_type": "int8",
                "min_chunk": 0.6,
                "max_chunk": 8.0,
                "overlap": 0.7,
                "silence_timeout": 0.9,
                "beam_size": 5,
            },
            "pi_cpu": {
                "model_size": "tiny",
                "device": "cpu",
                "compute_type": "int8",
                "min_chunk": 0.5,
                "max_chunk": 5.0,
                "overlap": 0.4,
                "silence_timeout": 0.5,
                "beam_size": 1,
            },
            "gpu": {
                "model_size": "small",
                "device": "cuda",
                "compute_type": "float16",
                "min_chunk": 0.6,
                "max_chunk": 6.0,
                "overlap": 0.5,
                "silence_timeout": 0.7,
                "beam_size": 2,
            },
        }

        for profile, expected in expectations.items():
            with self.subTest(profile=profile):
                with loaded_audio_config({"TRANSCRIPTION_PROFILE": profile}) as config:
                    self.assertEqual(config.MODEL_SIZE, expected["model_size"])
                    self.assertEqual(config.DEVICE, expected["device"])
                    self.assertEqual(config.COMPUTE_TYPE, expected["compute_type"])
                    self.assertEqual(config.MIN_CHUNK_DURATION_SECONDS, expected["min_chunk"])
                    self.assertEqual(config.MAX_CHUNK_DURATION_SECONDS, expected["max_chunk"])
                    self.assertEqual(config.OVERLAP_DURATION_SECONDS, expected["overlap"])
                    self.assertEqual(
                        config.SILENCE_TIMEOUT_SECONDS,
                        expected["silence_timeout"],
                    )
                    self.assertEqual(config.BEAM_SIZE, expected["beam_size"])

    def test_unknown_profile_falls_back_to_balanced_realtime(self):
        with loaded_audio_config({"TRANSCRIPTION_PROFILE": "unknown"}) as config:
            self.assertEqual(config.TRANSCRIPTION_PROFILE, "balanced_realtime")
            self.assertEqual(config.MIN_CHUNK_DURATION_SECONDS, 0.6)
            self.assertEqual(config.MAX_CHUNK_DURATION_SECONDS, 6.0)
            self.assertEqual(config.BEAM_SIZE, 2)

    def test_explicit_env_overrides_profile_defaults_and_derived_byte_sizes(self):
        with loaded_audio_config(
            {
                "TRANSCRIPTION_PROFILE": "pi_cpu",
                "MODEL_SIZE": "base",
                "DEVICE": "cuda",
                "COMPUTE_TYPE": "int8_float16",
                "BEAM_SIZE": "3",
                "MIN_CHUNK_DURATION_SECONDS": "0.75",
                "MAX_CHUNK_DURATION_SECONDS": "7.5",
                "OVERLAP_DURATION_SECONDS": "0.25",
                "SILENCE_TIMEOUT_SECONDS": "0.8",
            }
        ) as config:
            bytes_per_second = config.SAMPLE_RATE * config.SAMPLE_WIDTH

            self.assertEqual(config.MODEL_SIZE, "base")
            self.assertEqual(config.DEVICE, "cuda")
            self.assertEqual(config.COMPUTE_TYPE, "int8_float16")
            self.assertEqual(config.BEAM_SIZE, 3)
            self.assertEqual(config.MIN_CHUNK_DURATION_SECONDS, 0.75)
            self.assertEqual(config.MAX_CHUNK_DURATION_SECONDS, 7.5)
            self.assertEqual(config.OVERLAP_DURATION_SECONDS, 0.25)
            self.assertEqual(config.SILENCE_TIMEOUT_SECONDS, 0.8)
            self.assertEqual(config.MIN_CHUNK_SIZE_BYTES, int(bytes_per_second * 0.75))
            self.assertEqual(config.MAX_CHUNK_SIZE_BYTES, int(bytes_per_second * 7.5))
            self.assertEqual(config.OVERLAP_SIZE_BYTES, int(bytes_per_second * 0.25))

    def test_stt_parameter_defaults_and_env_overrides(self):
        with loaded_audio_config() as config:
            self.assertEqual(config.SILERO_VAD_THRESHOLD, 0.5)
            self.assertEqual(config.SILERO_MIN_SPEECH_MS, 200)
            self.assertEqual(config.SILERO_MIN_SILENCE_MS, 300)
            self.assertEqual(config.SILERO_SPEECH_PAD_MS, 200)
            self.assertTrue(config.VAD_FILTER)
            self.assertEqual(config.COMPRESSION_RATIO_THRESHOLD, 2.2)
            self.assertEqual(config.LOG_PROB_THRESHOLD, -0.7)
            self.assertEqual(config.NO_SPEECH_THRESHOLD, 0.75)
            self.assertEqual(config.TEMPERATURE, (0.0,))

        with loaded_audio_config(
            {
                "SILERO_VAD_THRESHOLD": "0.45",
                "SILERO_MIN_SPEECH_MS": "150",
                "SILERO_MIN_SILENCE_MS": "500",
                "SILERO_SPEECH_PAD_MS": "250",
                "VAD_FILTER": "false",
                "COMPRESSION_RATIO_THRESHOLD": "2.4",
                "LOG_PROB_THRESHOLD": "-1.0",
                "NO_SPEECH_THRESHOLD": "0.8",
                "TEMPERATURE": "0.0,0.2",
            }
        ) as config:
            self.assertEqual(config.SILERO_VAD_THRESHOLD, 0.45)
            self.assertEqual(config.SILERO_MIN_SPEECH_MS, 150)
            self.assertEqual(config.SILERO_MIN_SILENCE_MS, 500)
            self.assertEqual(config.SILERO_SPEECH_PAD_MS, 250)
            self.assertFalse(config.VAD_FILTER)
            self.assertEqual(config.COMPRESSION_RATIO_THRESHOLD, 2.4)
            self.assertEqual(config.LOG_PROB_THRESHOLD, -1.0)
            self.assertEqual(config.NO_SPEECH_THRESHOLD, 0.8)
            self.assertEqual(config.TEMPERATURE, (0.0, 0.2))
            self.assertEqual(config.VAD_PARAMETERS["threshold"], 0.45)
            self.assertEqual(config.VAD_PARAMETERS["min_speech_duration_ms"], 150)
            self.assertEqual(config.VAD_PARAMETERS["min_silence_duration_ms"], 500)
            self.assertEqual(config.VAD_PARAMETERS["speech_pad_ms"], 250)


if __name__ == "__main__":
    unittest.main()
