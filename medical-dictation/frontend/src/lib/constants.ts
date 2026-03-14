// ✅ FIX: Changed /ws/dictate → /ws/audio to match backend endpoint
// export const WS_URL = "ws://localhost:8000/ws/audio";
// export const API_URL = "http://localhost:8000";
// export const AUDIO_SAMPLE_RATE = 16000;
// export const AUDIO_CHUNK_INTERVAL = 250;
// export const BROWSER_SAMPLE_RATE = 44100;
// export const AUTO_SAVE_INTERVAL = 30000;
// export const MAX_SESSIONS = 50;
// export const TOAST_DURATION = 3000;


// use following code when the backend port is forworded

export const WS_URL = "wss://d5vvj07d-8000.inc1.devtunnels.ms/ws/audio";
export const API_URL = "https://d5vvj07d-8000.inc1.devtunnels.ms";

export const AUDIO_SAMPLE_RATE = 16000;
export const AUDIO_CHUNK_INTERVAL = 250;
export const BROWSER_SAMPLE_RATE = 44100;
export const AUTO_SAVE_INTERVAL = 30000;
export const MAX_SESSIONS = 50;
export const TOAST_DURATION = 3000;