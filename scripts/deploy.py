#!/usr/bin/env python3
"""Set up and run the CoreSTT demo server."""

from __future__ import annotations

import argparse
import dataclasses
import os
import pathlib
import shutil
import subprocess
import sys


MIN_PYTHON = (3, 11)
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8020
DEFAULT_DEVICE = "cpu"


@dataclasses.dataclass(frozen=True)
class ProjectPaths:
    root: pathlib.Path
    corestt: pathlib.Path
    venv: pathlib.Path


def is_supported_python(version_info: tuple[int, int, int] | tuple[int, int]) -> bool:
    return tuple(version_info[:2]) >= MIN_PYTHON


def should_prepare_node(package_json_exists: bool, install_node: bool) -> bool:
    return package_json_exists or install_node


def venv_python_path(project: ProjectPaths) -> pathlib.Path:
    if os.name == "nt":
        return project.venv / "Scripts" / "python.exe"
    return project.venv / "bin" / "python"


def build_server_command(
    project: ProjectPaths,
    host: str,
    port: int,
    device: str,
    no_model_warmup: bool = False,
) -> list[str]:
    command = [
        str(venv_python_path(project)),
        "server.py",
        "--host",
        host,
        "--port",
        str(port),
        "--device",
        device,
    ]
    if no_model_warmup:
        command.append("--no-model-warmup")
    return command


def print_step(message: str) -> None:
    print(f"\n==> {message}", flush=True)


def run_command(command: list[str], cwd: pathlib.Path, dry_run: bool = False) -> None:
    printable = " ".join(command)
    print(f"$ {printable}", flush=True)
    if dry_run:
        return
    subprocess.run(command, cwd=str(cwd), check=True)


def project_paths() -> ProjectPaths:
    root = pathlib.Path(__file__).resolve().parents[1]
    corestt = root / "CoreSTT"
    requirements = corestt / "requirements.txt"
    server = corestt / "server.py"
    if not requirements.exists() or not server.exists():
        raise SystemExit(f"Could not find CoreSTT project files under {corestt}")
    return ProjectPaths(root=root, corestt=corestt, venv=corestt / ".venv")


def command_exists(command: str) -> bool:
    return shutil.which(command) is not None


def find_supported_python() -> str | None:
    candidates = [
        os.environ.get("PYTHON"),
        sys.executable,
        "python3.13",
        "python3.12",
        "python3.11",
        "python3",
        "python",
    ]
    seen: set[str] = set()
    for candidate in candidates:
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        if shutil.which(candidate) is None and not pathlib.Path(candidate).exists():
            continue
        probe = [
            candidate,
            "-c",
            "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')",
        ]
        try:
            result = subprocess.run(
                probe,
                check=True,
                capture_output=True,
                text=True,
            )
        except (OSError, subprocess.CalledProcessError):
            continue
        version = tuple(int(part) for part in result.stdout.strip().split(".")[:3])
        if is_supported_python(version):
            return candidate
    return None


def ensure_supported_python() -> str:
    if is_supported_python(sys.version_info):
        return sys.executable

    supported = find_supported_python()
    if supported and pathlib.Path(supported).resolve() != pathlib.Path(sys.executable).resolve():
        os.execv(supported, [supported, *sys.argv])

    raise SystemExit(
        "Python 3.11 or newer is required. Install a supported Python first, "
        "then rerun the macOS or Linux deployment script."
    )


def ensure_virtualenv(project: ProjectPaths, python_executable: str, dry_run: bool) -> pathlib.Path:
    python_in_venv = venv_python_path(project)
    if python_in_venv.exists():
        print_step(f"Using existing virtual environment: {project.venv}")
        return python_in_venv

    print_step(f"Creating virtual environment: {project.venv}")
    run_command([python_executable, "-m", "venv", str(project.venv)], project.corestt, dry_run=dry_run)
    return python_in_venv


def install_python_packages(
    project: ProjectPaths,
    python_in_venv: pathlib.Path,
    force_reinstall: bool,
    dry_run: bool,
) -> None:
    requirements = project.corestt / "requirements.txt"
    print_step("Installing Python package tooling")
    run_command(
        [str(python_in_venv), "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"],
        project.corestt,
        dry_run=dry_run,
    )

    print_step("Installing CoreSTT Python packages")
    command = [str(python_in_venv), "-m", "pip", "install", "-r", str(requirements)]
    if force_reinstall:
        command.insert(4, "--force-reinstall")
    try:
        run_command(command, project.corestt, dry_run=dry_run)
    except subprocess.CalledProcessError as exc:
        print(
            "\nPython package installation failed. If the failure mentions PyAudio or "
            "PortAudio, install the OS prerequisite first, then rerun this script:\n"
            "  macOS: brew install portaudio\n"
            "  Debian/Ubuntu: sudo apt install portaudio19-dev python3-dev build-essential\n"
            "  Fedora: sudo dnf install portaudio-devel python3-devel gcc\n"
            "  Arch: sudo pacman -S portaudio base-devel\n",
            file=sys.stderr,
        )
        raise exc


def install_node_packages_if_needed(project: ProjectPaths, dry_run: bool) -> None:
    package_json = project.root / "package.json"
    if not package_json.exists():
        print_step("No package.json found; skipping Node package install")
        return

    if not command_exists("npm"):
        raise SystemExit("package.json exists, but npm was not found. Install Node.js, then rerun.")

    print_step("Installing Node packages")
    install_command = ["npm", "ci"] if (project.root / "package-lock.json").exists() else ["npm", "install"]
    run_command(install_command, project.root, dry_run=dry_run)


def report_node_status(project: ProjectPaths, install_node: bool, dry_run: bool) -> None:
    package_json_exists = (project.root / "package.json").exists()
    if not should_prepare_node(package_json_exists, install_node):
        print_step("Node.js is not required for this checkout; skipping Node setup")
        return

    if command_exists("node"):
        version = subprocess.run(["node", "--version"], capture_output=True, text=True, check=False)
        print_step(f"Node.js available: {version.stdout.strip() or 'version unknown'}")
    else:
        raise SystemExit(
            "Node.js was requested or package.json exists, but node was not found. "
            "Use scripts/deploy-macos.sh --install-node --yes or "
            "scripts/deploy-linux.sh --install-node --yes to install it when supported."
        )

    install_node_packages_if_needed(project, dry_run=dry_run)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Set up and run the CoreSTT server.")
    parser.add_argument("--setup-only", action="store_true", help="Install prerequisites and packages without starting the server.")
    parser.add_argument("--run-only", action="store_true", help="Skip package installation and start the server.")
    parser.add_argument("--host", default=DEFAULT_HOST, help=f"Server host. Default: {DEFAULT_HOST}")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"Server port. Default: {DEFAULT_PORT}")
    parser.add_argument("--device", default=DEFAULT_DEVICE, help=f"CoreSTT device. Default: {DEFAULT_DEVICE}")
    parser.add_argument("--force-reinstall", action="store_true", help="Force reinstall Python packages.")
    parser.add_argument("--install-node", action="store_true", help="Require Node.js setup even if this checkout has no package.json.")
    parser.add_argument("--no-model-warmup", action="store_true", help="Pass --no-model-warmup to the CoreSTT server.")
    parser.add_argument("--dry-run", action="store_true", help="Print commands without running them.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    if args.setup_only and args.run_only:
        raise SystemExit("--setup-only and --run-only cannot be used together.")

    project = project_paths()
    python_executable = ensure_supported_python()
    python_in_venv = ensure_virtualenv(project, python_executable, dry_run=args.dry_run)

    if not args.run_only:
        install_python_packages(project, python_in_venv, args.force_reinstall, dry_run=args.dry_run)
        report_node_status(project, args.install_node, dry_run=args.dry_run)

    if args.setup_only:
        print_step("Setup complete")
        return 0

    print_step(f"Starting CoreSTT server at http://{args.host}:{args.port}")
    run_command(
        build_server_command(project, args.host, args.port, args.device, args.no_model_warmup),
        project.corestt,
        dry_run=args.dry_run,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
