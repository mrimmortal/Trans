'use client';

import { useEffect, useRef, useState } from 'react';
import { X, Sliders } from 'lucide-react';
import { AppSettings } from '@/types';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  settings: AppSettings;
  onUpdateSettings: (partial: Partial<AppSettings>) => void;
}

type Tab = 'audio' | 'transcription' | 'editor' | 'about';

export function SettingsModal({
  isOpen,
  onClose,
  settings,
  onUpdateSettings,
}: SettingsModalProps) {
  const [activeTab, setActiveTab] = useState<Tab>('audio');
  const [audioDevices, setAudioDevices] = useState<MediaDeviceInfo[]>([]);
  const modalRef = useRef<HTMLDivElement>(null);

  // Enumerate audio devices
  useEffect(() => {
    const enumerateDevices = async () => {
      try {
        const devices = await navigator.mediaDevices.enumerateDevices();
        const audioDevs = devices.filter((d) => d.kind === 'audioinput');
        setAudioDevices(audioDevs);
      } catch (e) {
        console.warn('Failed to enumerate audio devices:', e);
      }
    };
    enumerateDevices();
  }, []);

  // Close on Escape
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };

    if (isOpen) {
      document.addEventListener('keydown', handleEscape);
      return () => document.removeEventListener('keydown', handleEscape);
    }
  }, [isOpen, onClose]);

  // Close on click outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (modalRef.current && !modalRef.current.contains(e.target as Node)) {
        onClose();
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [isOpen, onClose]);

  // Trap focus inside modal
  useEffect(() => {
    if (isOpen && modalRef.current) {
      const firstFocusable = modalRef.current.querySelector<HTMLElement>(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      );
      firstFocusable?.focus();
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const tabs: { id: Tab; label: string }[] = [
    { id: 'audio', label: 'Audio' },
    { id: 'transcription', label: 'Transcription' },
    { id: 'editor', label: 'Editor' },
    { id: 'about', label: 'About' },
  ];

  return (
    <div
      className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4 settings-modal"
      role="dialog"
      aria-modal="true"
      aria-label="Settings"
    >
      <div
        ref={modalRef}
        className="bg-white rounded-lg max-w-2xl w-full max-h-[80vh] overflow-hidden flex flex-col"
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 bg-white sticky top-0">
          <div className="flex items-center gap-3">
            <Sliders className="w-5 h-5 text-gray-700" aria-hidden="true" />
            <h2 className="text-xl font-semibold text-gray-900" id="settings-modal-title">Settings</h2>
          </div>
          <button
            onClick={onClose}
            className="p-1 hover:bg-gray-100 rounded-lg transition-colors"
            aria-label="Close settings"
            tabIndex={0}
          >
            <X className="w-5 h-5 text-gray-600" aria-hidden="true" />
          </button>
        </div>

        {/* Content */}
        <div className="flex flex-1 overflow-hidden">
          {/* Tabs */}
          <div className="w-40 bg-gray-50 border-r border-gray-200 flex flex-col" role="tablist" aria-label="Settings tabs">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-4 py-3 text-sm font-medium text-left transition-colors border-l-2 ${activeTab === tab.id
                    ? 'bg-white border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-700 hover:bg-gray-100'
                  }`}
                role="tab"
                aria-selected={activeTab === tab.id}
                aria-controls={`settings-panel-${tab.id}`}
                id={`settings-tab-${tab.id}`}
                tabIndex={0}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Content Area */}
          <div className="flex-1 overflow-y-auto p-6 space-y-6">
            {/* Audio Section */}
            {activeTab === 'audio' && (
              <div className="space-y-6" role="tabpanel" id="settings-panel-audio" aria-labelledby="settings-tab-audio">
                <div>
                  <label className="block text-sm font-semibold text-gray-900 mb-2" htmlFor="settings-microphone">
                    Microphone
                  </label>
                  <select
                    id="settings-microphone"
                    value={settings.audio.deviceId}
                    onChange={(e) =>
                      onUpdateSettings({
                        audio: { ...settings.audio, deviceId: e.target.value },
                      })
                    }
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    aria-label="Select microphone device"
                  >
                    <option value="">Default microphone</option>
                    {audioDevices.map((device) => (
                      <option key={device.deviceId} value={device.deviceId}>
                        {device.label || `Microphone ${device.deviceId.slice(0, 5)}`}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <label className="text-sm font-medium text-gray-900" htmlFor="settings-noise-suppression">
                        Noise Suppression
                      </label>
                      <p className="text-xs text-gray-600 mt-0.5">
                        Reduce background noise in audio
                      </p>
                    </div>
                    <input
                      id="settings-noise-suppression"
                      type="checkbox"
                      checked={settings.audio.noiseSuppression}
                      onChange={(e) =>
                        onUpdateSettings({
                          audio: {
                            ...settings.audio,
                            noiseSuppression: e.target.checked,
                          },
                        })
                      }
                      className="w-5 h-5 rounded border-gray-300 text-blue-600 cursor-pointer"
                      aria-label="Toggle noise suppression"
                    />
                  </div>

                  <div className="flex items-center justify-between">
                    <div>
                      <label className="text-sm font-medium text-gray-900" htmlFor="settings-echo-cancellation">
                        Echo Cancellation
                      </label>
                      <p className="text-xs text-gray-600 mt-0.5">
                        Remove speaker echo from recording
                      </p>
                    </div>
                    <input
                      id="settings-echo-cancellation"
                      type="checkbox"
                      checked={settings.audio.echoCancellation}
                      onChange={(e) =>
                        onUpdateSettings({
                          audio: {
                            ...settings.audio,
                            echoCancellation: e.target.checked,
                          },
                        })
                      }
                      className="w-5 h-5 rounded border-gray-300 text-blue-600 cursor-pointer"
                      aria-label="Toggle echo cancellation"
                    />
                  </div>

                  <div className="flex items-center justify-between">
                    <div>
                      <label className="text-sm font-medium text-gray-900" htmlFor="settings-auto-gain">
                        Auto Gain Control
                      </label>
                      <p className="text-xs text-gray-600 mt-0.5">
                        Automatically adjust microphone level
                      </p>
                    </div>
                    <input
                      id="settings-auto-gain"
                      type="checkbox"
                      checked={settings.audio.autoGainControl}
                      onChange={(e) =>
                        onUpdateSettings({
                          audio: {
                            ...settings.audio,
                            autoGainControl: e.target.checked,
                          },
                        })
                      }
                      className="w-5 h-5 rounded border-gray-300 text-blue-600 cursor-pointer"
                      aria-label="Toggle auto gain control"
                    />
                  </div>
                </div>
              </div>
            )}

            {/* Transcription Section */}
            {activeTab === 'transcription' && (
              <div className="space-y-6" role="tabpanel" id="settings-panel-transcription" aria-labelledby="settings-tab-transcription">
                <div>
                  <label className="block text-sm font-semibold text-gray-900 mb-2" htmlFor="settings-language">
                    Language
                  </label>
                  <select
                    id="settings-language"
                    value={settings.transcription.language}
                    onChange={(e) =>
                      onUpdateSettings({
                        transcription: {
                          ...settings.transcription,
                          language: e.target.value,
                        },
                      })
                    }
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    aria-label="Select transcription language"
                  >
                    <option value="en">English</option>
                    <option value="es">Spanish</option>
                    <option value="fr">French</option>
                    <option value="de">German</option>
                    <option value="hi">Hindi</option>
                  </select>
                </div>

                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <label className="text-sm font-medium text-gray-900" htmlFor="settings-auto-punctuation">
                        Auto-Punctuation
                      </label>
                      <p className="text-xs text-gray-600 mt-0.5">
                        Automatically add punctuation to transcription
                      </p>
                    </div>
                    <input
                      id="settings-auto-punctuation"
                      type="checkbox"
                      checked={settings.transcription.autoPunctuation}
                      onChange={(e) =>
                        onUpdateSettings({
                          transcription: {
                            ...settings.transcription,
                            autoPunctuation: e.target.checked,
                          },
                        })
                      }
                      className="w-5 h-5 rounded border-gray-300 text-blue-600 cursor-pointer"
                      aria-label="Toggle auto-punctuation"
                    />
                  </div>

                  <div className="flex items-center justify-between">
                    <div>
                      <label className="text-sm font-medium text-gray-900" htmlFor="settings-medical-formatting">
                        Medical Formatting
                      </label>
                      <p className="text-xs text-gray-600 mt-0.5">
                        Format medical terminology and abbreviations
                      </p>
                    </div>
                    <input
                      id="settings-medical-formatting"
                      type="checkbox"
                      checked={settings.transcription.medicalFormatting}
                      onChange={(e) =>
                        onUpdateSettings({
                          transcription: {
                            ...settings.transcription,
                            medicalFormatting: e.target.checked,
                          },
                        })
                      }
                      className="w-5 h-5 rounded border-gray-300 text-blue-600 cursor-pointer"
                      aria-label="Toggle medical formatting"
                    />
                  </div>
                </div>
              </div>
            )}

            {/* Editor Section */}
            {activeTab === 'editor' && (
              <div className="space-y-6" role="tabpanel" id="settings-panel-editor" aria-labelledby="settings-tab-editor">
                <div>
                  <label className="block text-sm font-semibold text-gray-900 mb-3" htmlFor="settings-font-size">
                    Font Size: {settings.editor.fontSize}px
                  </label>
                  <input
                    id="settings-font-size"
                    type="range"
                    min="12"
                    max="24"
                    step="1"
                    value={settings.editor.fontSize}
                    onChange={(e) =>
                      onUpdateSettings({
                        editor: {
                          ...settings.editor,
                          fontSize: parseInt(e.target.value),
                        },
                      })
                    }
                    className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
                    aria-label={`Font size: ${settings.editor.fontSize}px`}
                  />
                  <div className="flex justify-between text-xs text-gray-500 mt-2">
                    <span>12px</span>
                    <span>24px</span>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-semibold text-gray-900 mb-2" htmlFor="settings-font-family">
                    Font Family
                  </label>
                  <select
                    id="settings-font-family"
                    value={settings.editor.fontFamily}
                    onChange={(e) =>
                      onUpdateSettings({
                        editor: {
                          ...settings.editor,
                          fontFamily: e.target.value,
                        },
                      })
                    }
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    aria-label="Select font family"
                  >
                    <option value="system-ui">System Default</option>
                    <option value="Georgia">Georgia</option>
                    <option value="Arial">Arial</option>
                    <option value="'Times New Roman'">Times New Roman</option>
                  </select>
                </div>

                <div className="flex items-center justify-between pt-2">
                  <div>
                    <label className="text-sm font-medium text-gray-900" htmlFor="settings-command-notifications">
                      Voice Command Notifications
                    </label>
                    <p className="text-xs text-gray-600 mt-0.5">
                      Show notifications when commands are executed
                    </p>
                  </div>
                  <input
                    id="settings-command-notifications"
                    type="checkbox"
                    checked={settings.editor.showCommandNotifications}
                    onChange={(e) =>
                      onUpdateSettings({
                        editor: {
                          ...settings.editor,
                          showCommandNotifications: e.target.checked,
                        },
                      })
                    }
                    className="w-5 h-5 rounded border-gray-300 text-blue-600 cursor-pointer"
                    aria-label="Toggle voice command notifications"
                  />
                </div>
              </div>
            )}

            {/* About Section */}
            {activeTab === 'about' && (
              <div className="space-y-4" role="tabpanel" id="settings-panel-about" aria-labelledby="settings-tab-about">
                <div>
                  <h3 className="text-lg font-semibold text-gray-900 mb-2">
                    MedDictate v1.0.0
                  </h3>
                  <p className="text-sm text-gray-600">
                    Medical voice dictation made simple and accurate.
                  </p>
                </div>

                <div className="border-t border-gray-200 pt-4">
                  <p className="text-sm text-gray-600">
                    Built with{' '}
                    <span className="font-semibold">Whisper AI</span>,{' '}
                    <span className="font-semibold">FastAPI</span>, and{' '}
                    <span className="font-semibold">Next.js</span>
                  </p>
                </div>

                <div className="border-t border-gray-200 pt-4">
                  <p className="text-xs text-gray-500">
                    © 2026 MedDictate. All rights reserved.
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-gray-200 bg-gray-50">
          <button
            onClick={onClose}
            className="px-4 py-2 text-gray-700 font-medium text-sm hover:bg-gray-200 rounded-lg transition-colors"
            aria-label="Close settings"
            tabIndex={0}
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
