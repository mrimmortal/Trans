from pathlib import Path
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
AUDIO_RECORDER_PATH = PROJECT_ROOT / "frontend/src/hooks/useAudioRecorder.ts"


class FrontendAudioRecorderStaticTests(unittest.TestCase):
    def test_microphone_constraints_request_int16_friendly_capture(self):
        source = AUDIO_RECORDER_PATH.read_text()

        self.assertIn("channelCount: channelCount", source)
        self.assertIn("sampleRate: { ideal: sampleRate }", source)
        self.assertIn("sampleSize: 16", source)
        self.assertIn("echoCancellation: true", source)
        self.assertIn("noiseSuppression: true", source)
        self.assertIn("autoGainControl: true", source)

    def test_pcm_conversion_outputs_little_endian_int16(self):
        source = AUDIO_RECORDER_PATH.read_text()

        self.assertIn("new ArrayBuffer(float32Array.length * 2)", source)
        self.assertIn("view.setInt16(i * 2", source)
        self.assertIn("true);", source)


if __name__ == "__main__":
    unittest.main()
