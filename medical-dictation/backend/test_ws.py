import asyncio
import websockets
import numpy as np

# Generate 2 seconds of 440Hz sine wave at 16kHz, Int16 PCM
SAMPLE_RATE = 16000
DURATION_SEC = 2
FREQ = 440

t = np.linspace(0, DURATION_SEC, int(SAMPLE_RATE * DURATION_SEC), endpoint=False)
wave = 0.5 * np.sin(2 * np.pi * FREQ * t)
pcm = (wave * 32767).astype(np.int16)
audio_bytes = pcm.tobytes()

async def test_ws():
    uri = "ws://localhost:8000/ws/dictate"
    async with websockets.connect(uri) as ws:
        print(f"Connected to {uri}")
        # Send audio bytes in one go
        await ws.send(audio_bytes)
        print(f"Sent {len(audio_bytes)} bytes of audio")
        try:
            while True:
                msg = await ws.recv()
                print(f"Received: {msg}")
        except websockets.ConnectionClosed:
            print("Connection closed")

if __name__ == "__main__":
    asyncio.run(test_ws())
