import type {
  ServerMessage,
  ServerMessageHandler,
  ClientCommandType,
} from "../types/websocket-contract";

export interface WebSocketClientCallbacks {
  onOpen?: () => void;
  onClose?: () => void;
  onError?: (event: Event) => void;
  onMessage?: ServerMessageHandler;
}

export class WebSocketClient {
  private socket: WebSocket | null = null;
  private callbacks: WebSocketClientCallbacks = {};
  private _url = "";

  get url(): string {
    return this._url;
  }

  get isOpen(): boolean {
    return this.socket?.readyState === WebSocket.OPEN;
  }

  get isConnecting(): boolean {
    return this.socket?.readyState === WebSocket.CONNECTING;
  }

  connect(url: string, callbacks: WebSocketClientCallbacks): void {
    this.disconnect();
    this._url = url;
    this.callbacks = callbacks;

    try {
      const socket = new WebSocket(url);
      socket.binaryType = "arraybuffer";
      this.socket = socket;

      socket.onopen = () => {
        this.callbacks.onOpen?.();
      };

      socket.onclose = () => {
        this.callbacks.onClose?.();
      };

      socket.onerror = (event: Event) => {
        this.callbacks.onError?.(event);
      };

      socket.onmessage = (event: MessageEvent) => {
        if (typeof event.data === "string") {
          try {
            const message = JSON.parse(event.data) as ServerMessage;
            this.callbacks.onMessage?.(message);
          } catch {
            this.callbacks.onMessage?.({
              type: "error",
              message: "Failed to parse server message",
            });
          }
        }
      };
    } catch (err) {
      this.callbacks.onError?.(new Event("connection_failed"));
      this.socket = null;
    }
  }

  disconnect(): void {
    if (this.socket) {
      this.socket.onopen = null;
      this.socket.onclose = null;
      this.socket.onerror = null;
      this.socket.onmessage = null;
      if (
        this.socket.readyState === WebSocket.OPEN ||
        this.socket.readyState === WebSocket.CONNECTING
      ) {
        this.socket.close();
      }
      this.socket = null;
    }
    this.callbacks = {};
  }

  sendCommand(type: ClientCommandType): void {
    if (!this.isOpen) return;
    this.socket!.send(JSON.stringify({ type }));
  }

  sendAudioPacket(packet: ArrayBuffer): void {
    if (!this.isOpen) return;
    this.socket!.send(packet);
  }
}
