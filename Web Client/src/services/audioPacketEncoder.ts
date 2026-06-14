import type { AudioMetadata } from "../types/websocket-contract";

export function float32ToInt16(floatSamples: Float32Array): Int16Array {
  const pcm = new Int16Array(floatSamples.length);
  for (let i = 0; i < floatSamples.length; i++) {
    const value = Math.max(-1, Math.min(1, floatSamples[i]!));
    pcm[i] = value < 0 ? value * 32768 : value * 32767;
  }
  return pcm;
}

export function encodeAudioPacket(
  metadata: AudioMetadata,
  audioBuffer: ArrayBuffer
): ArrayBuffer {
  const metadataBytes = new TextEncoder().encode(
    JSON.stringify(metadata)
  );
  const packet = new ArrayBuffer(
    4 + metadataBytes.byteLength + audioBuffer.byteLength
  );
  const view = new DataView(packet);
  view.setUint32(0, metadataBytes.byteLength, true);
  new Uint8Array(packet, 4, metadataBytes.byteLength).set(metadataBytes);
  new Uint8Array(packet, 4 + metadataBytes.byteLength).set(
    new Uint8Array(audioBuffer)
  );
  return packet;
}
