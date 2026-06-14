import { float32ToInt16, encodeAudioPacket } from "./audioPacketEncoder";
import type { AudioMetadata } from "../types/websocket-contract";

export interface AudioCaptureCallbacks {
  onPacket: (packet: ArrayBuffer) => void;
  onError: (error: string) => void;
}

export class AudioCapture {
  private stream: MediaStream | null = null;
  private audioContext: AudioContext | null = null;
  private source: MediaStreamAudioSourceNode | null = null;
  private worklet: AudioWorkletNode | null = null;
  private processor: ScriptProcessorNode | null = null;
  private zeroGain: GainNode | null = null;
  private sampleRate = 0;
  private chunkBuffers: Float32Array[] = [];
  private bufferedSamples = 0;
  private targetChunkMs = 40;
  private _streaming = false;
  private sequence = 0;
  private callbacks: AudioCaptureCallbacks | null = null;

  get isActive(): boolean {
    return this._streaming;
  }

  async start(
    callbacks: AudioCaptureCallbacks,
    targetChunkMs = 40
  ): Promise<void> {
    this.stop();
    this.callbacks = callbacks;
    this.targetChunkMs = targetChunkMs;
    this.chunkBuffers = [];
    this.bufferedSamples = 0;
    this.sequence = 0;

    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          channelCount: 1,
        },
      });
    } catch (err) {
      const message =
        err instanceof DOMException && err.name === "NotAllowedError"
          ? "Microphone permission denied"
          : "Microphone access failed";
      callbacks.onError(message);
      throw err;
    }

    this.stream = stream;

    const AudioContextClass =
      window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
    const audioContext = new AudioContextClass({ latencyHint: "interactive" });
    this.audioContext = audioContext;
    this.sampleRate = audioContext.sampleRate;

    const source = audioContext.createMediaStreamSource(stream);
    this.source = source;

    const zeroGain = audioContext.createGain();
    zeroGain.gain.value = 0;
    zeroGain.connect(audioContext.destination);
    this.zeroGain = zeroGain;

    this._streaming = true;

    if (audioContext.audioWorklet) {
      try {
        const workletSource = `class CoreSTTCapture extends AudioWorkletProcessor {
          process(inputs: Float32Array[][], _parameters: Record<string, Float32Array>, _outputs: Float32Array[][]) {
            const input = inputs[0];
            if (input && input[0]) {
              this.port.postMessage((input[0] as Float32Array).slice(0));
            }
            return true;
          }
        }
        registerProcessor('corestt-capture', CoreSTTCapture);`;
        const blob = new Blob([workletSource], {
          type: "application/javascript",
        });
        const url = URL.createObjectURL(blob);
        await audioContext.audioWorklet.addModule(url);
        URL.revokeObjectURL(url);
        const node = new AudioWorkletNode(audioContext, "corestt-capture");
        node.port.onmessage = (event: MessageEvent<Float32Array>) =>
          this.enqueueSamples(event.data);
        source.connect(node);
        node.connect(zeroGain);
        this.worklet = node;
      } catch {
        this.startScriptProcessor(audioContext, source, zeroGain);
      }
    } else {
      this.startScriptProcessor(audioContext, source, zeroGain);
    }
  }

  private startScriptProcessor(
    audioContext: AudioContext,
    source: MediaStreamAudioSourceNode,
    zeroGain: GainNode
  ): void {
    const processor = audioContext.createScriptProcessor(1024, 1, 1);
    processor.onaudioprocess = (event: AudioProcessingEvent) => {
      this.enqueueSamples(event.inputBuffer.getChannelData(0));
    };
    source.connect(processor);
    processor.connect(zeroGain);
    this.processor = processor;
  }

  stop(): void {
    this._streaming = false;
    this.chunkBuffers = [];
    this.bufferedSamples = 0;

    if (this.worklet) {
      try {
        this.worklet.disconnect();
      } catch {
        /* already disconnected */
      }
      this.worklet = null;
    }

    if (this.processor) {
      try {
        this.processor.disconnect();
      } catch {
        /* already disconnected */
      }
      this.processor = null;
    }

    if (this.source) {
      try {
        this.source.disconnect();
      } catch {
        /* already disconnected */
      }
      this.source = null;
    }

    if (this.zeroGain) {
      try {
        this.zeroGain.disconnect();
      } catch {
        /* already disconnected */
      }
      this.zeroGain = null;
    }

    if (this.stream) {
      this.stream.getTracks().forEach((track) => track.stop());
      this.stream = null;
    }

    if (this.audioContext) {
      this.audioContext.close().catch(() => {});
      this.audioContext = null;
    }

    this.callbacks = null;
  }

  private enqueueSamples(samples: Float32Array): void {
    if (!this._streaming) return;
    const copy = new Float32Array(samples);
    this.chunkBuffers.push(copy);
    this.bufferedSamples += copy.length;
    const targetSamples = Math.max(
      256,
      Math.floor((this.sampleRate * this.targetChunkMs) / 1000)
    );
    if (this.bufferedSamples >= targetSamples) {
      this.flushAudio();
    }
  }

  private flushAudio(): void {
    if (!this.bufferedSamples || !this.callbacks) return;
    const merged = new Float32Array(this.bufferedSamples);
    let offset = 0;
    for (const chunk of this.chunkBuffers) {
      merged.set(chunk, offset);
      offset += chunk.length;
    }
    this.chunkBuffers = [];
    this.bufferedSamples = 0;

    const pcm = float32ToInt16(merged);
    this.sequence += 1;
    const metadata: AudioMetadata = {
      sampleRate: this.sampleRate,
      channels: 1,
      format: "pcm_s16le",
      frames: pcm.length,
      sentAt: performance.now(),
      clientPlatform: "web",
      clientProtocolVersion: "1.0",
      sequence: this.sequence,
    };
    const packet = encodeAudioPacket(metadata, pcm.buffer as ArrayBuffer);
    this.callbacks.onPacket(packet);
  }
}
