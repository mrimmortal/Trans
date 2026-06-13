import argparse
import asyncio
import json
import math
import statistics
import struct
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlsplit, urlunsplit

try:
    from protocol import encode_audio_packet
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from protocol import encode_audio_packet

import websockets
from websockets.exceptions import ConnectionClosed


DEFAULT_SAMPLE_RATE = 16000
DEFAULT_CHANNELS = 1
DEFAULT_CHUNK_MS = 100
DEFAULT_PING_INTERVAL = 5.0
DEFAULT_DURATION = 10.0


def clamp_client_count(value):
    value = int(value)
    if value <= 0:
        raise ValueError("client count must be a positive integer")
    return value


def non_negative_float(value, name):
    value = float(value)
    if value < 0:
        raise ValueError(f"{name} must be non-negative")
    return value


def positive_float(value, name):
    value = float(value)
    if value <= 0:
        raise ValueError(f"{name} must be greater than zero")
    return value


def synthesize_pcm_s16le(sample_rate, channels, duration_seconds, frequency_hz, amplitude):
    sample_rate = int(sample_rate)
    channels = int(channels)
    duration_seconds = float(duration_seconds)
    frequency_hz = float(frequency_hz)
    amplitude = float(amplitude)

    if sample_rate <= 0:
        raise ValueError("sample_rate must be positive")
    if channels <= 0:
        raise ValueError("channels must be positive")
    if duration_seconds <= 0:
        raise ValueError("duration_seconds must be positive")
    if frequency_hz <= 0:
        raise ValueError("frequency_hz must be positive")
    if not 0.0 <= amplitude <= 1.0:
        raise ValueError("amplitude must be between 0.0 and 1.0")

    total_frames = max(1, int(round(sample_rate * duration_seconds)))
    peak = int(round(amplitude * 32767))
    buffer = bytearray(total_frames * channels * 2)
    for frame_index in range(total_frames):
        sample = int(round(peak * math.sin((2.0 * math.pi * frequency_hz * frame_index) / sample_rate)))
        offset = frame_index * channels * 2
        for channel_index in range(channels):
            struct.pack_into("<h", buffer, offset + (channel_index * 2), sample)
    return bytes(buffer)


def make_audio_packet_bytes(sample_rate, channels, pcm_bytes):
    return encode_audio_packet(
        {
            "sampleRate": int(sample_rate),
            "channels": int(channels),
            "format": "pcm_s16le",
        },
        pcm_bytes,
    )


def build_arg_parser():
    parser = argparse.ArgumentParser(
        description="Stress and soak test the CoreSTT websocket service.",
    )
    parser.add_argument("--url", required=True, help="WebSocket URL, for example ws://127.0.0.1:8020/ws/transcribe")
    parser.add_argument("--clients", type=int, default=1, help="Concurrent websocket clients to open.")
    parser.add_argument("--duration", type=float, default=DEFAULT_DURATION, help="How long each client should stay active.")
    parser.add_argument("--mode", choices=("handshake", "stream"), default="stream", help="Handshake-only sockets or audio streaming sockets.")
    parser.add_argument("--sample-rate", type=int, default=DEFAULT_SAMPLE_RATE, help="Synthetic PCM sample rate.")
    parser.add_argument("--channels", type=int, default=DEFAULT_CHANNELS, help="Synthetic PCM channel count.")
    parser.add_argument("--chunk-ms", type=int, default=DEFAULT_CHUNK_MS, help="Synthetic audio chunk duration in milliseconds.")
    parser.add_argument("--ping-interval", type=float, default=DEFAULT_PING_INTERVAL, help="Seconds between ping messages.")
    parser.add_argument("--connect-stagger-ms", type=int, default=0, help="Delay between client connection starts.")
    parser.add_argument("--audio-frequency-hz", type=float, default=440.0, help="Sine wave frequency for synthetic audio.")
    parser.add_argument("--audio-amplitude", type=float, default=0.2, help="Sine wave amplitude between 0.0 and 1.0.")
    parser.add_argument("--startup-timeout", type=float, default=20.0, help="Seconds to wait for hello/ready before continuing.")
    parser.add_argument("--metrics", action="store_true", help="Fetch /health and /api/metrics after the websocket run.")
    parser.add_argument("--report-json", action="store_true", help="Emit the aggregate report as JSON.")
    return parser


def validate_args(args):
    args.clients = clamp_client_count(args.clients)
    args.duration = non_negative_float(args.duration, "duration")
    args.sample_rate = int(args.sample_rate)
    args.channels = int(args.channels)
    args.chunk_ms = int(args.chunk_ms)
    args.ping_interval = positive_float(args.ping_interval, "ping_interval")
    args.connect_stagger_ms = max(0, int(args.connect_stagger_ms))
    args.audio_frequency_hz = positive_float(args.audio_frequency_hz, "audio_frequency_hz")
    args.audio_amplitude = float(args.audio_amplitude)
    if not 0.0 <= args.audio_amplitude <= 1.0:
        raise ValueError("audio_amplitude must be between 0.0 and 1.0")
    args.startup_timeout = positive_float(args.startup_timeout, "startup_timeout")
    if args.chunk_ms <= 0:
        raise ValueError("chunk_ms must be positive")
    return args


def percentile(values, pct):
    if not values:
        return None
    if len(values) == 1:
        return float(values[0])
    rank = (len(values) - 1) * pct
    lower = math.floor(rank)
    upper = math.ceil(rank)
    if lower == upper:
        return float(values[lower])
    lower_value = values[lower]
    upper_value = values[upper]
    return float(lower_value + ((upper_value - lower_value) * (rank - lower)))


def summarize_latencies(values):
    if not values:
        return None
    ordered = sorted(float(value) for value in values)
    return {
        "count": len(ordered),
        "minMs": round(ordered[0], 2),
        "avgMs": round(statistics.fmean(ordered), 2),
        "p95Ms": round(percentile(ordered, 0.95), 2),
        "maxMs": round(ordered[-1], 2),
    }


def derive_http_url(websocket_url, path):
    parts = urlsplit(websocket_url)
    scheme = "https" if parts.scheme == "wss" else "http"
    return urlunsplit((scheme, parts.netloc, path, "", ""))


def fetch_json(url):
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


@dataclass
class ClientResult:
    client_index: int
    connected: bool = False
    hello_received: bool = False
    ready_received: bool = False
    messages: Counter = field(default_factory=Counter)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    ready_latency_ms: Optional[float] = None
    pong_latencies_ms: List[float] = field(default_factory=list)
    disconnect_code: Optional[int] = None
    disconnect_reason: Optional[str] = None
    exception: Optional[str] = None


class ClientState:
    def __init__(self, result, startup_timeout):
        self.result = result
        self.connect_started_at = time.perf_counter()
        self.hello_event = asyncio.Event()
        self.ready_event = asyncio.Event()
        self.receiver_done = asyncio.Event()
        self.pending_ping_sent_at = None
        self.startup_timeout = startup_timeout


async def receive_messages(websocket, state):
    try:
        while True:
            message = await websocket.recv()
            if isinstance(message, bytes):
                state.result.messages["binary"] += 1
                continue
            try:
                data = json.loads(message)
            except json.JSONDecodeError:
                state.result.messages["invalid_json"] += 1
                continue

            message_type = data.get("type", "unknown")
            state.result.messages[message_type] += 1

            if message_type == "hello":
                state.result.hello_received = True
                state.hello_event.set()
            elif message_type == "ready":
                state.result.ready_received = True
                state.result.ready_latency_ms = (time.perf_counter() - state.connect_started_at) * 1000.0
                state.ready_event.set()
            elif message_type == "pong":
                if state.pending_ping_sent_at is not None:
                    state.result.pong_latencies_ms.append((time.perf_counter() - state.pending_ping_sent_at) * 1000.0)
                    state.pending_ping_sent_at = None
            elif message_type == "warning":
                state.result.warnings.append(str(data.get("message", "warning")))
            elif message_type == "error":
                state.result.errors.append(str(data.get("message", "error")))
    except ConnectionClosed as exc:
        state.result.disconnect_code = exc.code
        state.result.disconnect_reason = exc.reason or ""
    except Exception as exc:
        state.result.exception = str(exc)
    finally:
        state.receiver_done.set()


async def maybe_send_ping(websocket, state):
    if state.pending_ping_sent_at is not None:
        return
    state.pending_ping_sent_at = time.perf_counter()
    await websocket.send(json.dumps({"type": "ping"}))


async def run_client(args, client_index):
    result = ClientResult(client_index=client_index)
    await asyncio.sleep((args.connect_stagger_ms / 1000.0) * client_index)
    try:
        async with websockets.connect(args.url, max_size=None) as websocket:
            result.connected = True
            state = ClientState(result, args.startup_timeout)
            receiver_task = asyncio.create_task(receive_messages(websocket, state))

            await asyncio.wait_for(state.hello_event.wait(), timeout=args.startup_timeout)
            try:
                await asyncio.wait_for(state.ready_event.wait(), timeout=args.startup_timeout)
            except asyncio.TimeoutError:
                pass

            end_time = time.perf_counter() + args.duration
            last_ping_at = 0.0

            if args.mode == "stream":
                await websocket.send(json.dumps({"type": "start"}))
                chunk_seconds = args.chunk_ms / 1000.0
                pcm_chunk = synthesize_pcm_s16le(
                    sample_rate=args.sample_rate,
                    channels=args.channels,
                    duration_seconds=chunk_seconds,
                    frequency_hz=args.audio_frequency_hz,
                    amplitude=args.audio_amplitude,
                )
                audio_packet = make_audio_packet_bytes(args.sample_rate, args.channels, pcm_chunk)

                while time.perf_counter() < end_time:
                    await websocket.send(audio_packet)
                    now = time.perf_counter()
                    if now - last_ping_at >= args.ping_interval:
                        await maybe_send_ping(websocket, state)
                        last_ping_at = now
                    await asyncio.sleep(chunk_seconds)

                await websocket.send(json.dumps({"type": "stop"}))
            else:
                while time.perf_counter() < end_time:
                    now = time.perf_counter()
                    if now - last_ping_at >= args.ping_interval:
                        await maybe_send_ping(websocket, state)
                        last_ping_at = now
                    if args.metrics:
                        await websocket.send(json.dumps({"type": "metrics"}))
                    await asyncio.sleep(min(0.25, max(0.05, args.ping_interval / 2.0)))

            if args.metrics:
                await websocket.send(json.dumps({"type": "metrics"}))
                await asyncio.sleep(0.25)

            await websocket.close()
            await asyncio.wait_for(state.receiver_done.wait(), timeout=2.0)
            await receiver_task
    except Exception as exc:
        result.exception = str(exc)
    return result


def aggregate_results(results):
    message_counts = Counter()
    ready_latencies = []
    pong_latencies = []
    error_count = 0
    warning_count = 0
    exceptions = []

    for result in results:
        message_counts.update(result.messages)
        if result.ready_latency_ms is not None:
            ready_latencies.append(result.ready_latency_ms)
        pong_latencies.extend(result.pong_latencies_ms)
        error_count += len(result.errors)
        warning_count += len(result.warnings)
        if result.exception:
            exceptions.append({"client": result.client_index, "error": result.exception})

    return {
        "clientsRequested": len(results),
        "clientsConnected": sum(1 for result in results if result.connected),
        "helloReceived": sum(1 for result in results if result.hello_received),
        "readyReceived": sum(1 for result in results if result.ready_received),
        "disconnects": sum(1 for result in results if result.disconnect_code is not None),
        "errorMessages": error_count,
        "warningMessages": warning_count,
        "messageCounts": dict(sorted(message_counts.items())),
        "readyLatency": summarize_latencies(ready_latencies),
        "pongLatency": summarize_latencies(pong_latencies),
        "exceptions": exceptions,
    }


def print_human_report(report):
    print(f"Clients requested: {report['clientsRequested']}")
    print(f"Clients connected: {report['clientsConnected']}")
    print(f"Hello received: {report['helloReceived']}")
    print(f"Ready received: {report['readyReceived']}")
    print(f"Disconnects observed: {report['disconnects']}")
    print(f"Warning messages: {report['warningMessages']}")
    print(f"Error messages: {report['errorMessages']}")
    if report["readyLatency"] is not None:
        latency = report["readyLatency"]
        print(
            "Ready latency ms: "
            f"min={latency['minMs']} avg={latency['avgMs']} p95={latency['p95Ms']} max={latency['maxMs']}"
        )
    if report["pongLatency"] is not None:
        latency = report["pongLatency"]
        print(
            "Pong latency ms: "
            f"min={latency['minMs']} avg={latency['avgMs']} p95={latency['p95Ms']} max={latency['maxMs']}"
        )
    if report["messageCounts"]:
        print("Message counts:")
        for key, value in report["messageCounts"].items():
            print(f"  {key}: {value}")
    if report["exceptions"]:
        print("Exceptions:")
        for item in report["exceptions"]:
            print(f"  client {item['client']}: {item['error']}")


async def run_load(args):
    tasks = [asyncio.create_task(run_client(args, index)) for index in range(args.clients)]
    results = await asyncio.gather(*tasks)
    report = aggregate_results(results)
    if args.metrics:
        try:
            report["health"] = fetch_json(derive_http_url(args.url, "/health"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            report["healthFetchError"] = str(exc)
        try:
            report["serviceMetrics"] = fetch_json(derive_http_url(args.url, "/api/metrics"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            report["metricsFetchError"] = str(exc)
    return report


def main(argv=None):
    parser = build_arg_parser()
    args = validate_args(parser.parse_args(argv))
    report = asyncio.run(run_load(args))
    if args.report_json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print_human_report(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
