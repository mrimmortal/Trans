"""Run the supported final-only CoreSTT stress matrix on NVIDIA Linux."""

import argparse
import json
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlsplit

try:
    from tools.stress.harness import (
        derive_http_url,
        ensure_local_server,
        ensure_sample_wav,
        fetch_json,
    )
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from tools.stress.harness import (
        derive_http_url,
        ensure_local_server,
        ensure_sample_wav,
        fetch_json,
    )


CORE_DIR = Path(__file__).resolve().parents[2]
DEFAULT_SAMPLE_WAV = Path(__file__).resolve().parent / "sampleaudio.wav"


def parse_client_counts(value):
    try:
        counts = tuple(int(item.strip()) for item in value.split(","))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("clients must be comma-separated integers") from exc
    if not counts or any(count <= 0 for count in counts):
        raise argparse.ArgumentTypeError("clients must contain positive integers")
    return counts


def build_parser():
    parser = argparse.ArgumentParser(
        description="Run the final-only CoreSTT stress matrix on NVIDIA Linux.",
    )
    parser.add_argument(
        "--url",
        default="ws://127.0.0.1:8020/ws/transcribe",
        help="WebSocket endpoint for an already-running final-only server.",
    )
    parser.add_argument("--output-dir", type=Path, default=CORE_DIR / "benchmark-results")
    parser.add_argument("--clients", type=parse_client_counts, default=(1, 2, 4))
    parser.add_argument("--duration", type=float, default=120.0)
    parser.add_argument("--handshake-clients", type=int, default=25)
    parser.add_argument("--handshake-duration", type=float, default=10.0)
    parser.add_argument("--skip-handshake", action="store_true")
    parser.add_argument("--include-soak", action="store_true")
    parser.add_argument("--soak-clients", type=int, default=4)
    parser.add_argument("--soak-duration", type=float, default=1800.0)
    parser.add_argument("--sample-rate", type=int, default=48000)
    parser.add_argument("--channels", type=int, default=1)
    parser.add_argument("--chunk-ms", type=int, default=40)
    parser.add_argument("--ping-interval", type=float, default=2.0)
    parser.add_argument("--connect-stagger-ms", type=int, default=100)
    parser.add_argument("--skip-gpu-check", action="store_true")
    parser.add_argument(
        "--auto-start-server",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Start a local final-only server when the configured URL is unavailable.",
    )
    parser.add_argument("--server-start-timeout", type=float, default=300.0)
    parser.add_argument("--server-gpu-device-index", type=int, default=0)
    parser.add_argument("--server-compute-type", default="float16")
    parser.add_argument("--wav", type=Path, default=DEFAULT_SAMPLE_WAV)
    parser.add_argument(
        "--record-if-missing",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    parser.add_argument("--record-seconds", type=float, default=30.0)
    parser.add_argument("--input-device-index", type=int)
    parser.add_argument("--final-timeout", type=float, default=60.0)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print commands without checking the platform, server, or writing reports.",
    )
    return parser


def validate_args(args):
    positive_values = {
        "duration": args.duration,
        "handshake_clients": args.handshake_clients,
        "handshake_duration": args.handshake_duration,
        "soak_clients": args.soak_clients,
        "soak_duration": args.soak_duration,
        "sample_rate": args.sample_rate,
        "channels": args.channels,
        "chunk_ms": args.chunk_ms,
        "ping_interval": args.ping_interval,
        "server_start_timeout": args.server_start_timeout,
        "record_seconds": args.record_seconds,
        "final_timeout": args.final_timeout,
    }
    for name, value in positive_values.items():
        if value <= 0:
            raise ValueError(f"{name} must be greater than zero")
    if args.connect_stagger_ms < 0:
        raise ValueError("connect_stagger_ms must be non-negative")
    if args.server_gpu_device_index < 0:
        raise ValueError("server_gpu_device_index must be non-negative")
    if args.input_device_index is not None and args.input_device_index < 0:
        raise ValueError("input_device_index must be non-negative")
    return args


def scenarios(args):
    selected = []
    if not args.skip_handshake:
        selected.append(("handshake", args.handshake_clients, args.handshake_duration))
    selected.extend(("stream", clients, args.duration) for clients in args.clients)
    if args.include_soak:
        selected.append(("soak", args.soak_clients, args.soak_duration))
    return selected


def harness_command(args, mode, clients, duration):
    harness_mode = "handshake" if mode == "handshake" else "stream"
    command = [
        sys.executable,
        "-m",
        "tools.stress.harness",
        "--url",
        args.url,
        "--clients",
        str(clients),
        "--duration",
        str(duration),
        "--mode",
        harness_mode,
        "--sample-rate",
        str(args.sample_rate),
        "--channels",
        str(args.channels),
        "--chunk-ms",
        str(args.chunk_ms),
        "--ping-interval",
        str(args.ping_interval),
        "--connect-stagger-ms",
        str(args.connect_stagger_ms),
        "--metrics",
        "--report-json",
        "--wav",
        str(args.wav.expanduser().resolve()),
        "--final-timeout",
        str(args.final_timeout),
    ]
    if mode == "soak":
        command.append("--wav-loop")
    return command


def server_command(args):
    parts = urlsplit(args.url)
    port = parts.port or (443 if parts.scheme == "wss" else 80)
    host = parts.hostname or "127.0.0.1"
    return [
        sys.executable,
        "server.py",
        "--host",
        host,
        "--port",
        str(port),
        "--device",
        "cuda",
        "--gpu-device-index",
        str(args.server_gpu_device_index),
        "--compute-type",
        args.server_compute_type,
        "--no-realtime-transcription",
        "--diagnostic-logging",
    ]


def verify_final_only_server(url):
    config = fetch_json(derive_http_url(url, "/api/config"))
    health = fetch_json(derive_http_url(url, "/health"))
    if config.get("settings", {}).get("realtime_transcription_enabled") is not False:
        raise RuntimeError("server must be started with --no-realtime-transcription")
    if health.get("scheduler", {}).get("mode") != "final-only":
        raise RuntimeError("server scheduler is not reporting final-only mode")
    if not health.get("ok"):
        raise RuntimeError("server health check is not OK")
    return {"config": config, "health": health}


def nvidia_metadata(skip_gpu_check):
    nvidia_smi = shutil.which("nvidia-smi")
    if nvidia_smi is None:
        if skip_gpu_check:
            return {"available": False, "reason": "nvidia-smi not found"}
        raise RuntimeError("nvidia-smi is required; use --skip-gpu-check to bypass")
    command = [
        nvidia_smi,
        "--query-gpu=name,driver_version,memory.total,memory.free,utilization.gpu",
        "--format=csv,noheader,nounits",
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        if skip_gpu_check:
            return {"available": False, "reason": result.stderr.strip()}
        raise RuntimeError(f"nvidia-smi failed: {result.stderr.strip()}")
    return {"available": True, "query": result.stdout.strip().splitlines()}


def linux_metadata(skip_gpu_check):
    return {
        "platform": platform.platform(),
        "python": platform.python_version(),
        "machine": platform.machine(),
        "gpu": nvidia_metadata(skip_gpu_check),
    }


def run_matrix(args):
    selected = scenarios(args)
    commands = [harness_command(args, *scenario) for scenario in selected]
    startup_command = server_command(args)
    if args.dry_run:
        print("SERVER: " + " ".join(startup_command))
        for command in commands:
            print(" ".join(command))
        return 0

    if platform.system() != "Linux":
        raise RuntimeError("this runner must be executed on Linux")

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = args.output_dir.expanduser().resolve() / f"linux-final-only-{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=False)

    with ensure_local_server(
        args.url,
        startup_command,
        CORE_DIR,
        run_dir / "server.log",
        startup_timeout=args.server_start_timeout,
        auto_start=args.auto_start_server,
    ) as server_started:
        preflight = verify_final_only_server(args.url)
        wav_audio = ensure_sample_wav(
            args.wav,
            record_if_missing=args.record_if_missing,
            record_seconds=args.record_seconds,
            input_device_index=args.input_device_index,
        )
        (run_dir / "environment.json").write_text(
            json.dumps(
                {
                    "system": linux_metadata(args.skip_gpu_check),
                    "server": preflight,
                    "serverAutoStarted": server_started,
                    "wav": {
                        "name": wav_audio.path.name,
                        "sampleRate": wav_audio.sample_rate,
                        "channels": wav_audio.channels,
                        "durationSeconds": round(wav_audio.duration_seconds, 3),
                    },
                },
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )

        failed = False
        for (mode, clients, _duration), command in zip(selected, commands):
            report_path = run_dir / f"{mode}-{clients}-clients.json"
            print(f"Running {mode} with {clients} client(s): {report_path}")
            result = subprocess.run(
                command,
                cwd=CORE_DIR,
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0:
                failed = True
                report_path.with_suffix(".stderr.txt").write_text(
                    result.stderr,
                    encoding="utf-8",
                )
                continue
            report = json.loads(result.stdout)
            report["scenario"] = {
                "platform": "linux-nvidia",
                "mode": mode,
                "clients": clients,
                "audio": "wav",
                "wavName": wav_audio.path.name,
                "wavDurationSeconds": round(wav_audio.duration_seconds, 3),
                "serverMetricsCumulativeWithinRun": True,
            }
            report_path.write_text(
                json.dumps(report, indent=2, sort_keys=True),
                encoding="utf-8",
            )
            if result.stderr:
                report_path.with_suffix(".stderr.txt").write_text(
                    result.stderr,
                    encoding="utf-8",
                )
            failed = failed or bool(
                report.get("clientsConnected") != report.get("clientsRequested")
                or report.get("errorMessages")
                or report.get("exceptions")
            )

        (run_dir / "nvidia-after.json").write_text(
            json.dumps(nvidia_metadata(args.skip_gpu_check), indent=2, sort_keys=True),
            encoding="utf-8",
        )
    print(f"Reports written to {run_dir}")
    return 1 if failed else 0


def main(argv=None):
    try:
        args = validate_args(build_parser().parse_args(argv))
        return run_matrix(args)
    except URLError as exc:
        print(
            "Cannot connect to the CoreSTT server. Start the final-only server "
            "on 127.0.0.1:8020, then rerun this command. "
            f"Connection error: {exc.reason}",
            file=sys.stderr,
        )
        return 2
    except (RuntimeError, ValueError) as exc:
        print(f"Harness preflight failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
