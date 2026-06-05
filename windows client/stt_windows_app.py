import asyncio
import json
import queue
import struct
import threading
import tkinter as tk

import sounddevice as sd
import websockets
import pyautogui
import sys
import os

from PIL import Image, ImageTk, ImageDraw


WS_URL = "ws://103.183.80.236:8000/ws"
SAMPLE_RATE = 16000
CHANNELS = 1
BLOCK_SIZE = 1024

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

LOGO_PATH = resource_path("dark spark logo.jpeg")


class STTWindowsApp:
    def __init__(self, root):
        self.root = root

        # ================= UI: Floating Circle Logo Window =================
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-transparentcolor", "#ff00ff")
        self.root.configure(bg="#ff00ff")

        self.logo_size = 96
        self.window_size = 112

        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()

        x = screen_w - 145
        y = screen_h - 185

        self.root.geometry(f"{self.window_size}x{self.window_size}+{x}+{y}")
        self.root.resizable(False, False)

        # Always keep app window on top
        self.root.attributes("-topmost", True)
        self.root.lift()
        self.root.focus_force()

        self.running = False
        self.audio_queue = queue.Queue()
        self.loop = None
        self.thread = None

        # Drag variables
        self.drag_x = 0
        self.drag_y = 0
        self.is_dragging = False

        # ================= UI: Logo Button =================
        self.logo_img = self.create_circle_logo(LOGO_PATH, self.logo_size)

        self.logo_btn = tk.Label(
            root,
            image=self.logo_img,
            bg="#ff00ff",
            cursor="hand2",
            bd=0,
            highlightthickness=0
        )
        self.logo_btn.place(
            x=(self.window_size - self.logo_size) // 2,
            y=(self.window_size - self.logo_size) // 2
        )

        self.logo_btn.bind("<ButtonPress-1>", self.start_drag)
        self.logo_btn.bind("<B1-Motion>", self.drag_window)
        self.logo_btn.bind("<ButtonRelease-1>", self.end_drag)

        # Double click logo to close app
        self.logo_btn.bind("<Double-Button-1>", lambda e: self.close_app())

        # ================= UI: Thinking / Transcription Box =================
        self.create_transcription_box()

        self.root.protocol("WM_DELETE_WINDOW", self.close_app)

        # Reapply always-on-top continuously
        self.keep_window_on_top()

    # ================= UI FUNCTIONS ONLY =================

    def create_circle_logo(self, image_path, size):
        img = Image.open(image_path).convert("RGBA")
        img = img.resize((size, size), Image.LANCZOS)

        mask = Image.new("L", (size, size), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, size, size), fill=255)

        output = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        output.paste(img, (0, 0), mask)

        return ImageTk.PhotoImage(output)

    def create_transcription_box(self):
        self.box_width = 430
        self.box_height = 180

        self.box = tk.Toplevel(self.root)
        self.box.overrideredirect(True)
        self.box.attributes("-topmost", True)
        self.box.configure(bg="#071426")

        self.update_box_position()

        self.header = tk.Label(
            self.box,
            text="🎙 Stopped",
            font=("Segoe UI", 12, "bold"),
            fg="#ff5c5c",
            bg="#071426",
            anchor="w"
        )
        self.header.pack(fill="x", padx=18, pady=(14, 6))

        self.line = tk.Frame(self.box, height=1, bg="#2b3d55")
        self.line.pack(fill="x", padx=16)

        self.title = tk.Label(
            self.box,
            text="Live Transcription",
            font=("Segoe UI", 11, "bold"),
            fg="#38bdf8",
            bg="#071426",
            anchor="w"
        )
        self.title.pack(fill="x", padx=18, pady=(12, 4))

        self.realtime = tk.Label(
            self.box,
            text="Click logo to start listening...",
            font=("Segoe UI", 14),
            fg="white",
            bg="#071426",
            wraplength=380,
            justify="left",
            anchor="nw"
        )
        self.realtime.pack(fill="both", expand=True, padx=18, pady=(4, 16))

        self.status = self.header

        self.box.withdraw()

    def update_box_position(self):
        self.root.update_idletasks()

        root_x = self.root.winfo_x()
        root_y = self.root.winfo_y()

        box_x = root_x - self.box_width + 95
        box_y = root_y - self.box_height - 12

        self.box.geometry(
            f"{self.box_width}x{self.box_height}+{box_x}+{box_y}"
        )

    def start_drag(self, event):
        self.drag_x = event.x
        self.drag_y = event.y
        self.is_dragging = False

    def drag_window(self, event):
        self.is_dragging = True

        x = self.root.winfo_pointerx() - self.drag_x
        y = self.root.winfo_pointery() - self.drag_y

        self.root.geometry(f"+{x}+{y}")
        self.update_box_position()

    def end_drag(self, event):
        if not self.is_dragging:
            self.toggle()

    # ================= YOUR EXISTING LOGIC =================

    def keep_window_on_top(self):
        self.root.attributes("-topmost", True)
        self.box.attributes("-topmost", True)
        self.root.after(1000, self.keep_window_on_top)

    def set_status(self, text):
        self.root.after(
            0,
            lambda: self.status.config(text=f"🎙 {text}")
        )

    def set_realtime(self, text):
        display_text = text if text else "Listening..."
        self.root.after(
            0,
            lambda: self.realtime.config(text=display_text)
        )

    def build_packet(self, audio_bytes):
        metadata = json.dumps({"sampleRate": SAMPLE_RATE}).encode("utf-8")
        header = struct.pack("<I", len(metadata))
        return header + metadata + audio_bytes

    def audio_callback(self, indata, frames, time_info, status):
        if self.running:
            self.audio_queue.put(indata.tobytes())

    def toggle(self):
        if self.running:
            self.stop_service()
        else:
            self.start_service()

    def start_service(self):
        self.running = True

        self.box.deiconify()
        self.update_box_position()

        self.root.attributes("-alpha", 0.82)
        self.set_status("Connecting...")
        self.set_realtime("Listening...")

        self.thread = threading.Thread(target=self.run_async_loop, daemon=True)
        self.thread.start()

    def stop_service(self):
        self.running = False

        self.root.attributes("-alpha", 1.0)
        self.set_status("Stopped")
        self.set_realtime("Click logo to start listening...")

        self.root.after(700, self.box.withdraw)

        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                break

    def run_async_loop(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        try:
            self.loop.run_until_complete(self.websocket_main())
        except Exception as e:
            self.set_status(f"Error: {e}")
            self.running = False
            self.root.after(
                0,
                lambda: self.root.attributes("-alpha", 1.0)
            )
        finally:
            self.loop.close()

    async def sender(self, websocket):
        while self.running:
            audio_bytes = await asyncio.to_thread(self.audio_queue.get)

            if not self.running:
                break

            packet = self.build_packet(audio_bytes)
            await websocket.send(packet)

    async def receiver(self, websocket):
        while self.running:
            message = await websocket.recv()
            data = json.loads(message)

            msg_type = data.get("type")
            text = data.get("text", "")

            if msg_type == "status":
                self.set_status(text)

            elif msg_type == "realtime":
                self.set_realtime(text)

            elif msg_type == "final":
                self.set_realtime("")
                if text.strip():
                    pyautogui.write(text.strip() + " ", interval=0.01)

            elif msg_type == "error":
                self.set_status(text)

    async def websocket_main(self):
        async with websockets.connect(WS_URL, max_size=None) as websocket:
            self.set_status("Connected. Listening...")

            with sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=CHANNELS,
                dtype="int16",
                blocksize=BLOCK_SIZE,
                callback=self.audio_callback,
            ):
                await asyncio.gather(
                    self.sender(websocket),
                    self.receiver(websocket)
                )

    def close_app(self):
        self.running = False

        try:
            self.box.destroy()
        except Exception:
            pass

        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = STTWindowsApp(root)
    root.mainloop()