import unittest

from protocol import (
    AudioPacketError,
    decode_audio_packet,
    encode_audio_packet,
    normalize_engine_name,
    parse_json_object,
    require_positive_int,
)


class ServerProtocolTest(unittest.TestCase):
    def test_audio_packet_round_trip_preserves_metadata_and_audio(self):
        packet = encode_audio_packet(
            {"sampleRate": 48000, "channels": 1, "format": "pcm_s16le"},
            b"\x01\x00\x02\x00",
        )

        decoded = decode_audio_packet(packet)

        self.assertEqual(
            decoded.metadata,
            {
                "sampleRate": 48000,
                "channels": 1,
                "format": "pcm_s16le",
            },
        )
        self.assertEqual(decoded.audio, b"\x01\x00\x02\x00")

    def test_decode_audio_packet_rejects_incomplete_metadata(self):
        with self.assertRaisesRegex(AudioPacketError, "metadata is incomplete"):
            decode_audio_packet(b"\x08\x00\x00\x00{}")

    def test_require_positive_int_rejects_bool(self):
        with self.assertRaisesRegex(AudioPacketError, "sampleRate"):
            require_positive_int({"sampleRate": True}, "sampleRate")

    def test_parse_json_object_requires_object(self):
        with self.assertRaisesRegex(ValueError, "decode to a JSON object"):
            parse_json_object("[1, 2, 3]", "--engine-options")

    def test_normalize_engine_name_matches_factory_names(self):
        self.assertEqual(normalize_engine_name("faster-whisper"), "faster_whisper")


if __name__ == "__main__":
    unittest.main()
