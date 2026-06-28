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
                self.assertIn('.venv/bin/python server.py --host "${HOST}" --port "${PORT}" --device "${DEVICE}"', text)

    def test_windows_script_follows_documented_windows_commands(self):
        text = read_script(WINDOWS_SCRIPT)

        self.assertIn("py -3.11", text)
        self.assertIn("-m venv .venv", text)
        self.assertIn(".venv\\Scripts\\python.exe -m pip install -r requirements.txt", text)
        self.assertIn(".venv\\Scripts\\python.exe server.py --host $HostAddress --port $Port --device $Device", text)

    def test_scripts_do_not_include_node_or_extra_python_runner(self):
        self.assertFalse((ROOT / "scripts" / "deploy.py").exists())
        for script in (MAC_SCRIPT, LINUX_SCRIPT, WINDOWS_SCRIPT):
            with self.subTest(script=script.name):
                self.assertNotIn("node", read_script(script).lower())


if __name__ == "__main__":
    unittest.main()
