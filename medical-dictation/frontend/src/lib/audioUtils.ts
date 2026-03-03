/**
 * Audio utility functions for processing and handling audio data
 *
 * These helpers are primarily concerned with converting and measuring
 * audio data coming from the browser so it matches Whisper's expectations.
 * A common and critical bug is sending audio at the wrong sample rate; the
 * backend silently transcribes garbage when fed 44.1kHz/48kHz instead of
 * 16kHz.  The functions below prevent that by downsampling and converting to
 * 16‑bit PCM before transmission.
 */

/**
 * Convert audio blob to base64 string
 */
export async function blobToBase64(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onloadend = () => {
      const base64 = reader.result as string;
      resolve(base64.split(",")[1]); // Remove data:audio/webm;base64, prefix
    };
    reader.onerror = reject;
    reader.readAsDataURL(blob);
  });
}

/**
 * Convert audio blob to WAV format for Whisper processing
 * TODO: Implement WAV conversion using audio resampler if needed
 */
export async function convertToWav(blob: Blob): Promise<Blob> {
  // For now, return as-is
  // TODO: Implement proper WAV conversion with resampling to 16kHz
  return blob;
}

/**
 * Resample audio to 16kHz (Whisper requirement)
 * TODO: Implement audio resampling
 */
export async function resampleAudio(
  audioBuffer: AudioBuffer,
  targetSampleRate: number = 16000
): Promise<AudioBuffer> {
  // TODO: Implement resampling logic
  return audioBuffer;
}

/**
 * Calculate audio duration in seconds
 */
export function calculateDuration(blob: Blob, sampleRate: number = 16000): number {
  // Rough estimate: assume 2 bytes per sample (16-bit)
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
 * Downsample a Float32Array from a higher sample rate to a lower one.  The
 * result is another Float32Array at the target rate, still containing values
 * between -1.0 and +1.0.  Whisper requires 16kHz input, so this method is
 * routinely used to convert 44.1kHz or 48kHz audio captured by the browser.
 * Failing to downsample is the root cause of the most common bug in the
 * system (#1): the model either returns nonsense or throws an error.
 *
 * Upsampling is forbidden because it would invent samples and degrade
 * recognition quality.  The algorithm below uses linear interpolation based
 * on the ratio of the two sample rates.
 *
 * For two rates `inRate` and `outRate`, we compute `ratio = inRate / outRate`.
 * Each output sample at index `i` corresponds to position `i * ratio` in the
 * input buffer.  We interpolate between the surrounding input samples using
 * the fractional remainder.  The output length is approximately
 * `input.length / ratio` and is rounded to the nearest integer.
 *
 * @param inputBuffer samples normalized between -1.0 and +1.0
 * @param inputSampleRate the rate at which `inputBuffer` was recorded
 * @param outputSampleRate the desired rate (typically 16000)
 * @returns a Float32Array containing samples at the output rate
 * @throws {Error} when attempting to upsample
 */
export function downsampleBuffer(
  inputBuffer: Float32Array,
  inputSampleRate: number,
  outputSampleRate: number
): Float32Array {
  if (outputSampleRate === inputSampleRate) {
    // return a copy to avoid accidental mutation
    return new Float32Array(inputBuffer);
  }

  if (outputSampleRate > inputSampleRate) {
    throw new Error(
      `Cannot upsample audio from ${inputSampleRate} to ${outputSampleRate}`
    );
  }

  const ratio = inputSampleRate / outputSampleRate;
  const outputLength = Math.round(inputBuffer.length / ratio);
  console.log(`Downsample: ${inputBuffer.length} @ ${inputSampleRate} -> ${outputLength} @ ${outputSampleRate}`);
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
 * Convert a Float32Array of audio samples to 16-bit PCM without resampling.
 * Used internally when the sample rates already match.
 *
 * @param buffer input samples
 * @returns ArrayBuffer containing Int16 data
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
 * Compute the root-mean-square (RMS) level of a buffer.  This value is
 * frequently used for audio level meters because it relates to perceived
 * loudness.
 *
 * @param buffer float samples
 * @returns RMS value between 0 and 1
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
 * Determine the peak amplitude in the buffer.  Useful for clipping
 * detection or simple peak meters.
 *
 * @param buffer float samples
 * @returns maximum absolute sample value
 */
export function calculatePeak(buffer: Float32Array): number {
  let peak = 0;
  for (let i = 0; i < buffer.length; i++) {
    const abs = Math.abs(buffer[i]);
    if (abs > peak) peak = abs;
  }
  return peak;
}
