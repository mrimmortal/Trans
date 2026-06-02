'use client';

import { useEffect, useRef, useState } from 'react';
import { X, Sliders } from 'lucide-react';
import { AppSettings, BackendConfigResponse, DiagnosticsResponse, SafeSttSettings } from '@/types';
import { APP_CONFIG } from '@/lib/appConfig';
import { getBackendConfig } from '@/services/configApi';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  settings: AppSettings;
  onUpdateSettings: (partial: Partial<AppSettings>) => void;
  diagnostics?: DiagnosticsResponse | null;
}

type Tab = 'audio' | 'transcription' | 'stt' | 'editor' | 'about';

export function SettingsModal({
  isOpen,
  onClose,
  settings,
  onUpdateSettings,
  diagnostics,
}: SettingsModalProps) {
  const [activeTab, setActiveTab] = useState<Tab>('audio');
  const [audioDevices, setAudioDevices] = useState<MediaDeviceInfo[]>([]);
  const [backendConfig, setBackendConfig] = useState<BackendConfigResponse | null>(null);
  const [isConfigLoading, setIsConfigLoading] = useState(false);
  const [configError, setConfigError] = useState<string | null>(null);
  const modalRef = useRef<HTMLDivElement>(null);

  const loadBackendConfig = async () => {
    setIsConfigLoading(true);
    setConfigError(null);
    try {
      const config = await getBackendConfig();
      setBackendConfig(config);
    } catch {
      setConfigError('Backend config is unavailable.');
    } finally {
      setIsConfigLoading(false);
    }
  };

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

  useEffect(() => {
    if (isOpen) {
      void loadBackendConfig();
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const tabs: { id: Tab; label: string }[] = [
    { id: 'audio', label: 'Audio' },
    { id: 'transcription', label: 'Transcription' },
    { id: 'stt', label: 'STT' },
    { id: 'editor', label: 'Editor' },
    { id: 'about', label: 'About' },
  ];

  const sttSettings = mergeSttSettings(backendConfig);
  const sttMetrics = diagnostics?.stt?.metrics;

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
                      <label className="text-sm font-medium text-gray-900" htmlFor="settings-domain-formatting">
                        Wrapper Formatting
                      </label>
                      <p className="text-xs text-gray-600 mt-0.5">
                        Reserved for domain wrappers that transform transcript text
                      </p>
                    </div>
                    <input
                      id="settings-domain-formatting"
                      type="checkbox"
                      checked={settings.transcription.domainFormatting}
                      onChange={(e) =>
                        onUpdateSettings({
                          transcription: {
                            ...settings.transcription,
                            domainFormatting: e.target.checked,
                          },
                        })
                      }
                      className="w-5 h-5 rounded border-gray-300 text-blue-600 cursor-pointer"
                      aria-label="Toggle wrapper formatting"
                    />
                  </div>
                </div>
              </div>
            )}

            {/* STT Section */}
            {activeTab === 'stt' && (
              <div className="space-y-5" role="tabpanel" id="settings-panel-stt" aria-labelledby="settings-tab-stt">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900">
                      Transcription Engine
                    </h3>
                    <p className="text-xs text-gray-600 mt-1">
                      Read-only backend configuration. Runtime editing needs a dedicated backend settings API.
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => void loadBackendConfig()}
                    disabled={isConfigLoading}
                    className="px-3 py-1.5 rounded border border-gray-300 text-xs font-medium text-gray-700 disabled:opacity-50"
                  >
                    {isConfigLoading ? 'Refreshing...' : 'Refresh backend config'}
                  </button>
                </div>

                {configError && (
                  <div className="rounded border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
                    {configError} Values below may be stale or unknown.
                  </div>
                )}

                <ReadonlySection
                  title="Audio Contract"
                  note="Fixed protocol values expected by backend and frontend."
                  rows={[
                    settingRow('Sample rate', hz(sttSettings.sample_rate), 'Whisper-style pipelines expect 16 kHz audio.'),
                    settingRow('Channels', channels(sttSettings.channels), 'Mono keeps the browser and backend audio contract simple.'),
                    settingRow('Format', sampleFormat(sttSettings.sample_width), 'The browser converts captured audio to little-endian int16 PCM before streaming.'),
                  ]}
                />

                <ReadonlySection
                  title="Profile"
                  note="Profiles are presets; current app behavior is controlled by backend env config."
                  rows={[
                    settingRow('Active profile', sttSettings.transcription_profile || 'unknown', profileGuide(sttSettings.transcription_profile)),
                  ]}
                />

                <ReadonlySection
                  title="Model / Runtime"
                  rows={[
                    settingRow('Model size', sttSettings.model_size || 'unknown', 'Larger models may improve accuracy but need more memory and time.'),
                    settingRow('Device', sttSettings.device || 'unknown', 'CPU is broadly compatible; CUDA needs a supported NVIDIA GPU.'),
                    settingRow('Compute type', sttSettings.compute_type || 'unknown', 'CPU usually uses int8; CUDA usually uses float16.'),
                    settingRow('Language', sttSettings.language || 'unknown', 'Language is supplied to Faster-Whisper for transcription.'),
                    settingRow('Beam size', formatValue(sttSettings.beam_size), 'Lower is faster; higher may improve accuracy with more latency.'),
                    settingRow('Temperature', formatTemperature(sttSettings.temperature), '0.0 keeps decoding deterministic for realtime dictation.'),
                  ]}
                />

                <ReadonlySection
                  title="Realtime Buffering"
                  note="Shorter chunks respond faster; longer chunks give more context."
                  rows={[
                    settingRow('Min chunk', seconds(sttSettings.min_chunk_duration_seconds), 'Lower values can respond sooner but may reduce text stability.'),
                    settingRow('Max chunk', seconds(sttSettings.max_chunk_duration_seconds), 'Higher values give more context but increase latency.'),
                    settingRow('Overlap', seconds(sttSettings.overlap_duration_seconds), 'Helps avoid clipped boundary words; too much can repeat text.'),
                    settingRow('Silence timeout', seconds(sttSettings.silence_timeout_seconds), 'Lower triggers sooner; higher waits for more complete phrases.'),
                  ]}
                />

                <ReadonlySection
                  title="VAD"
                  rows={[
                    settingRow('VAD filter', booleanLabel(sttSettings.vad_filter), 'Faster-Whisper/Silero VAD skips silence before transcription.'),
                    settingRow('VAD threshold', formatValue(sttSettings.vad_parameters?.threshold), 'Higher is stricter; lower catches quieter speech but may include noise.'),
                    settingRow('Min speech', ms(sttSettings.vad_parameters?.min_speech_duration_ms), 'Speech/silence/pad values tune short-word capture and phrase splitting.'),
                    settingRow('Min silence', ms(sttSettings.vad_parameters?.min_silence_duration_ms), 'Shorter values split phrases sooner; longer values keep phrases together.'),
                    settingRow('Speech pad', ms(sttSettings.vad_parameters?.speech_pad_ms), 'Adds context around detected speech so words are not clipped.'),
                  ]}
                />

                <ReadonlySection
                  title="Hallucination / Silence Filtering"
                  note="More aggressive values reduce silence/repetition artifacts but can drop valid speech."
                  rows={[
                    settingRow('Compression ratio threshold', formatValue(sttSettings.compression_ratio_threshold), 'Lower values filter repetitive output more aggressively.'),
                    settingRow('Log probability threshold', formatValue(sttSettings.log_prob_threshold), 'Stricter values filter uncertain decoding.'),
                    settingRow('No-speech threshold', formatValue(sttSettings.no_speech_threshold), 'Higher values filter more silence-like output.'),
                    settingRow('Min confidence', formatValue(sttSettings.min_transcription_confidence), 'Filters very low-confidence text when configured.'),
                    settingRow('Max no-speech probability', formatValue(sttSettings.hallucination_max_no_speech_prob), 'Drops text when Whisper thinks the segment was likely silence.'),
                    settingRow('Hallucination silence threshold', disabledLabel(sttSettings.hallucination_silence_threshold_enabled), 'Not enabled because word timestamps are disabled.'),
                  ]}
                />

                <ReadonlySection
                  title="Diagnostics Summary"
                  note="RTF below 1.0 is faster than realtime; below 0.5 is better for responsive dictation."
                  rows={[
                    settingRow('Last RTF', formatValue(sttMetrics?.last_real_time_factor), 'Most recent transcription speed relative to audio duration.'),
                    settingRow('Average RTF', formatValue(sttMetrics?.average_real_time_factor), 'Average processing speed across completed transcriptions.'),
                    settingRow('Last processing time', ms(sttMetrics?.last_processing_time_ms), 'Backend time spent processing the latest transcription.'),
                    settingRow('Last audio duration', seconds(sttMetrics?.last_audio_duration_seconds), 'Audio duration of the latest transcription buffer.'),
                    settingRow('Flush reason', sttMetrics?.last_flush_reason || 'unknown', 'Why the stream flushed: pause, max buffer, manual flush, or unknown.'),
                    settingRow('Silence skipped', percent(sttMetrics?.silence_skipped_percent), 'High values mean VAD is saving backend work.'),
                  ]}
                />
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
                    {APP_CONFIG.name} v1.0.0
                  </h3>
                  <p className="text-sm text-gray-600">
                    {APP_CONFIG.description}
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
                    © 2026 {APP_CONFIG.name}. All rights reserved.
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

interface SettingRow {
  label: string;
  value: string;
  guide: string;
}

function ReadonlySection({
  title,
  note,
  rows,
}: {
  title: string;
  note?: string;
  rows: SettingRow[];
}) {
  return (
    <section className="space-y-2">
      <div>
        <h4 className="text-sm font-semibold text-gray-900">{title}</h4>
        {note && <p className="text-xs text-gray-600 mt-0.5">{note}</p>}
      </div>
      <div className="divide-y divide-gray-100 rounded border border-gray-200 bg-gray-50">
        {rows.map((row) => (
          <div key={`${title}-${row.label}`} className="grid gap-1 px-3 py-2 sm:grid-cols-[150px_1fr]">
            <div className="text-xs font-medium text-gray-700">{row.label}</div>
            <div>
              <div className="inline-flex rounded bg-white px-2 py-0.5 text-xs font-semibold text-gray-900 ring-1 ring-gray-200">
                {row.value}
              </div>
              <p className="mt-1 text-xs text-gray-600">{row.guide}</p>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function settingRow(label: string, value: string, guide: string): SettingRow {
  return { label, value, guide };
}

function mergeSttSettings(config: BackendConfigResponse | null): SafeSttSettings {
  return {
    sample_rate: config?.stt?.sample_rate ?? config?.audio?.sample_rate,
    channels: config?.stt?.channels ?? config?.audio?.channels,
    sample_width: config?.stt?.sample_width ?? config?.audio?.sample_width,
    model_size: config?.stt?.model_size ?? config?.model?.size,
    device: config?.stt?.device ?? config?.model?.device,
    compute_type: config?.stt?.compute_type ?? config?.model?.compute_type,
    language: config?.stt?.language ?? config?.model?.language,
    min_chunk_duration_seconds:
      config?.stt?.min_chunk_duration_seconds ?? config?.audio?.min_chunk_duration_seconds,
    max_chunk_duration_seconds:
      config?.stt?.max_chunk_duration_seconds ?? config?.audio?.max_chunk_duration_seconds,
    overlap_duration_seconds:
      config?.stt?.overlap_duration_seconds ?? config?.audio?.overlap_duration_seconds,
    ...config?.stt,
  };
}

function formatValue(value: string | number | boolean | null | undefined): string {
  if (value === null || value === undefined || value === '') return 'unknown';
  if (typeof value === 'number') return Number.isInteger(value) ? String(value) : value.toFixed(3).replace(/0+$/, '').replace(/\.$/, '');
  return String(value);
}

function hz(value: number | undefined): string {
  return value ? `${value} Hz` : 'unknown';
}

function channels(value: number | undefined): string {
  if (value === 1) return 'mono';
  if (value) return `${value} channels`;
  return 'unknown';
}

function sampleFormat(sampleWidth: number | undefined): string {
  if (sampleWidth === 2) return '16-bit PCM / int16';
  if (sampleWidth) return `${sampleWidth * 8}-bit PCM`;
  return 'unknown';
}

function seconds(value: number | undefined): string {
  return value === undefined ? 'unknown' : `${formatValue(value)} sec`;
}

function ms(value: number | undefined): string {
  return value === undefined ? 'unknown' : `${formatValue(value)} ms`;
}

function percent(value: number | undefined): string {
  return value === undefined ? 'unknown' : `${formatValue(value)}%`;
}

function booleanLabel(value: boolean | undefined): string {
  if (value === undefined) return 'unknown';
  return value ? 'enabled' : 'disabled';
}

function disabledLabel(value: boolean | undefined): string {
  return value ? 'enabled' : 'not enabled';
}

function formatTemperature(value: number[] | undefined): string {
  if (!value || value.length === 0) return 'unknown';
  return value.map((item) => formatValue(item)).join(', ');
}

function profileGuide(profile: string | undefined): string {
  switch (profile) {
    case 'low_latency':
      return 'Faster responses with a higher chance of less stable text.';
    case 'high_accuracy':
      return 'More context and stronger decoding with higher latency.';
    case 'pi_cpu':
      return 'Small model and CPU-friendly defaults for weak hardware.';
    case 'gpu':
      return 'CUDA and float16 defaults for machines with supported GPUs.';
    case 'balanced':
    case 'balanced_realtime':
      return 'Default realtime behavior and the best first choice.';
    default:
      return 'Profile details are unavailable until backend config loads.';
  }
}
