# CoreSTT WebSocket Client Integration Contract

## Purpose

This document standardizes the client request and input format for integrating
CoreSTT with any platform that can open a WebSocket and send PCM audio.

Use this contract before implementing web, Windows, Android, iOS, macOS,
Python, CLI, backend, or other non-browser clients for `WS /ws/transcribe`.
It documents the current implementation and does not define a new protocol.

## WebSocket Endpoint

Local development endpoint:

```text
ws://127.0.0.1:8020/ws/transcribe
```

Production endpoint behind TLS:

```text
wss://<host>/ws/transcribe
```

Browser clients should select the scheme from the page origin:

```javascript
const proto = location.protocol === "https:" ? "wss:" : "ws:";
const socket = new WebSocket(proto + "//" + location.host + "/ws/transcribe");
socket.binaryType = "arraybuffer";
```

Non-browser clients should use `wss://` when crossing untrusted networks.

## Connection Lifecycle

The normal lifecycle is:

```text
connect -> hello -> ready -> start -> send audio -> realtime/final -> stop -> close
```

1. Client opens `WS /ws/transcribe`.
2. Server accepts or rejects admission.
3. On admission, server sends `hello`.
4. If the scheduler is ready, server sends `ready`.
5. Client sends `{"type":"start"}` before audio.
6. Client sends binary audio packets.
7. Server sends `status`, `timeline`, `realtime`, and `final` messages while processing.
8. Client sends `{"type":"stop"}` when capture ends.
9. Client closes the socket or keeps it open for another `start`.

Audio is allowed only after the socket is open and the client has sent `start`.
Clients should wait for `ready` before presenting the stream as ready to users.
If domain profiles are edited while a client is connected, the server may send
`domain_profiles_updated`; clients should refresh domain-selection controls for
future `start` commands.

## Client to Server Message Types

The socket accepts two frame types:

| Frame type | Payload | Purpose |
|---|---|---|
| Text | JSON object with `type` | Control commands such as `start`, `stop`, `clear`, `ping`, and `metrics`. |
| Binary | CoreSTT audio packet | PCM audio with a metadata prefix. |

Text frames must decode to a JSON object. Unknown command types return an
`error` message.

## JSON Control Messages

### start

Purpose: Start server-side streaming/session state for this WebSocket.

Example:

```json
{ "type": "start" }
```

Domain-biased example:

```json
{ "type": "start", "domain": "medical" }
```

Send when the user begins recording or when a non-interactive client begins
sending audio. `domain` is optional. When present, it must match one of the
server-owned domain profiles exposed by `/api/config` and the WebSocket
`hello`/`ready` messages. A selected profile supplies prompt and hotword biasing
for the session; it does not perform correction or rewrite final text.

### stop

Purpose: Stop server-side streaming/session state and trigger end-of-recording
handling.

Example:

```json
{ "type": "stop" }
```

Send when the user stops recording, when an audio file has finished streaming,
or before closing after a stream.

### clear

Purpose: Clear the server/client transcript state for the session.

Example:

```json
{ "type": "clear" }
```

Send when the client wants to reset displayed transcript content for the current
session.

### ping

Purpose: Measure socket/control latency. The server replies with `pong`.

Example:

```json
{ "type": "ping" }
```

Send periodically while connected. The browser client currently sends this every
2.5 seconds.

### metrics

Purpose: Request the current session metrics snapshot. The server replies with
`metrics`.

Example:

```json
{ "type": "metrics" }
```

Send for diagnostics, stress testing, or client-side monitoring. Do not send at
very high frequency from production clients.

## Domain Profile HTTP API

Domain profiles are server-owned transcription hints. Clients can list and edit
them through HTTP, then select a profile by name in the WebSocket `start`
command. Profile edits affect future streams; clients should not expect an
active stream to change domain behavior mid-recording.

### GET /api/domain-profiles

Purpose: Return editable profile details and the sorted list of profile names.

Example response:

```json
{
  "domainProfiles": ["general", "medical"],
  "profiles": {
    "general": {
      "initial_prompt": null,
      "initial_prompt_realtime": null,
      "hotwords": null
    },
    "medical": {
      "initial_prompt": "This is medical dictation.",
      "initial_prompt_realtime": "Medical dictation.",
      "hotwords": ["hypertension", "metformin"]
    }
  }
}
```

### PUT /api/domain-profiles/{name}

Purpose: Create or replace one profile.

Example request:

```json
{
  "initial_prompt": "This is legal dictation.",
  "initial_prompt_realtime": "Legal dictation.",
  "hotwords": ["affidavit", "plaintiff"]
}
```

Rules:

- `{name}` must be a non-empty profile name.
- `initial_prompt` and `initial_prompt_realtime` may be strings or `null`.
- `hotwords` may be a string, a list of strings, or omitted.
- Invalid profile payloads return HTTP `400`.

Example response:

```json
{
  "profile": {
    "initial_prompt": "This is legal dictation.",
    "initial_prompt_realtime": "Legal dictation.",
    "hotwords": ["affidavit", "plaintiff"]
  },
  "domainProfiles": ["general", "legal", "medical"],
  "profiles": {
    "legal": {
      "initial_prompt": "This is legal dictation.",
      "initial_prompt_realtime": "Legal dictation.",
      "hotwords": ["affidavit", "plaintiff"]
    }
  }
}
```

### DELETE /api/domain-profiles/{name}

Purpose: Delete one profile.

Unknown profile names return HTTP `404`. Successful deletes return the same
shape as `GET /api/domain-profiles`.

Production deployments should protect profile-write endpoints with the same
authorization policy used for runtime configuration, because prompts and
hotwords can strongly influence transcription output.

## Binary Audio Packet Format

Each binary audio frame has this exact layout:

```text
[uint32 metadataLength little-endian][metadata JSON UTF-8][pcm_s16le audio bytes]
```

| Offset | Size | Encoding | Description |
|---:|---:|---|---|
| `0` | `4` bytes | unsigned 32-bit little-endian | Byte length of the metadata JSON. |
| `4` | `metadataLength` bytes | UTF-8 JSON | Metadata object. |
| `4 + metadataLength` | remaining bytes | `pcm_s16le` | Raw signed 16-bit little-endian PCM samples. |

Protocol constraints from `CoreSTT/protocol.py`:

| Rule | Value |
|---|---|
| Binary packet must be bytes-like | Required |
| Metadata must decode to JSON object | Required |
| Metadata length encoding | unsigned 32-bit little-endian |
| Maximum metadata size | `64 KiB` |
| Audio payload type | bytes-like |

Server settings also cap audio packet bytes. The current default
`max_audio_packet_bytes` is `512 KiB`.

## Audio Metadata Schema

Recommended metadata:

```json
{
  "sampleRate": 48000,
  "channels": 1,
  "format": "pcm_s16le",
  "frames": 1920,
  "sentAt": 123456.78,
  "clientPlatform": "android",
  "clientProtocolVersion": "1.0",
  "sequence": 42
}
```

| Field | Status | Type | Rules |
|---|---|---|---|
| `sampleRate` | Required | positive integer | Original audio sample rate before server resampling. |
| `channels` | Recommended | positive integer | Defaults to `1`; maximum `8`. Mono is recommended. |
| `format` | Recommended | string | Defaults to `pcm_s16le`; only `pcm_s16le` is supported. |
| `frames` | Optional | positive integer | If present, must equal payload frame count. |
| `sentAt` | Optional | number | Client-side monotonic or wall-clock timestamp for diagnostics. |
| `clientPlatform` | Optional | string | Example values: `web`, `windows`, `android`, `ios`, `macos`, `python`. |
| `sequence` | Optional | integer | Client packet sequence number for diagnostics. |
| `clientProtocolVersion` | Recommended | string | Use `"1.0"` for current clients. |

Unknown metadata fields are currently ignored by the server after packet
decoding, but clients should keep metadata compact.

## Audio Format Requirements

Audio bytes must be `pcm_s16le`:

| Requirement | Value |
|---|---|
| Sample format | signed 16-bit integer |
| Endianness | little-endian |
| Valid sample range | `-32768` to `32767` |
| Recommended channel count | `1` mono |
| Maximum channel count | `8` |
| Server internal sample rate | `16000 Hz` after resampling |

The server accepts other positive input sample rates and resamples to its
internal rate. If `channels > 1`, the server averages channels to mono before
resampling.

Float32 microphone samples must be clamped to `[-1.0, 1.0]` and converted to
signed 16-bit PCM:

```javascript
const pcm = new Int16Array(floatSamples.length);

for (let i = 0; i < floatSamples.length; i++) {
  const value = Math.max(-1, Math.min(1, floatSamples[i]));
  pcm[i] = value < 0 ? value * 32768 : value * 32767;
}
```

## Chunk Size Standard

Recommended chunk size is `40 ms`. Acceptable normal range is `20 ms` to
`100 ms`.

Formula:

```text
frames = sampleRate * chunkMs / 1000
bytes = frames * channels * 2
```

Examples for mono `pcm_s16le`:

| Sample rate | Chunk | Frames | Bytes |
|---:|---:|---:|---:|
| `16000 Hz` | `40 ms` | `640` | `1280` |
| `44100 Hz` | `40 ms` | `1764` | `3528` |
| `48000 Hz` | `40 ms` | `1920` | `3840` |
| `16000 Hz` | `20 ms` | `320` | `640` |
| `16000 Hz` | `100 ms` | `1600` | `3200` |

Use whole-frame payloads only. For multi-channel packets:

```text
bytes = frames * channels * 2
```

## Packet Encoding Examples

### JavaScript

```javascript
function encodePacket(metadata, audioBuffer) {
  const metadataBytes = new TextEncoder().encode(JSON.stringify(metadata));
  const packet = new ArrayBuffer(4 + metadataBytes.byteLength + audioBuffer.byteLength);
  const view = new DataView(packet);

  view.setUint32(0, metadataBytes.byteLength, true);
  new Uint8Array(packet, 4, metadataBytes.byteLength).set(metadataBytes);
  new Uint8Array(packet, 4 + metadataBytes.byteLength).set(new Uint8Array(audioBuffer));

  return packet;
}
```

### Python

```python
import json
import struct


def encode_packet(metadata, pcm_bytes):
    metadata_bytes = json.dumps(metadata, separators=(",", ":")).encode("utf-8")
    return struct.pack("<I", len(metadata_bytes)) + metadata_bytes + bytes(pcm_bytes)
```

### C#/.NET

```csharp
using System.Buffers.Binary;
using System.Text;
using System.Text.Json;

static byte[] EncodePacket(object metadata, byte[] pcmBytes)
{
    byte[] metadataBytes = JsonSerializer.SerializeToUtf8Bytes(metadata);
    byte[] packet = new byte[4 + metadataBytes.Length + pcmBytes.Length];

    BinaryPrimitives.WriteUInt32LittleEndian(packet.AsSpan(0, 4), (uint)metadataBytes.Length);
    metadataBytes.CopyTo(packet.AsSpan(4));
    pcmBytes.CopyTo(packet.AsSpan(4 + metadataBytes.Length));

    return packet;
}
```

### Kotlin/Android

```kotlin
import org.json.JSONObject
import java.nio.ByteBuffer
import java.nio.ByteOrder

fun encodePacket(metadata: JSONObject, pcmBytes: ByteArray): ByteArray {
    val metadataBytes = metadata.toString().toByteArray(Charsets.UTF_8)
    return ByteBuffer
        .allocate(4 + metadataBytes.size + pcmBytes.size)
        .order(ByteOrder.LITTLE_ENDIAN)
        .putInt(metadataBytes.size)
        .put(metadataBytes)
        .put(pcmBytes)
        .array()
}
```

### Swift/iOS/macOS

```swift
import Foundation

func encodePacket(metadata: [String: Any], pcmBytes: Data) throws -> Data {
    let metadataBytes = try JSONSerialization.data(withJSONObject: metadata)
    var packet = Data()

    var metadataLength = UInt32(metadataBytes.count).littleEndian
    withUnsafeBytes(of: &metadataLength) { packet.append(contentsOf: $0) }
    packet.append(metadataBytes)
    packet.append(pcmBytes)

    return packet
}
```

## Server to Client Messages

### hello

Purpose: Confirms admission and provides session/server configuration.

Example:

```json
{
  "type": "hello",
  "clientId": "session-id",
  "sessionId": "session-id",
  "settings": {},
  "limits": {},
  "supportedEngines": [],
  "domainProfiles": ["general", "medical"],
  "runtimeSettings": {}
}
```

Client handling: Store `sessionId`/`clientId`, inspect limits/settings if needed,
inspect `domainProfiles` if the client offers domain selection, and wait for
`ready` before marking the session ready.

### ready

Purpose: Indicates the scheduler/session is ready.

Example:

```json
{
  "type": "ready",
  "sessionId": "session-id",
  "ok": true,
  "settings": {},
  "limits": {},
  "domainProfiles": ["general", "medical"],
  "runtimeSettings": {}
}
```

Client handling: Enable recording controls and allow `start`.
If `domainProfiles` is present, clients may include one of those names in the
next `start` command.

### status

Purpose: Reports recorder/session state and queue counters.

Example:

```json
{
  "type": "status",
  "sessionId": "session-id",
  "domain": "medical",
  "state": "recording",
  "activeClientId": "session-id",
  "queueDepth": 0.64,
  "droppedChunks": 0,
  "coalescedRealtime": 0,
  "staleRealtimeDiscarded": 0,
  "activeSessions": 1,
  "activeSpeakers": 1,
  "wakeWordEnabled": false
}
```

Client handling: Update UI state, queue indicators, selected domain display,
and diagnostics.

### realtime

Purpose: Interim transcript update.

Example:

```json
{
  "type": "realtime",
  "sessionId": "session-id",
  "segmentId": 1,
  "sequence": 12,
  "text": "partial text",
  "displayText": "partial text",
  "stableText": "partial",
  "unstableText": " text",
  "timestamp": 1234567890.0,
  "timestampIso": "2026-06-14T10:00:00.000Z"
}
```

Client handling: Display as non-final text. Replace/update the same `segmentId`
instead of appending duplicate interim content.

### final

Purpose: Final transcript segment.

Example:

```json
{
  "type": "final",
  "sessionId": "session-id",
  "segmentId": 1,
  "text": "final text",
  "timestamp": 1234567890.0,
  "timestampIso": "2026-06-14T10:00:00.000Z"
}
```

Client handling: Commit as final text for the `segmentId`.

### timeline

Purpose: Recorder, wake-word, and transcription lifecycle event.

Example:

```json
{
  "type": "timeline",
  "sessionId": "session-id",
  "domain": "medical",
  "event": "recording_started",
  "segmentId": 1,
  "timestamp": 1234567890.0,
  "timestampIso": "2026-06-14T10:00:00.000Z"
}
```

Client handling: Use for event logs, timing views, selected-domain diagnostics,
and troubleshooting.

### clear

Purpose: Instructs client to clear transcript state.

Example:

```json
{
  "type": "clear",
  "sessionId": "session-id"
}
```

Client handling: Clear local transcript and segment state.

### warning

Purpose: Non-fatal issue, commonly rejected audio chunk or degradation notice.

Example:

```json
{
  "type": "warning",
  "sessionId": "session-id",
  "message": "Audio chunk was rejected."
}
```

Client handling: Log and surface if user action is needed, but keep the socket
open.

### error

Purpose: Fatal or command/audio error. Admission errors are sent before close
when the configured session limit is reached.

Example:

```json
{
  "type": "error",
  "sessionId": "session-id",
  "where": "audio_packet",
  "message": "only pcm_s16le audio packets are supported"
}
```

Admission error example:

```json
{
  "type": "error",
  "where": "admission",
  "message": "Server is at the configured session limit.",
  "limits": {}
}
```

Unknown domain example:

```json
{
  "type": "error",
  "sessionId": "session-id",
  "where": "domain",
  "message": "Unknown domain profile: medical-specialty"
}
```

Client handling: Stop recording for fatal/admission errors. For packet errors,
fix client encoding before retrying. For domain errors, choose one of the
advertised `domainProfiles` or omit `domain`.

### pong

Purpose: Reply to `ping`.

Example:

```json
{
  "type": "pong",
  "sessionId": "session-id",
  "serverTime": 1234567890.0
}
```

Client handling: Measure latency from client send time to receive time.

### metrics

Purpose: Reply to `metrics` control message with session snapshot.

Example:

```json
{
  "type": "metrics",
  "sessionId": "session-id",
  "metrics": {
    "sessionId": "session-id",
    "domain": "medical",
    "streaming": true,
    "state": "recording"
  }
}
```

Client handling: Use for diagnostics and operational dashboards, not transcript
rendering.

### domain_profiles_updated

Purpose: Notify connected clients that editable domain profile data changed.

Example:

```json
{
  "type": "domain_profiles_updated",
  "domainProfiles": ["general", "medical"],
  "profiles": {
    "medical": {
      "initial_prompt": "This is medical dictation.",
      "initial_prompt_realtime": "Medical dictation.",
      "hotwords": ["hypertension", "metformin"]
    }
  }
}
```

Client handling: Refresh domain-selection controls and any profile editing UI.
Do not change an active stream's selected domain; send the desired domain in the
next `start` command.

## Cross-Platform Integration Notes

### Web

Use `WebSocket`, set `binaryType = "arraybuffer"`, capture microphone audio with
`getUserMedia`, and convert `Float32Array` samples to `Int16Array` before packet
encoding. The current browser client requests mono capture with echo
cancellation, noise suppression, auto gain control, and `channelCount: 1`.

### Windows

Capture PCM from WASAPI, Media Foundation, NAudio, or another audio API.
Convert to mono `pcm_s16le`, encode packets with a 4-byte little-endian metadata
prefix, and send binary frames over a WebSocket client.

### macOS

Capture from Core Audio or AVFoundation. Prefer mono capture or downmix before
sending. Ensure Swift or Objective-C packet encoding writes the metadata length
as little-endian `UInt32`.

### iOS

Use `AVAudioEngine` or `AVAudioRecorder` capture paths that produce PCM. Respect
microphone permissions, stop capture on socket close, and avoid background
recording unless the app has the required platform entitlement and user consent.

### Android

Use `AudioRecord` for PCM capture. Prefer mono input, convert samples to signed
16-bit little-endian bytes, and avoid sending audio while the WebSocket is not
open.

### Python/backend Clients

Use a WebSocket library such as `websockets` or `websocket-client`. Stream WAV,
microphone, or generated PCM by chunking into whole `pcm_s16le` frames and using
the same packet layout.

## Recommended Client State Machine

| State | Meaning | Audio allowed |
|---|---|---|
| `DISCONNECTED` | No socket exists. | No |
| `CONNECTING` | Socket open is in progress. | No |
| `CONNECTED` | Socket opened, waiting for `hello`/`ready`. | No |
| `READY` | Server sent `ready`. | No, send `start` first |
| `STREAMING` | Client sent `start` and capture is active. | Yes |
| `STOPPING` | Client sent `stop` and is draining/closing capture. | No new audio |
| `CLOSED` | Socket closed. | No |

Clients should not keep recording when the socket is closed. Stop microphone or
file streaming immediately on disconnect.

## Client-Side Validation Rules

Before sending each binary packet, validate:

- WebSocket is open.
- Client is in `STREAMING` state.
- Metadata is a JSON object.
- Encoded metadata is no larger than `64 KiB`.
- `sampleRate` is a positive integer.
- `channels` is a positive integer no greater than `8`.
- `format` is exactly `pcm_s16le`.
- Audio bytes are signed 16-bit little-endian PCM.
- Payload byte length is divisible by `channels * 2`.
- If `frames` is present, `frames * channels * 2 == audio byte length`.
- Packet size is below the server `maxAudioPacketBytes` limit when known.

## Error Handling and Reconnect Strategy

Clients should treat `warning` and `error` differently:

- `warning`: non-fatal; keep the socket open and continue only if audio capture
  remains valid.
- `error` with `where: "admission"`: server rejected the session; stop capture
  and retry later with backoff.
- `error` with `where: "audio_packet"`: client encoding is invalid; stop sending
  audio until the packet bug is fixed.
- `error` with `where: "command"`: client sent invalid JSON or an unknown
  command; fix the control message before retrying.
- `error` with `where: "domain"`: client requested an unknown domain profile;
  choose one of the advertised `domainProfiles` or omit `domain`.

On socket close:

- Stop microphone or file capture immediately.
- Do not buffer unlimited audio while disconnected.
- Move state to `CLOSED` or `DISCONNECTED`.
- Reconnect with bounded exponential backoff.
- Send a new `start` after reconnecting and receiving `ready`.

Recommended backoff:

```text
1s, 2s, 4s, 8s, then cap at 30s
```

## Integration Checklist

- Open `ws://127.0.0.1:8020/ws/transcribe` locally or
  `wss://<host>/ws/transcribe` in production.
- Handle `hello`, `ready`, `status`, `realtime`, `final`, `timeline`, `clear`,
  `warning`, `error`, `pong`, `metrics`, and `domain_profiles_updated`.
- Send JSON control messages as text frames.
- Send audio packets as binary frames.
- Send `{"type":"start"}` before the first audio packet.
- Optionally include a domain profile name in `start`, for example
  `{"type":"start","domain":"medical"}`.
- Use `GET /api/domain-profiles` when the client needs editable profile
  details, not just names.
- Convert audio to mono `pcm_s16le` where practical.
- Use 40 ms chunks by default.
- Include `sampleRate`, `channels`, `format`, `frames`, `sentAt`, `sequence`,
  `clientPlatform`, and `clientProtocolVersion` metadata.
- Validate packet alignment before sending.
- Send `{"type":"stop"}` when capture ends.
- Stop audio capture immediately on socket close.
- Implement bounded reconnect/backoff.

## Versioning Recommendation

Include this metadata in all new clients:

```json
{
  "clientProtocolVersion": "1.0"
}
```

The current server does not require this field, but including it gives future
clients and server versions a clear compatibility marker.
