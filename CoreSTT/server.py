"""Standalone CoreSTT browser demo server.

Run from this folder:

    python server.py --host 127.0.0.1 --port 8020

Then open http://127.0.0.1:8020 and allow microphone access.
"""

import argparse
import asyncio
import json
import logging
import struct
import threading
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import websockets
import numpy as np
from scipy.signal import resample

from CoreSTT import AudioToTextRecorder


ROOT = Path(__file__).resolve().parent
STATIC_ROOT = ROOT / "static"
SERVER_SAMPLE_RATE = 16000
LOGGER = logging.getLogger("corestt.demo")


class StaticHandler(SimpleHTTPRequestHandler):
    """Serves the minimal browser UI and a simple health endpoint."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC_ROOT), **kwargs)

    def do_GET(self):
        if self.path == "/health":
            body = json.dumps({"ok": True}).encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path == "/favicon.ico":
            self.send_response(HTTPStatus.NO_CONTENT)
            self.end_headers()
            return
        return super().do_GET()


def resample_pcm_s16le(audio_bytes, original_sample_rate):
    """Converts browser PCM bytes to 16 kHz mono PCM bytes for the recorder."""

    samples = np.frombuffer(audio_bytes, dtype=np.int16)
    if not len(samples):
        return b""
    if original_sample_rate != SERVER_SAMPLE_RATE:
        target_samples = int(len(samples) * SERVER_SAMPLE_RATE / original_sample_rate)
        samples = resample(samples, target_samples).astype(np.int16)
    return samples.tobytes()


def parse_audio_packet(packet):
    """Extracts metadata and normalized 16 kHz PCM from a browser packet."""

    if len(packet) < 4:
        raise ValueError("Audio packet is too short")

    metadata_length = struct.unpack("<I", packet[:4])[0]
    metadata_end = 4 + metadata_length
    if metadata_end > len(packet):
        raise ValueError("Audio packet metadata length is invalid")

    metadata = json.loads(packet[4:metadata_end].decode("utf-8"))
    audio_bytes = packet[metadata_end:]
    sample_rate = int(metadata.get("sampleRate", SERVER_SAMPLE_RATE))
    return resample_pcm_s16le(audio_bytes, sample_rate)


def create_recorder(send_message):
    """Creates a recorder tuned for local CPU browser testing."""

    def on_realtime(text):
        send_message({"type": "realtime", "text": text})

    return AudioToTextRecorder(
        spinner=False,
        use_microphone=False,
        model="small.en",
        device="cpu",
        compute_type="int8",
        language="en",
        no_log_file=True,
        enable_realtime_transcription=True,
        realtime_model_type="tiny.en",
        realtime_processing_pause=0.05,
        on_realtime_transcription_update=on_realtime,
        silero_sensitivity=0.4,
        webrtc_sensitivity=2,
        post_speech_silence_duration=0.7,
        min_length_of_recording=0.2,
        min_gap_between_recordings=0,
    )


async def websocket_handler(websocket):
    """Handles one browser microphone websocket connection."""

    loop = asyncio.get_running_loop()
    outgoing = asyncio.Queue()
    packet_count = 0

    def send_message(message):
        loop.call_soon_threadsafe(outgoing.put_nowait, message)

    recorder = create_recorder(send_message)
    stop_event = threading.Event()

    async def sender():
        while not stop_event.is_set():
            message = await outgoing.get()
            await websocket.send(json.dumps(message))

    def final_transcription_worker():
        while not stop_event.is_set():
            try:
                text = recorder.text()
            except Exception as exc:
                send_message({"type": "error", "text": str(exc)})
                continue
            if text:
                send_message({"type": "final", "text": text})

    sender_task = asyncio.create_task(sender())
    final_thread = threading.Thread(target=final_transcription_worker, daemon=True)
    final_thread.start()
    send_message({"type": "status", "text": "Connected. Allow microphone and start speaking."})

    try:
        async for packet in websocket:
            if isinstance(packet, str):
                continue
            audio_bytes = parse_audio_packet(packet)
            if not audio_bytes:
                continue
            recorder.feed_audio(audio_bytes, original_sample_rate=SERVER_SAMPLE_RATE)
            packet_count += 1
            if packet_count == 1:
                LOGGER.info("Receiving browser audio")
                send_message({"type": "status", "text": "Receiving audio. Waiting for speech."})
    finally:
        stop_event.set()
        sender_task.cancel()
        recorder.shutdown()


def start_http_server(host, port):
    server = ThreadingHTTPServer((host, port), StaticHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


async def main():
    parser = argparse.ArgumentParser(description="Run the standalone CoreSTT demo.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8020)
    parser.add_argument("--ws-port", type=int, default=8021)
    args = parser.parse_args()

    http_server = start_http_server(args.host, args.port)
    print(f"CoreSTT UI: http://{args.host}:{args.port}")
    print(f"CoreSTT websocket: ws://{args.host}:{args.ws_port}/ws")

    async with websockets.serve(websocket_handler, args.host, args.ws_port):
        try:
            await asyncio.Future()
        finally:
            http_server.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
