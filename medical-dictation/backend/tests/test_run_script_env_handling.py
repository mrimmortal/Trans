import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class RunScriptEnvHandlingTests(unittest.TestCase):
    def test_mac_dev_backend_env_uses_example_fallback(self):
        source = (PROJECT_ROOT / "scripts/run.sh").read_text(encoding="utf-8")

        self.assertIn('load_env "$BACKEND_DIR/.env.mac" "$BACKEND_DIR/.env.example"', source)

    def test_uat_check_backend_env_uses_example_fallback(self):
        source = (PROJECT_ROOT / "scripts/run.sh").read_text(encoding="utf-8")

        self.assertIn('load_env "$BACKEND_DIR/.env.uat" "$BACKEND_DIR/.env.example"', source)

    def test_mac_script_includes_prod_check(self):
        source = (PROJECT_ROOT / "scripts/run.sh").read_text(encoding="utf-8")

        self.assertIn("prod-check", source)
        self.assertIn('load_env "$BACKEND_DIR/.env.prod" "$BACKEND_DIR/.env.example"', source)

    def test_windows_dev_backend_env_uses_example_fallback(self):
        source = (PROJECT_ROOT / "scripts/run.ps1").read_text(encoding="utf-8")

        self.assertIn('Import-EnvFile (Join-Path $BackendDir ".env.windows") (Join-Path $BackendDir ".env.example")', source)

    def test_windows_script_includes_dev_uat_and_prod_commands(self):
        source = (PROJECT_ROOT / "scripts/run.ps1").read_text(encoding="utf-8")

        self.assertIn('[ValidateSet("win-dev", "uat-win", "prod-win", "help")]', source)


if __name__ == "__main__":
    unittest.main()
