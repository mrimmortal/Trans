import { DEFAULTS } from "../config/defaults";

const HTML_KEY = "corestt.webclient.transcriptDraftHtml";

export function loadWsUrl(): string {
  try {
    const saved = localStorage.getItem(DEFAULTS.localStorageKeys.wsUrl);
    return saved ?? DEFAULTS.wsUrl;
  } catch {
    return DEFAULTS.wsUrl;
  }
}

export function saveWsUrl(url: string): void {
  try {
    localStorage.setItem(DEFAULTS.localStorageKeys.wsUrl, url);
  } catch {
    /* storage full or unavailable */
  }
}

export function loadTranscriptHtml(): string {
  try {
    const saved = localStorage.getItem(HTML_KEY);
    return saved ?? "";
  } catch {
    return "";
  }
}

export function saveTranscriptHtml(html: string): void {
  try {
    localStorage.setItem(HTML_KEY, html);
  } catch {
    /* storage full or unavailable */
  }
}

export function clearTranscriptDraft(): void {
  try {
    localStorage.removeItem(HTML_KEY);
  } catch {
    /* unavailable */
  }
}
