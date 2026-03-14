// hooks/useAudioRecorder.ts
'use client';

import { useState, useRef, useCallback, useEffect } from 'react';

interface AudioRecorderOptions {
  sampleRate?: number;
  channelCount?: number;
  onAudioData?: (data: ArrayBuffer) => void;
  onError?: (error: string) => void;
  chunkIntervalMs?: number;
}

interface AudioRecorderHook {
  isRecording: boolean;
  isInitialized: boolean;
  error: string | null;
  audioLevel: number;
  startRecording: () => Promise<void>;
  stopRecording: () => void;
  toggleRecording: () => Promise<void>;
}

/**
 * Hook for recording audio from microphone and streaming PCM data.
 * Outputs 16-bit PCM at 16kHz mono - format expected by Whisper.
 */
export function useAudioRecorder(options: AudioRecorderOptions = {}): AudioRecorderHook {
  const {
    sampleRate = 16000,
    channelCount = 1,
    onAudioData,
    onError,
    chunkIntervalMs = 100, // Send audio every 100ms
  } = options;

  const [isRecording, setIsRecording] = useState(false);
  const [isInitialized, setIsInitialized] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [audioLevel, setAudioLevel] = useState(0);

  const audioContextRef = useRef<AudioContext | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const workletNodeRef = useRef<AudioWorkletNode | null>(null);
  const sourceNodeRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const animationFrameRef = useRef<number | null>(null);

  // Alternative: ScriptProcessor for broader compatibility
  const scriptProcessorRef = useRef<ScriptProcessorNode | null>(null);
  const audioBufferRef = useRef<Float32Array[]>([]);
  const chunkIntervalRef = useRef<number | null>(null);

  // Cleanup function
  const cleanup = useCallback(() => {
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
      animationFrameRef.current = null;
    }

    if (chunkIntervalRef.current) {
      clearInterval(chunkIntervalRef.current);
      chunkIntervalRef.current = null;
    }

    if (workletNodeRef.current) {
      workletNodeRef.current.disconnect();
      workletNodeRef.current = null;
    }

    if (scriptProcessorRef.current) {
      scriptProcessorRef.current.disconnect();
      scriptProcessorRef.current = null;
    }

    if (sourceNodeRef.current) {
      sourceNodeRef.current.disconnect();
      sourceNodeRef.current = null;
    }

    if (analyserRef.current) {
      analyserRef.current.disconnect();
      analyserRef.current = null;
    }

    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }

    if (audioContextRef.current && audioContextRef.current.state !== 'closed') {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }

    audioBufferRef.current = [];
    setAudioLevel(0);
  }, []);

  // Convert Float32 to Int16 PCM
  const floatTo16BitPCM = useCallback((float32Array: Float32Array): ArrayBuffer => {
    const buffer = new ArrayBuffer(float32Array.length * 2);
    const view = new DataView(buffer);
    
    for (let i = 0; i < float32Array.length; i++) {
      // Clamp and convert to 16-bit
      const s = Math.max(-1, Math.min(1, float32Array[i]));
      view.setInt16(i * 2, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
    }
    
    return buffer;
  }, []);

  // Downsample audio to target sample rate
  const downsample = useCallback((buffer: Float32Array, inputSampleRate: number, outputSampleRate: number): Float32Array => {
    if (inputSampleRate === outputSampleRate) {
      return buffer;
    }
    
    const ratio = inputSampleRate / outputSampleRate;
    const newLength = Math.round(buffer.length / ratio);
    const result = new Float32Array(newLength);
    
    for (let i = 0; i < newLength; i++) {
      const index = Math.round(i * ratio);
      result[i] = buffer[index];
    }
    
    return result;
  }, []);

  // Process and send accumulated audio
  const processAudioBuffer = useCallback(() => {
    if (audioBufferRef.current.length === 0) return;

    // Concatenate all buffered chunks
    const totalLength = audioBufferRef.current.reduce((sum, arr) => sum + arr.length, 0);
    const combined = new Float32Array(totalLength);
    
    let offset = 0;
    for (const chunk of audioBufferRef.current) {
      combined.set(chunk, offset);
      offset += chunk.length;
    }
    
    // Clear buffer
    audioBufferRef.current = [];

    // Downsample if needed
    const inputSampleRate = audioContextRef.current?.sampleRate || 48000;
    const downsampled = downsample(combined, inputSampleRate, sampleRate);

    // Convert to 16-bit PCM
    const pcmData = floatTo16BitPCM(downsampled);

    // Send to callback
    if (onAudioData) {
      onAudioData(pcmData);
    }
  }, [sampleRate, downsample, floatTo16BitPCM, onAudioData]);

  // Update audio level visualization
  const updateAudioLevel = useCallback(() => {
    if (!analyserRef.current || !isRecording) return;

    const dataArray = new Uint8Array(analyserRef.current.frequencyBinCount);
    analyserRef.current.getByteFrequencyData(dataArray);

    // Calculate RMS
    let sum = 0;
    for (let i = 0; i < dataArray.length; i++) {
      sum += dataArray[i] * dataArray[i];
    }
    const rms = Math.sqrt(sum / dataArray.length);
    const normalizedLevel = Math.min(rms / 128, 1);
    
    setAudioLevel(normalizedLevel);

    animationFrameRef.current = requestAnimationFrame(updateAudioLevel);
  }, [isRecording]);

  // Start recording
  const startRecording = useCallback(async () => {
    try {
      setError(null);

      // Request microphone permission
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: channelCount,
          sampleRate: { ideal: sampleRate },
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });
      streamRef.current = stream;

      // Create audio context
      const audioContext = new AudioContext({ sampleRate: sampleRate });
      audioContextRef.current = audioContext;

      // Resume if suspended
      if (audioContext.state === 'suspended') {
        await audioContext.resume();
      }

      // Create source from microphone
      const source = audioContext.createMediaStreamSource(stream);
      sourceNodeRef.current = source;

      // Create analyser for visualization
      const analyser = audioContext.createAnalyser();
      analyser.fftSize = 256;
      analyserRef.current = analyser;
      source.connect(analyser);

      // Use ScriptProcessor for compatibility (AudioWorklet is preferred but more complex)
      const bufferSize = 4096;
      const scriptProcessor = audioContext.createScriptProcessor(bufferSize, channelCount, channelCount);
      scriptProcessorRef.current = scriptProcessor;

      scriptProcessor.onaudioprocess = (event) => {
        if (!isRecording) return;
        
        const inputData = event.inputBuffer.getChannelData(0);
        // Clone the data since the buffer will be reused
        audioBufferRef.current.push(new Float32Array(inputData));
      };

      source.connect(scriptProcessor);
      scriptProcessor.connect(audioContext.destination);

      // Start chunk interval
      chunkIntervalRef.current = window.setInterval(processAudioBuffer, chunkIntervalMs);

      setIsRecording(true);
      setIsInitialized(true);

      // Start audio level updates
      animationFrameRef.current = requestAnimationFrame(updateAudioLevel);

      console.log('[AudioRecorder] Started recording');

    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to access microphone';
      console.error('[AudioRecorder] Error:', errorMessage);
      setError(errorMessage);
      onError?.(errorMessage);
      cleanup();
    }
  }, [sampleRate, channelCount, chunkIntervalMs, isRecording, processAudioBuffer, updateAudioLevel, cleanup, onError]);

  // Stop recording
  const stopRecording = useCallback(() => {
    console.log('[AudioRecorder] Stopping recording');
    
    // Process any remaining audio
    processAudioBuffer();
    
    setIsRecording(false);
    cleanup();
  }, [processAudioBuffer, cleanup]);

  // Toggle recording
  const toggleRecording = useCallback(async () => {
    if (isRecording) {
      stopRecording();
    } else {
      await startRecording();
    }
  }, [isRecording, startRecording, stopRecording]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      cleanup();
    };
  }, [cleanup]);

  // Update isRecording ref for the script processor callback
  useEffect(() => {
    if (scriptProcessorRef.current) {
      scriptProcessorRef.current.onaudioprocess = (event) => {
        if (!isRecording) return;
        const inputData = event.inputBuffer.getChannelData(0);
        audioBufferRef.current.push(new Float32Array(inputData));
      };
    }
  }, [isRecording]);

  return {
    isRecording,
    isInitialized,
    error,
    audioLevel,
    startRecording,
    stopRecording,
    toggleRecording,
  };
}