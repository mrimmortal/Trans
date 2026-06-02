'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { AssistantApiError, requestAssistantResponse } from '@/services/assistantApi';
import { synthesizeSpeech, TTSApiError } from '@/services/ttsApi';
import { AssistantStage, LocalAssistantErrorCode } from '@/types';

interface LocalAssistantState {
  responseText: string;
  audioUrl: string | null;
  stage: AssistantStage;
  error: string | null;
  errorCode: LocalAssistantErrorCode | null;
  lastRequestId: string | null;
  lastLlmRequestId: string | null;
  lastTtsRequestId: string | null;
}

const INITIAL_STATE: LocalAssistantState = {
  responseText: '',
  audioUrl: null,
  stage: 'idle',
  error: null,
  errorCode: null,
  lastRequestId: null,
  lastLlmRequestId: null,
  lastTtsRequestId: null,
};

export function useLocalAssistant() {
  const [state, setState] = useState<LocalAssistantState>(INITIAL_STATE);
  const audioUrlRef = useRef<string | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const revokeAudioUrl = useCallback((url: string | null) => {
    if (url) {
      URL.revokeObjectURL(url);
    }
  }, []);

  const playAudio = useCallback(async (url: string) => {
    audioRef.current?.pause();

    setState((prev) => ({ ...prev, stage: 'playing', error: null, errorCode: null }));

      const audio = new Audio(url);
    audioRef.current = audio;
    audio.onended = () => {
      if (audioRef.current === audio) {
        setState((prev) => ({ ...prev, stage: 'idle' }));
      }
    };

    try {
      await audio.play();
    } catch {
      if (audioRef.current === audio) {
        audioRef.current = null;
      }
      setState((prev) => ({
        ...prev,
        stage: 'idle',
        error: 'Speech generated, but browser playback was blocked.',
        errorCode: 'REQUEST_FAILED',
      }));
    }
  }, []);

  const runAssistant = useCallback(
    async (transcript: string) => {
      const cleanTranscript = transcript.trim();
      if (!cleanTranscript) {
        setState((prev) => ({
          ...prev,
          error: 'Transcript is empty.',
          errorCode: 'REQUEST_FAILED',
        }));
        return;
      }

      setState((prev) => ({
        ...prev,
        stage: 'generating-response',
        error: null,
        errorCode: null,
      }));

      try {
        const assistantResponse = await requestAssistantResponse(cleanTranscript);

        setState((prev) => ({
          ...prev,
          responseText: assistantResponse.response,
          stage: 'generating-speech',
          lastRequestId: assistantResponse.request_id || prev.lastRequestId,
          lastLlmRequestId: assistantResponse.request_id || prev.lastLlmRequestId,
        }));

        const ttsResult = await synthesizeSpeech(assistantResponse.response);
        const audioUrl = ttsResult.audioUrl;
        revokeAudioUrl(audioUrlRef.current);
        audioUrlRef.current = audioUrl;

        setState((prev) => ({
          ...prev,
          audioUrl,
          stage: 'idle',
          lastRequestId: ttsResult.request_id || prev.lastRequestId,
          lastTtsRequestId: ttsResult.request_id || prev.lastTtsRequestId,
        }));

        await playAudio(audioUrl);
      } catch (error) {
        setState((prev) => ({
          ...prev,
          stage: 'idle',
          ...mapAssistantError(error),
        }));
      }
    },
    [playAudio, revokeAudioUrl]
  );

  const replayAudio = useCallback(() => {
    if (audioUrlRef.current) {
      void playAudio(audioUrlRef.current);
    }
  }, [playAudio]);

  const clearAssistant = useCallback(() => {
    audioRef.current?.pause();
    audioRef.current = null;
    revokeAudioUrl(audioUrlRef.current);
    audioUrlRef.current = null;
    setState(INITIAL_STATE);
  }, [revokeAudioUrl]);

  useEffect(() => {
    return () => {
      audioRef.current?.pause();
      revokeAudioUrl(audioUrlRef.current);
    };
  }, [revokeAudioUrl]);

  return {
    ...state,
    isGeneratingResponse: state.stage === 'generating-response',
    isGeneratingSpeech: state.stage === 'generating-speech',
    isBusy: state.stage !== 'idle',
    runAssistant,
    replayAudio,
    clearAssistant,
  };
}

function mapAssistantError(
  error: unknown
): Partial<Pick<LocalAssistantState, 'error' | 'errorCode' | 'lastRequestId' | 'lastLlmRequestId' | 'lastTtsRequestId'>> {
  if (error instanceof AssistantApiError && error.code === 'LM_STUDIO_UNAVAILABLE') {
    return {
      error: 'LM Studio unavailable.',
      errorCode: 'LM_STUDIO_UNAVAILABLE',
      lastRequestId: error.requestId || null,
      lastLlmRequestId: error.requestId || null,
    };
  }

  if (error instanceof TTSApiError && error.code === 'TTS_UNAVAILABLE') {
    return {
      error: 'TTS unavailable.',
      errorCode: 'TTS_UNAVAILABLE',
      lastRequestId: error.requestId || null,
      lastTtsRequestId: error.requestId || null,
    };
  }

  const mapped: Partial<
    Pick<LocalAssistantState, 'error' | 'errorCode' | 'lastRequestId' | 'lastLlmRequestId' | 'lastTtsRequestId'>
  > = {
    error: 'Assistant request failed.',
    errorCode: 'REQUEST_FAILED',
  };

  if (error instanceof AssistantApiError) {
    mapped.lastRequestId = error.requestId || null;
    mapped.lastLlmRequestId = error.requestId || null;
  } else if (error instanceof TTSApiError) {
    mapped.lastRequestId = error.requestId || null;
    mapped.lastTtsRequestId = error.requestId || null;
  }

  return mapped;
}
