'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import { downsampleBuffer, calculateRMS } from '../lib/audioUtils';

interface UseAudioRecorder {
  isRecording: boolean;
  isPaused: boolean;
  duration: number;
  audioLevel: number;
  error: string | null;
  startRecording: (onAudioChunk: (chunk: ArrayBuffer) => void) => Promise<void>;
  stopRecording: () => void;
  pauseRecording: () => void;
  resumeRecording: () => void;
}

/**
 * Microphone -> MediaStream -> AudioContext -> MediaStreamSource ->
 * ScriptProcessorNode (bufferSize=4096) -> downsampleBuffer (browser rate
 * -> 16kHz) -> accumulate -> send interval -> websocket.
 *
 * We intentionally use ScriptProcessorNode instead of AudioWorklet because
 * the latter requires a separate file and much more boilerplate.  For voice
 * dictation the latency and CPU characteristics of ScriptProcessor are more
 * than adequate, and browser support is universal.
 */
export function useAudioRecorder(): UseAudioRecorder {
  const [isRecording, setIsRecording] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [duration, setDuration] = useState(0);
  const [audioLevel, setAudioLevel] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const audioContextRef = useRef<AudioContext | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const scriptProcessorRef = useRef<ScriptProcessorNode | null>(null);
  const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const sendIntervalRef = useRef<number | null>(null);
  const durationIntervalRef = useRef<number | null>(null);
  const audioChunksRef = useRef<Float32Array[]>([]);
  const onAudioChunkRef = useRef<((chunk: ArrayBuffer) => void) | null>(null);
  const isRecordingRef = useRef(false);

  const startRecording = useCallback(async (onAudioChunk: (chunk: ArrayBuffer) => void) => {
    setError(null);
    onAudioChunkRef.current = onAudioChunk;

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          channelCount: 1,
          sampleRate: { ideal: 16000 },
        },
      });
      mediaStreamRef.current = stream;

      const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
      audioContextRef.current = audioContext;
      const AUDIO_SAMPLE_RATE = 16000;
      console.log(`AudioContext: ${audioContext.sampleRate}Hz, Target: ${AUDIO_SAMPLE_RATE}Hz`);

      const source = audioContext.createMediaStreamSource(stream);
      sourceRef.current = source;

      const processor = audioContext.createScriptProcessor(4096, 1, 1);
      scriptProcessorRef.current = processor;

      processor.onaudioprocess = (e) => {
        if (!isRecordingRef.current) return;
        const input = e.inputBuffer.getChannelData(0);
        const buffer = new Float32Array(input.length);
        buffer.set(input);

        const rms = calculateRMS(buffer);
        setAudioLevel(rms);

        const downsampled = downsampleBuffer(buffer, audioContext.sampleRate, 16000);
        audioChunksRef.current.push(downsampled);
      };

      source.connect(processor);
      processor.connect(audioContext.destination);

      sendIntervalRef.current = window.setInterval(() => {
        const chunks = audioChunksRef.current;
        if (chunks.length === 0) return;

        let totalLength = 0;
        for (const c of chunks) totalLength += c.length;
        const merged = new Float32Array(totalLength);
        let offset = 0;
        for (const c of chunks) {
          merged.set(c, offset);
          offset += c.length;
        }

        const int16 = new Int16Array(merged.length);
        for (let i = 0; i < merged.length; i++) {
          let sample = merged[i];
          if (sample > 1) sample = 1;
          else if (sample < -1) sample = -1;
          int16[i] = sample < 0
            ? Math.round(sample * 32768)
            : Math.round(sample * 32767);
        }

        console.log(`Sending chunk: ${int16.buffer.byteLength} bytes`);
        onAudioChunkRef.current?.(int16.buffer);
        audioChunksRef.current.length = 0;
      }, 250);

      durationIntervalRef.current = window.setInterval(() => {
        setDuration((d) => d + 1);
      }, 1000);

      isRecordingRef.current = true;
      setIsRecording(true);
      setIsPaused(false);
      setDuration(0);
      setAudioLevel(0);
    } catch (err: any) {
      const name = err.name;
      if (name === 'NotAllowedError') {
        setError('Microphone permission denied. Please enable microphone access.');
      } else if (name === 'NotFoundError') {
        setError('No microphone found on this device.');
      } else if (name === 'NotReadableError') {
        setError('Microphone in use by another application.');
      } else {
        setError('Failed to access microphone.');
      }
    }
  }, []);

  const stopRecording = useCallback(() => {
    isRecordingRef.current = false;
    if (sendIntervalRef.current !== null) {
      clearInterval(sendIntervalRef.current);
      sendIntervalRef.current = null;
    }
    if (durationIntervalRef.current !== null) {
      clearInterval(durationIntervalRef.current);
      durationIntervalRef.current = null;
    }

    if (scriptProcessorRef.current) {
      scriptProcessorRef.current.onaudioprocess = null;
      scriptProcessorRef.current.disconnect();
    }
    if (sourceRef.current) {
      sourceRef.current.disconnect();
    }
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((t) => t.stop());
    }
    if (audioContextRef.current && audioContextRef.current.state !== 'closed') {
      audioContextRef.current.close();
    }

    audioChunksRef.current.length = 0;

    setIsRecording(false);
    setIsPaused(false);
    setDuration(0);
    setAudioLevel(0);
  }, []);

  const pauseRecording = useCallback(() => {
    if (audioContextRef.current) {
      audioContextRef.current.suspend();
      setIsPaused(true);
    }
  }, []);

  const resumeRecording = useCallback(() => {
    if (audioContextRef.current) {
      audioContextRef.current.resume();
      setIsPaused(false);
    }
  }, []);

  useEffect(() => {
    return () => {
      if (isRecordingRef.current) {
        stopRecording();
      }
    };
  }, [stopRecording]);

  return {
    isRecording,
    isPaused,
    duration,
    audioLevel,
    error,
    startRecording,
    stopRecording,
    pauseRecording,
    resumeRecording,
  };
}
