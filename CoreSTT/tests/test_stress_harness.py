import argparse
import io
import math
import os
import subprocess
import sys
import unittest
import wave
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from urllib.error import URLError
from unittest.mock import MagicMock, patch

from protocol import decode_audio_packet
from tools.stress.harness import (
    ClientResult,
    aggregate_results,
    build_arg_parser,
    clamp_client_count,
    ensure_local_server,
    ensure_sample_wav,
    iter_wav_chunks,
    load_pcm_wav,
    make_audio_packet_bytes,
    record_microphone_wav,
    synthesize_pcm_s16le,
)
from tools.stress import run_linux, run_macos


class StressHarnessTest(unittest.TestCase):
    @staticmethod
    def _write_pcm_wav(path, frames=1600, sample_rate=16000, channels=1, width=2):
        with wave.open(str(path), "wb") as wav_file:
            wav_file.setnchannels(channels)
            wav_file.setsampwidth(width)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(b"\x01\x00" * frames * channels)

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
        self.assertIsNone(args.wav)
        self.assertFalse(args.wav_loop)

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

    def test_platform_runners_build_same_default_final_only_matrix(self):
        mac_args = run_macos.validate_args(run_macos.build_parser().parse_args([]))
        linux_args = run_linux.validate_args(run_linux.build_parser().parse_args([]))

        expected = [
            ("handshake", 25, 10.0),
            ("stream", 1, 120.0),
            ("stream", 2, 120.0),
            ("stream", 4, 120.0),
        ]
        self.assertEqual(run_macos.scenarios(mac_args), expected)
        self.assertEqual(run_linux.scenarios(linux_args), expected)

    def test_platform_runners_support_dry_run_without_platform_or_server(self):
        arguments = [
            "--dry-run",
            "--skip-handshake",
            "--clients",
            "1,4",
            "--duration",
            "5",
        ]

        with patch("builtins.print") as print_output:
            self.assertEqual(run_macos.main(arguments), 0)
            self.assertEqual(run_linux.main(arguments), 0)

        commands = [call.args[0] for call in print_output.call_args_list]
        server_commands = [command for command in commands if command.startswith("SERVER:")]
        harness_commands = [command for command in commands if not command.startswith("SERVER:")]
        self.assertEqual(len(server_commands), 2)
        self.assertEqual(len(harness_commands), 4)
        self.assertTrue(
            all("--no-realtime-transcription" in command for command in server_commands)
        )
        self.assertTrue(
            all("tools.stress.harness" in command for command in harness_commands)
        )
        self.assertTrue(all("--wav" in command for command in harness_commands))

    def test_platform_runner_rejects_invalid_client_matrix(self):
        with self.assertRaisesRegex(
            argparse.ArgumentTypeError,
            "positive integers",
        ):
            run_macos.parse_client_counts("1,0")

    def test_platform_runners_support_direct_file_execution(self):
        stress_dir = Path(__file__).resolve().parents[1] / "tools" / "stress"
        environment = dict(os.environ)
        environment["PYTHONDONTWRITEBYTECODE"] = "1"

        for script_name in ("run_macos.py", "run_linux.py"):
            result = subprocess.run(
                [
                    sys.executable,
                    script_name,
                    "--dry-run",
                    "--skip-handshake",
                    "--clients",
                    "1",
                    "--duration",
                    "1",
                ],
                cwd=stress_dir,
                env=environment,
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("tools.stress.harness", result.stdout)

    def test_platform_runners_report_unreachable_server_without_traceback(self):
        for runner, system_name in (
            (run_macos, "Darwin"),
            (run_linux, "Linux"),
        ):
            with TemporaryDirectory() as output_dir:
                with (
                    patch.object(runner.platform, "system", return_value=system_name),
                    patch.object(
                        runner,
                        "ensure_local_server",
                        side_effect=URLError("connection refused"),
                    ),
                    patch("sys.stderr", new_callable=io.StringIO) as stderr,
                ):
                    result = runner.main(
                        [
                            "--skip-handshake",
                            "--clients",
                            "1",
                            "--output-dir",
                            output_dir,
                        ]
                    )

            self.assertEqual(result, 2)
            self.assertIn("Cannot connect to the CoreSTT server", stderr.getvalue())
            self.assertNotIn("Traceback", stderr.getvalue())

    def test_platform_server_commands_are_final_only(self):
        mac_args = run_macos.validate_args(run_macos.build_parser().parse_args([]))
        linux_args = run_linux.validate_args(run_linux.build_parser().parse_args([]))

        mac_command = run_macos.server_command(mac_args)
        linux_command = run_linux.server_command(linux_args)

        self.assertIn("--no-realtime-transcription", mac_command)
        self.assertIn("--diagnostic-logging", mac_command)
        self.assertIn("cpu", mac_command)
        self.assertIn("int8", mac_command)
        self.assertIn("--no-realtime-transcription", linux_command)
        self.assertIn("--diagnostic-logging", linux_command)
        self.assertIn("cuda", linux_command)
        self.assertIn("float16", linux_command)

    def test_ensure_local_server_starts_and_stops_owned_process(self):
        process = MagicMock()
        process.poll.return_value = None
        with TemporaryDirectory() as output_dir:
            log_path = Path(output_dir) / "server.log"
            with (
                patch(
                    "tools.stress.harness.fetch_json",
                    side_effect=[URLError("connection refused"), {"ready": True, "ok": True}],
                ),
                patch("tools.stress.harness.subprocess.Popen", return_value=process) as popen,
            ):
                with ensure_local_server(
                    "ws://127.0.0.1:8020/ws/transcribe",
                    [sys.executable, "server.py"],
                    Path(output_dir),
                    log_path,
                    startup_timeout=1,
                ) as started:
                    self.assertTrue(started)

        popen.assert_called_once()
        process.terminate.assert_called_once()
        process.wait.assert_called_once_with(timeout=10)

    def test_ensure_local_server_leaves_existing_process_untouched(self):
        with (
            patch(
                "tools.stress.harness.fetch_json",
                return_value={"ready": True, "ok": True},
            ),
            patch("tools.stress.harness.subprocess.Popen") as popen,
        ):
            with ensure_local_server(
                "ws://127.0.0.1:8020/ws/transcribe",
                [sys.executable, "server.py"],
                Path.cwd(),
                Path.cwd() / "unused-server.log",
            ) as started:
                self.assertFalse(started)

        popen.assert_not_called()

    def test_ensure_local_server_rejects_remote_auto_start(self):
        with patch(
            "tools.stress.harness.fetch_json",
            side_effect=URLError("connection refused"),
        ):
            with self.assertRaisesRegex(RuntimeError, "limited to local URLs"):
                with ensure_local_server(
                    "ws://example.com:8020/ws/transcribe",
                    [sys.executable, "server.py"],
                    Path.cwd(),
                    Path.cwd() / "unused-server.log",
                ):
                    pass

    def test_ensure_local_server_reports_early_process_exit(self):
        process = MagicMock()
        process.poll.return_value = 1
        with TemporaryDirectory() as output_dir:
            log_path = Path(output_dir) / "server.log"
            with (
                patch(
                    "tools.stress.harness.fetch_json",
                    side_effect=URLError("connection refused"),
                ),
                patch("tools.stress.harness.subprocess.Popen", return_value=process),
            ):
                with self.assertRaisesRegex(RuntimeError, "exited with code 1"):
                    with ensure_local_server(
                        "ws://127.0.0.1:8020/ws/transcribe",
                        [sys.executable, "server.py"],
                        Path(output_dir),
                        log_path,
                        startup_timeout=1,
                    ):
                        pass

    def test_load_pcm_wav_and_chunking_preserve_audio(self):
        with TemporaryDirectory() as output_dir:
            path = Path(output_dir) / "sample.wav"
            self._write_pcm_wav(path, frames=1600)

            audio = load_pcm_wav(path)
            chunks = list(iter_wav_chunks(audio, chunk_ms=40))

        self.assertEqual(audio.sample_rate, 16000)
        self.assertEqual(audio.channels, 1)
        self.assertAlmostEqual(audio.duration_seconds, 0.1)
        self.assertEqual(b"".join(chunks), audio.pcm_bytes)
        self.assertEqual([len(chunk) for chunk in chunks], [1280, 1280, 640])

    def test_load_pcm_wav_rejects_non_16_bit_audio(self):
        with TemporaryDirectory() as output_dir:
            path = Path(output_dir) / "sample.wav"
            self._write_pcm_wav(path, frames=100, width=1)

            with self.assertRaisesRegex(ValueError, "16-bit"):
                load_pcm_wav(path)

    def test_ensure_sample_wav_records_only_after_confirmation(self):
        with TemporaryDirectory() as output_dir:
            path = Path(output_dir) / "sampleaudio.wav"

            def fake_record(target, **_kwargs):
                self._write_pcm_wav(target, frames=800)

            with patch(
                "tools.stress.harness.record_microphone_wav",
                side_effect=fake_record,
            ) as record:
                audio = ensure_sample_wav(
                    path,
                    record_seconds=1,
                    countdown_seconds=0,
                    input_func=lambda _prompt: "y",
                    print_func=lambda _message: None,
                    sleep_func=lambda _seconds: None,
                )

        record.assert_called_once()
        self.assertEqual(audio.frame_count, 800)

    def test_ensure_sample_wav_does_not_record_existing_file(self):
        with TemporaryDirectory() as output_dir:
            path = Path(output_dir) / "sampleaudio.wav"
            self._write_pcm_wav(path, frames=400)

            with patch("tools.stress.harness.record_microphone_wav") as record:
                audio = ensure_sample_wav(path)

        record.assert_not_called()
        self.assertEqual(audio.frame_count, 400)

    def test_aggregate_results_includes_final_transcripts(self):
        result = ClientResult(
            client_index=0,
            connected=True,
            final_texts=["known transcript"],
            audio_sent_seconds=10.0,
        )

        report = aggregate_results([result])

        self.assertEqual(
            report["finalTranscripts"],
            [
                {
                    "client": 0,
                    "audioSentSeconds": 10.0,
                    "finalMessages": 1,
                    "texts": ["known transcript"],
                    "timedOut": False,
                }
            ],
        )

    def test_record_microphone_wav_writes_pcm_audio(self):
        stream = MagicMock()
        stream.read.side_effect = lambda frames, **_kwargs: b"\x01\x00" * frames
        audio_interface = MagicMock()
        audio_interface.open.return_value = stream
        pyaudio_module = SimpleNamespace(
            paInt16=8,
            PyAudio=lambda: audio_interface,
        )

        with TemporaryDirectory() as output_dir:
            path = Path(output_dir) / "recorded.wav"
            with patch.dict(sys.modules, {"pyaudio": pyaudio_module}):
                record_microphone_wav(path, duration_seconds=0.1)
            audio = load_pcm_wav(path)

        self.assertEqual(audio.frame_count, 1600)
        stream.stop_stream.assert_called_once()
        stream.close.assert_called_once()
        audio_interface.terminate.assert_called_once()

    def test_soak_commands_loop_wav_audio(self):
        mac_args = run_macos.validate_args(run_macos.build_parser().parse_args([]))
        linux_args = run_linux.validate_args(run_linux.build_parser().parse_args([]))

        self.assertIn("--wav-loop", run_macos.harness_command(mac_args, "soak", 4, 30))
        self.assertIn("--wav-loop", run_linux.harness_command(linux_args, "soak", 4, 30))
        self.assertNotIn(
            "--wav-loop",
            run_macos.harness_command(mac_args, "stream", 1, 30),
        )


if __name__ == "__main__":
    unittest.main()
