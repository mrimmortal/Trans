import unittest

from app.audio_config import AudioConfig


class AudioConfigRealtimeTests(unittest.TestCase):
    def test_balanced_realtime_defaults_reduce_pause_latency(self):
        self.assertEqual(AudioConfig.TRANSCRIPTION_PROFILE, "balanced_realtime")
        self.assertEqual(AudioConfig.MIN_CHUNK_DURATION_SECONDS, 0.6)
        self.assertEqual(AudioConfig.SILENCE_TIMEOUT_SECONDS, 0.7)
        self.assertEqual(AudioConfig.MAX_CHUNK_DURATION_SECONDS, 6.0)
        self.assertEqual(AudioConfig.BEAM_SIZE, 2)

    def test_buffer_byte_sizes_follow_duration_settings(self):
        bytes_per_second = AudioConfig.SAMPLE_RATE * AudioConfig.SAMPLE_WIDTH

        self.assertEqual(
            AudioConfig.MIN_CHUNK_SIZE_BYTES,
            int(bytes_per_second * AudioConfig.MIN_CHUNK_DURATION_SECONDS),
        )
        self.assertEqual(
            AudioConfig.MAX_CHUNK_SIZE_BYTES,
            int(bytes_per_second * AudioConfig.MAX_CHUNK_DURATION_SECONDS),
        )
        self.assertEqual(
            AudioConfig.OVERLAP_SIZE_BYTES,
            int(bytes_per_second * AudioConfig.OVERLAP_DURATION_SECONDS),
        )


if __name__ == "__main__":
    unittest.main()
