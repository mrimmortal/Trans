export const DEFAULTS = {
  wsUrl: "ws://127.0.0.1:8020/ws/transcribe",
  clientPlatform: "web",
  clientProtocolVersion: "1.0",
  pingIntervalMs: 2500,
  targetChunkMs: 40,
  localStorageKeys: {
    wsUrl: "corestt.webclient.wsUrl",
  } as const,
} as const;
