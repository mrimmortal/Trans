import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
MAC_SCRIPT = ROOT / "scripts" / "deploy-macos.sh"
LINUX_SCRIPT = ROOT / "scripts" / "deploy-linux.sh"
WINDOWS_SCRIPT = ROOT / "scripts" / "deploy-windows.ps1"


def read_script(path):
    return path.read_text(encoding="utf-8")


class DeployScriptTest(unittest.TestCase):
    def test_mac_linux_and_windows_scripts_exist(self):
        self.assertTrue(MAC_SCRIPT.exists())
        self.assertTrue(LINUX_SCRIPT.exists())
        self.assertTrue(WINDOWS_SCRIPT.exists())

    def test_shell_scripts_follow_documented_unix_commands(self):
        for script in (MAC_SCRIPT, LINUX_SCRIPT):
            with self.subTest(script=script.name):
                text = read_script(script)
                self.assertIn("python3.11", text)
                self.assertIn("-m venv .venv", text)
                self.assertIn(".venv/bin/python -m pip install -r requirements.txt", text)
                self.assertIn('COMPUTE_TYPE="${COMPUTE_TYPE:-default}"', text)
                self.assertIn('.venv/bin/python server.py --host "${HOST}" --port "${PORT}" --device "${DEVICE}" --compute-type "${COMPUTE_TYPE}"', text)

    def test_windows_script_follows_documented_windows_commands(self):
        text = read_script(WINDOWS_SCRIPT)

        self.assertIn("py -3.11", text)
        self.assertIn("-m venv .venv", text)
        self.assertIn(".venv\\Scripts\\python.exe -m pip install -r requirements.txt", text)
        self.assertIn('[string]$ComputeType = "default"', text)
        self.assertIn(".venv\\Scripts\\python.exe server.py --host $HostAddress --port $Port --device $Device --compute-type $ComputeType", text)

    def test_scripts_do_not_include_node_or_extra_python_runner(self):
        self.assertFalse((ROOT / "scripts" / "deploy.py").exists())
        for script in (MAC_SCRIPT, LINUX_SCRIPT, WINDOWS_SCRIPT):
            with self.subTest(script=script.name):
                self.assertNotIn("node", read_script(script).lower())

    def test_scripts_create_virtualenv_only_when_missing(self):
        for script in (MAC_SCRIPT, LINUX_SCRIPT):
            with self.subTest(script=script.name):
                text = read_script(script)
                self.assertIn('if [[ ! -x ".venv/bin/python" ]]; then', text)
                self.assertIn('"${PYTHON_BIN}" -m venv .venv', text)

        windows_text = read_script(WINDOWS_SCRIPT)
        self.assertIn('if (-not (Test-Path ".venv\\Scripts\\python.exe"))', windows_text)
        self.assertIn("py -3.11 -m venv .venv", windows_text)


if __name__ == "__main__":
    unittest.main()
