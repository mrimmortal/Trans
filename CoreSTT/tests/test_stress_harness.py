import math
import unittest

from protocol import decode_audio_packet
from tools.stress.harness import (
    build_arg_parser,
    clamp_client_count,
    make_audio_packet_bytes,
    synthesize_pcm_s16le,
)


class StressHarnessTest(unittest.TestCase):
    def test_build_arg_parser_applies_expected_defaults(self):
        args = build_arg_parser().parse_args(["--url", "ws://127.0.0.1:8020/ws/transcribe"])

        self.assertEqual(args.url, "ws://127.0.0.1:8020/ws/transcribe")
        self.assertEqual(args.clients, 1)
        self.assertEqual(args.duration, 10.0)
        self.assertEqual(args.mode, "stream")
        self.assertEqual(args.sample_rate, 16000)
        self.assertEqual(args.channels, 1)
        self.assertEqual(args.chunk_ms, 100)
        self.assertEqual(args.ping_interval, 5.0)
        self.assertEqual(args.connect_stagger_ms, 0)
        self.assertFalse(args.metrics)

    def test_clamp_client_count_rejects_non_positive_values(self):
        with self.assertRaisesRegex(ValueError, "positive integer"):
            clamp_client_count(0)

    def test_synthesize_pcm_s16le_returns_aligned_bytes_for_requested_duration(self):
        payload = synthesize_pcm_s16le(
            sample_rate=16000,
            channels=1,
            duration_seconds=0.25,
            frequency_hz=440.0,
            amplitude=0.5,
        )

        self.assertEqual(len(payload), int(16000 * 0.25) * 2)
        self.assertNotEqual(payload, b"\x00" * len(payload))

    def test_make_audio_packet_bytes_uses_existing_protocol_format(self):
        packet = make_audio_packet_bytes(
            sample_rate=16000,
            channels=1,
            pcm_bytes=b"\x00\x00\x01\x00",
        )

        decoded = decode_audio_packet(packet)

        self.assertEqual(decoded.metadata["sampleRate"], 16000)
        self.assertEqual(decoded.metadata["channels"], 1)
        self.assertEqual(decoded.metadata["format"], "pcm_s16le")
        self.assertEqual(decoded.audio, b"\x00\x00\x01\x00")

    def test_synthesize_pcm_s16le_rejects_out_of_range_amplitude(self):
        with self.assertRaisesRegex(ValueError, "between 0.0 and 1.0"):
            synthesize_pcm_s16le(
                sample_rate=16000,
                channels=1,
                duration_seconds=0.1,
                frequency_hz=440.0,
                amplitude=1.5,
            )


if __name__ == "__main__":
    unittest.main()
