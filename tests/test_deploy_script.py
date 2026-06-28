import importlib.util
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
DEPLOY_PATH = ROOT / "scripts" / "deploy.py"


def load_deploy_module():
    spec = importlib.util.spec_from_file_location("deploy", DEPLOY_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class DeployScriptTest(unittest.TestCase):
    def test_python_version_supports_project_minimum(self):
        deploy = load_deploy_module()

        self.assertTrue(deploy.is_supported_python((3, 11, 0)))
        self.assertTrue(deploy.is_supported_python((3, 12, 2)))
        self.assertFalse(deploy.is_supported_python((3, 10, 13)))

    def test_node_install_is_conditional_on_manifest_or_flag(self):
        deploy = load_deploy_module()

        self.assertFalse(deploy.should_prepare_node(False, False))
        self.assertTrue(deploy.should_prepare_node(True, False))
        self.assertTrue(deploy.should_prepare_node(False, True))

    def test_server_command_uses_venv_python_and_cpu_default(self):
        deploy = load_deploy_module()
        project = deploy.ProjectPaths(
            root=pathlib.Path("/repo"),
            corestt=pathlib.Path("/repo/CoreSTT"),
            venv=pathlib.Path("/repo/CoreSTT/.venv"),
        )

        command = deploy.build_server_command(project, "127.0.0.1", 8020, "cpu")

        self.assertEqual(command[1:], ["server.py", "--host", "127.0.0.1", "--port", "8020", "--device", "cpu"])
        self.assertIn(".venv", command[0])

    def test_force_reinstall_precedes_requirements_file_flag(self):
        deploy = load_deploy_module()
        project = deploy.ProjectPaths(
            root=pathlib.Path("/repo"),
            corestt=pathlib.Path("/repo/CoreSTT"),
            venv=pathlib.Path("/repo/CoreSTT/.venv"),
        )
        commands = []

        def record_command(command, cwd, dry_run=False):
            commands.append(command)

        deploy.run_command = record_command

        deploy.install_python_packages(
            project,
            pathlib.Path("/repo/CoreSTT/.venv/bin/python"),
            force_reinstall=True,
            dry_run=True,
        )

        package_command = commands[1]
        self.assertLess(package_command.index("--force-reinstall"), package_command.index("-r"))


if __name__ == "__main__":
    unittest.main()
