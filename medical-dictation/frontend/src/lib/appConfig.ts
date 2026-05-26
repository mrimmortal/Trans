export const APP_CONFIG = {
  name: 'Transcription Template',
  shortName: 'Transcribe',
  tagline: 'Vanilla Voice Transcription',
  description: 'A wrapper-ready voice transcription workspace.',
  dictatedSignature: '\n\n-- Dictated using Transcription Template\n',
  storageKeys: {
    macros: 'transcriptionTemplateMacros',
    sessions: 'transcriptionTemplateSessions',
    settings: 'transcriptionTemplateSettings',
    autoSave: 'transcriptionTemplateAutoSave',
  },
  features: {
    macros: true,
    sessions: true,
    backendTemplates: false,
  },
} as const;
