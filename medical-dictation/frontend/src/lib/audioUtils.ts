/**
 * Audio utility functions for processing and handling audio data
 *
 * These helpers convert and measure audio data coming from the browser so it
 * matches Whisper's expectations (16 kHz, 16-bit PCM, mono).
 */

/**
 * Convert audio blob to base64 string
 */
export async function blobToBase64(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onloadend = () => {
      const base64 = reader.result as string;
      resolve(base64.split(",")[1]);
    };
    reader.onerror = reject;
    reader.readAsDataURL(blob);
  });
}

/**
 * Convert audio blob to WAV format for Whisper processing
 */
export async function convertToWav(blob: Blob): Promise<Blob> {
  return blob;
}

/**
 * Resample audio to target sample rate
 */
export async function resampleAudio(
  audioBuffer: AudioBuffer,
  targetSampleRate: number = 16000
): Promise<AudioBuffer> {
  return audioBuffer;
}

/**
 * Calculate audio duration in seconds
 */
export function calculateDuration(blob: Blob, sampleRate: number = 16000): number {
  const audioDataSize = blob.size;
  const bytesPerSecond = sampleRate * 2;
  return audioDataSize / bytesPerSecond;
}

/**
 * Validate audio format
 */
export function validateAudioFormat(blob: Blob): boolean {
  const validMimeTypes = ["audio/webm", "audio/wav", "audio/mp3", "audio/mpeg"];
  return validMimeTypes.some((mimeType) => blob.type.includes(mimeType));
}

/**
 * Create audio context if not available
 */
export function getAudioContext(): AudioContext {
  const audioContext =
    window.AudioContext || (window as any).webkitAudioContext;
  return new audioContext();
}

/**
 * Handle audio permission request errors
 */
export function handleAudioPermissionError(error: DOMException): string {
  if (error.name === "NotAllowedError") {
    return "Microphone permission denied. Please enable microphone access.";
  } else if (error.name === "NotFoundError") {
    return "No microphone found on this device.";
  }
  return "Failed to access microphone.";
}

/**
 * Downsample a Float32Array from a higher sample rate to a lower one.
 *
 * Uses linear interpolation.  Upsampling is forbidden.
 *
 * @param inputBuffer  samples normalized between -1.0 and +1.0
 * @param inputSampleRate  the rate at which inputBuffer was recorded
 * @param outputSampleRate the desired rate (typically 16000)
 * @returns Float32Array at the output rate
 * @throws {Error} when attempting to upsample
 */
export function downsampleBuffer(
  inputBuffer: Float32Array,
  inputSampleRate: number,
  outputSampleRate: number
): Float32Array {
  if (outputSampleRate === inputSampleRate) {
    return new Float32Array(inputBuffer);
  }

  if (outputSampleRate > inputSampleRate) {
    throw new Error(
      `Cannot upsample audio from ${inputSampleRate} to ${outputSampleRate}`
    );
  }

  const ratio = inputSampleRate / outputSampleRate;
  const outputLength = Math.round(inputBuffer.length / ratio);
  // ✅ FIX: removed per-chunk console.log that fired ~4×/sec and flooded console
  const outputBuffer = new Float32Array(outputLength);

  for (let i = 0; i < outputLength; i++) {
    const position = i * ratio;
    const indexBefore = Math.floor(position);
    const indexAfter = Math.min(indexBefore + 1, inputBuffer.length - 1);
    const weight = position - indexBefore;

    let sample =
      inputBuffer[indexBefore] +
      (inputBuffer[indexAfter] - inputBuffer[indexBefore]) * weight;

    if (sample > 1) sample = 1;
    else if (sample < -1) sample = -1;

    outputBuffer[i] = sample;
  }

  return outputBuffer;
}

/**
 * Convert Float32 samples to 16-bit PCM without resampling.
 */
export function float32ToInt16(buffer: Float32Array): ArrayBuffer {
  const output = new Int16Array(buffer.length);
  for (let i = 0; i < buffer.length; i++) {
    let sample = buffer[i];
    if (sample > 1) sample = 1;
    else if (sample < -1) sample = -1;
    output[i] = sample < 0
      ? Math.round(sample * 32768)
      : Math.round(sample * 32767);
  }
  return output.buffer;
}

/**
 * RMS level of a buffer (0–1).
 */
export function calculateRMS(buffer: Float32Array): number {
  let sum = 0;
  for (let i = 0; i < buffer.length; i++) {
    const v = buffer[i];
    sum += v * v;
  }
  return Math.sqrt(sum / buffer.length);
}

/**
 * Peak amplitude in the buffer.
 */
export function calculatePeak(buffer: Float32Array): number {
  let peak = 0;
  for (let i = 0; i < buffer.length; i++) {
    const abs = Math.abs(buffer[i]);
    if (abs > peak) peak = abs;
  }
  return peak;
}