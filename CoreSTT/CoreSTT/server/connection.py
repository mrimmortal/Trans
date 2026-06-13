import asyncio
import json


class ConnectionManager:
    def __init__(self):
        self._connections = {}
        self._lock = asyncio.Lock()
        self._loop = None

    def bind_loop(self, loop):
        self._loop = loop

    async def connect(self, session_id, websocket):
        await websocket.accept()
        async with self._lock:
            self._connections[session_id] = websocket

    async def disconnect(self, session_id):
        async with self._lock:
            self._connections.pop(session_id, None)

    async def send(self, session_id, message):
        payload = json.dumps(message, separators=(",", ":"))
        async with self._lock:
            websocket = self._connections.get(session_id)

        if websocket is None:
            return False

        try:
            await websocket.send_text(payload)
            return True
        except Exception:
            async with self._lock:
                if self._connections.get(session_id) is websocket:
                    self._connections.pop(session_id, None)
            return False

    async def send_all(self, message):
        payload = json.dumps(message, separators=(",", ":"))
        async with self._lock:
            connections = list(self._connections.items())

        stale = []
        for session_id, websocket in connections:
            try:
                await websocket.send_text(payload)
            except Exception:
                stale.append((session_id, websocket))

        if stale:
            async with self._lock:
                for session_id, websocket in stale:
                    if self._connections.get(session_id) is websocket:
                        self._connections.pop(session_id, None)

    def publish_session(self, session_id, message):
        if self._loop is None:
            return
        asyncio.run_coroutine_threadsafe(self.send(session_id, message), self._loop)

    def publish_all(self, message):
        if self._loop is None:
            return
        asyncio.run_coroutine_threadsafe(self.send_all(message), self._loop)
