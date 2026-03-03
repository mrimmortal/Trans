'use client';

import { useState, useEffect } from 'react';
import { AppSettings } from '@/types';

const DEFAULT_SETTINGS: AppSettings = {
  audio: {
    deviceId: '',
    noiseSuppression: true,
    echoCancellation: true,
    autoGainControl: true,
    silenceSensitivity: 0.008,
  },
  transcription: {
    language: 'en',
    autoPunctuation: true,
    medicalFormatting: true,
  },
  editor: {
    fontSize: 16,
    fontFamily: 'system-ui',
    darkMode: false,
    showCommandNotifications: true,
  },
};

export function useSettings() {
  const [settings, setSettings] = useState<AppSettings>(DEFAULT_SETTINGS);
  const [isLoaded, setIsLoaded] = useState(false);

  // Load settings from localStorage on mount
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('medDictateSettings');
      if (saved) {
        try {
          const parsed = JSON.parse(saved);
          setSettings({ ...DEFAULT_SETTINGS, ...parsed });
        } catch (e) {
          console.warn('Failed to load settings from localStorage:', e);
          setSettings(DEFAULT_SETTINGS);
        }
      } else {
        setSettings(DEFAULT_SETTINGS);
      }
      setIsLoaded(true);
    }
  }, []);

  // Update settings and persist to localStorage
  const updateSettings = (partial: Partial<AppSettings>) => {
    setSettings((prev) => {
      const updated = { ...prev };
      
      // Deep merge for nested objects
      if (partial.audio) {
        updated.audio = { ...prev.audio, ...partial.audio };
      }
      if (partial.transcription) {
        updated.transcription = { ...prev.transcription, ...partial.transcription };
      }
      if (partial.editor) {
        updated.editor = { ...prev.editor, ...partial.editor };
      }

      // Persist to localStorage
      if (typeof window !== 'undefined') {
        localStorage.setItem('medDictateSettings', JSON.stringify(updated));
      }

      return updated;
    });
  };

  // Reset to defaults
  const resetSettings = () => {
    setSettings(DEFAULT_SETTINGS);
    if (typeof window !== 'undefined') {
      localStorage.removeItem('medDictateSettings');
    }
  };

  return { settings, updateSettings, resetSettings, isLoaded };
}
