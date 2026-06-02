from pathlib import Path
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SETTINGS_MODAL_PATH = PROJECT_ROOT / "frontend/src/components/Settings/SettingsModal.tsx"
CONFIG_API_PATH = PROJECT_ROOT / "frontend/src/services/configApi.ts"


class FrontendGuidedSttSettingsStaticTests(unittest.TestCase):
    def test_settings_modal_includes_guided_readonly_stt_tab(self):
        source = SETTINGS_MODAL_PATH.read_text()

        self.assertIn("{ id: 'stt', label: 'STT' }", source)
        self.assertIn("Transcription Engine", source)
        self.assertIn("Read-only backend configuration", source)
        self.assertIn("Refresh backend config", source)
        self.assertNotIn("Apply backend config", source)
        self.assertNotIn("Save STT settings", source)

    def test_settings_modal_includes_required_guidance_notes(self):
        source = SETTINGS_MODAL_PATH.read_text()

        expected_guidance = [
            "Fixed protocol values expected by backend and frontend.",
            "Profiles are presets; current app behavior is controlled by backend env config.",
            "Larger models may improve accuracy but need more memory and time.",
            "CPU usually uses int8; CUDA usually uses float16.",
            "Lower is faster; higher may improve accuracy with more latency.",
            "Shorter chunks respond faster; longer chunks give more context.",
            "Helps avoid clipped boundary words; too much can repeat text.",
            "Lower triggers sooner; higher waits for more complete phrases.",
            "Higher is stricter; lower catches quieter speech but may include noise.",
            "Speech/silence/pad values tune short-word capture and phrase splitting.",
            "More aggressive values reduce silence/repetition artifacts but can drop valid speech.",
            "RTF below 1.0 is faster than realtime; below 0.5 is better for responsive dictation.",
            "Not enabled because word timestamps are disabled.",
        ]

        for guidance in expected_guidance:
            with self.subTest(guidance=guidance):
                self.assertIn(guidance, source)

    def test_config_api_client_calls_existing_config_endpoint(self):
        source = CONFIG_API_PATH.read_text()

        self.assertIn("getBackendConfig", source)
        self.assertIn("`${API_URL}/config`", source)
        self.assertIn("BackendConfigResponse", source)


if __name__ == "__main__":
    unittest.main()
