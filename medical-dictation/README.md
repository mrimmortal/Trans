# Medical Voice Dictation Application

A real-time medical voice dictation web application similar to Augntio.ai, enabling doctors and healthcare professionals to transcribe clinical notes using voice with medical-specific formatting and commands.

## Features

- **Real-time Voice Transcription**: Stream audio directly to the backend via WebSocket for instant transcription
- **Medical Formatting**: Automatic formatting of medical abbreviations, vital signs, and clinical terminology
- **Voice Commands**: Control the editor with voice commands (e.g., "bold", "new line", "undo")
- **Medical Templates**: Pre-built templates for common note types (Progress Notes, Encounter Notes, etc.)
- **Macro System**: Create custom text shortcuts for frequently used phrases
- **Audio Visualization**: Real-time audio level monitoring while recording
- **Multi-Format Export**: Export notes as Text, HTML, and PDF
- **Session History**: Track and manage past dictations
- **Customizable Settings**: Model size selection, auto-formatting, auto-save intervals

## Architecture

### Backend (Python FastAPI)
- **Framework**: FastAPI 0.104.1
- **Speech Recognition**: Faster-Whisper 1.0.1 with multiple model sizes (tiny, base, small, medium)
- **Real-time Communication**: WebSockets for audio streaming
- **Server**: Uvicorn
- **Processing**: Medical text formatting, voice command recognition

### Frontend (Next.js 14 + React 18)
- **Framework**: Next.js 14 with App Router
- **Editor**: TipTap (headless rich text editor)
- **Styling**: Tailwind CSS 3.4
- **Components**: React 18 with TypeScript
- **Icons**: Lucide React
- **Communication**: WebSocket client

## Project Structure

```
medical-dictation/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI app configuration
│   │   ├── audio_config.py         # Audio & model configuration
│   │   ├── services/
│   │   │   ├── transcription_engine.py
│   │   │   ├── medical_formatter.py
│   │   │   └── command_processor.py
│   │   ├── websocket/
│   │   │   └── audio_handler.py    # WebSocket streaming handler
│   │   └── models/
│   │       └── schemas.py          # Pydantic models
│   ├── requirements.txt
│   ├── .env
│   └── run.py                      # Entry point
│
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx          # Root layout
│   │   │   ├── page.tsx            # Main page
│   │   │   └── globals.css
│   │   ├── components/
│   │   │   ├── Editor/             # TipTap editor components
│   │   │   ├── Recorder/           # Audio recording UI
│   │   │   ├── Sidebar/            # Macros & history
│   │   │   ├── Header/             # Top navigation
│   │   │   ├── Settings/           # Settings modal
│   │   │   └── ui/                 # Reusable UI components
│   │   ├── hooks/                  # Custom React hooks
│   │   ├── lib/                    # Utilities & constants
│   │   └── types/                  # TypeScript definitions
│   ├── package.json
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   └── next.config.js
│
└── README.md
```

## Setup & Installation

### Prerequisites
- Python 3.11+
- Node.js 18+
- pnpm (or npm/yarn)
- macOS, Linux, or Windows

### Backend Setup

1. **Navigate to backend directory**:
```bash
cd medical-dictation/backend
```

2. **Create Python virtual environment**:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install Python dependencies**:
```bash
pip install -r requirements.txt
```

4. **Verify backend setup**:
```bash
python run.py
```

The API should start on `http://localhost:8000`
- Interactive API docs: `http://localhost:8000/docs`
- WebSocket endpoint: `ws://localhost:8000/ws/dictate`
- Health check: `http://localhost:8000/health`

### Frontend Setup

1. **Navigate to frontend directory**:
```bash
cd medical-dictation/frontend
```

2. **Install dependencies with pnpm**:
```bash
pnpm install
```

3. **Start development server**:
```bash
pnpm dev
```

The frontend will be available at `http://localhost:3000`

### Verify Both Services

**Terminal 1 - Backend**:
```bash
cd backend
source venv/bin/activate
python run.py
# Should show: 🚀 Starting Medical Dictation API
#             📍 Server: http://0.0.0.0:8000
#             📚 Docs: http://0.0.0.0:8000/docs
#             🔌 WebSocket: ws://0.0.0.0:8000/ws/dictate
```

**Terminal 2 - Frontend**:
```bash
cd frontend
pnpm dev
# Should show: ▲ Next.js 14.1.0
#             - Local: http://localhost:3000
```

**Terminal 3 - Test services**:
```bash
# Test backend health
curl http://localhost:8000/health

# Open frontend in browser
open http://localhost:3000
```

## Available Commands

### Backend
```bash
# Start development server with auto-reload
python run.py

# View API documentation
open http://localhost:8000/docs
```

### Frontend
```bash
# Start development server
pnpm dev

# Build for production
pnpm build

# Start production server
pnpm start

# Run type checking
pnpm tsc --noEmit

# Format code
pnpm prettier --write .
```

## Environment Configuration

### Backend (.env)
```
MODEL_SIZE=base.en              # Options: tiny.en, base.en, small.en, medium.en
DEVICE=cpu                      # Options: cpu, cuda, mps
COMPUTE_TYPE=int8              # Options: float32, float16, int8
HOST=0.0.0.0
PORT=8000
```

### Frontend (next.config.js)
```javascript
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
```

## Usage

1. **Start Recording**: Click the microphone button or press Space
2. **Speak Naturally**: The application streams audio to the backend in real-time
3. **View Transcription**: Text appears in the editor as it's transcribed
4. **Use Voice Commands**: Say "bold" to make text bold, "new line" for paragraph breaks, etc.
5. **Apply Templates**: Click Templates to insert pre-built medical note structures
6. **Create Macros**: Set up shortcuts like ":pt" to expand to full patient introduction
7. **Export**: Download your note as Text, HTML, or PDF

## Technology Stack

### Backend
- **FastAPI** (0.104.1): Modern async web framework
- **Faster-Whisper** (1.0.1): Optimized speech-to-text with multiple model sizes
- **WebSockets** (12.0): Real-time bidirectional communication
- **Uvicorn** (0.24.0): ASGI server
- **Python-dotenv** (1.0.0): Environment variable management
- **Pydantic** (2.5.2): Data validation

### Frontend
- **Next.js** (14.1.0): React framework with App Router
- **React** (18.2.0): UI library
- **TipTap** (2.1.0): Headless rich text editor
- **Tailwind CSS** (3.4.0): Utility-first CSS
- **TypeScript** (5.3.0): Type safety
- **Lucide React** (0.300.0): Icon library

## Implementation Notes

### TODO Items
The project includes placeholder implementations for the following:

**Backend**:
- [ ] Streaming transcription with Faster-Whisper
- [ ] Medical text formatter with terminology database
- [ ] Voice command pattern matching and execution
- [ ] Audio buffer management for streaming
- [ ] Error handling and logging

**Frontend**:
- [ ] WebSocket connection and message handling
- [ ] Audio recording and level monitoring
- [ ] Transcription result integration
- [ ] Voice command processing
- [ ] PDF export functionality
- [ ] Session persistence to local storage/backend

### Audio Pipeline

1. **Frontend**: Captures microphone audio at 16kHz (mono), chunks into 4KB packets
2. **WebSocket**: Streams audio packets to backend
3. **Backend**: Buffers audio, processes with Faster-Whisper
4. **Transcription**: Returns text segments with timing information
5. **Formatting**: Applies medical formatting rules
6. **Command Processing**: Detects and executes voice commands
7. **Response**: Sends formatted text back to frontend

## Performance Considerations

- **Model Selection**: Use `tiny.en` for real-time performance (faster), `base.en` for balanced accuracy
- **Compute Type**: `int8` reduces memory usage, `float32` improves accuracy
- **Device**: Use `cuda` for GPU acceleration if available, `cpu` for compatibility
- **Chunking**: Process in-buffer (4KB chunks) to balance latency and accuracy

## Future Enhancements

- [ ] Speaker diarization (multiple speakers)
- [ ] Real-time medical terminology database
- [ ] Custom model fine-tuning for specialty-specific domains
- [ ] Batch file transcription
- [ ] Integration with EHR systems
- [ ] Cloud deployment (AWS, GCP, Azure)
- [ ] Multi-user collaboration
- [ ] Audio quality enhancement
- [ ] Integration with speech understanding models for context awareness
- [ ] Automated clinical coding suggestions

## Troubleshooting

### Backend fails to start
- Ensure Python 3.11+ is installed: `python --version`
- Check if port 8000 is already in use: `lsof -i :8000`
- Verify all dependencies: `pip list | grep -E "fastapi|whisper|uvicorn"`

### Frontend won't connect
- Check API URL in `next.config.js`
- Verify backend is running: `curl http://localhost:8000/health`
- Check browser console for WebSocket errors

### Audio recording issues
- Allow microphone permission when prompted
- Check browser console for permissions errors
- Test microphone with system settings first

### Transcription is slow/inaccurate
- Switch to faster-whisper with `tiny.en` model
- Reduce `int8` compute type if using `float32`
- Ensure quiet recording environment
- Check backend logs for processing time

## License

This project is provided as-is for educational and development purposes.

## Support

For issues and questions, please refer to the component TODO comments and implementation guides within the codebase.

---

**Happy Dictating! 🎙️**


┌──────────────────────────────────────────────────────────────────┐
│                     APPLICATION FLOW                              │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌────────────────┐                                              │
│  │  Application   │                                              │
│  │    Startup     │                                              │
│  └───────┬────────┘                                              │
│          │                                                        │
│          ▼                                                        │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ 1. init_database()                                          │  │
│  │    • Create templates table if not exists                   │  │
│  │    • Create indexes                                         │  │
│  │    • Seed default templates (SOAP, HPI, Vitals, etc.)       │  │
│  └───────────────────────────┬────────────────────────────────┘  │
│                              │                                    │
│                              ▼                                    │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ 2. TemplateManager.__init__()                               │  │
│  │    • Load templates from SQLite                             │  │
│  │    • Build regex patterns for each template                 │  │
│  │    • Register with CommandProcessor                         │  │
│  └───────────────────────────┬────────────────────────────────┘  │
│                              │                                    │
│                              ▼                                    │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ 3. API Ready                                                │  │
│  │    • POST /api/templates/ - Create template                 │  │
│  │    • GET  /api/templates/ - List templates                  │  │
│  │    • PUT  /api/templates/{name} - Update                    │  │
│  │    • DELETE /api/templates/{name} - Delete                  │  │
│  │    • POST /api/templates/test - Test processing             │  │
│  └───────────────────────────┬────────────────────────────────┘  │
│                              │                                    │
│                              ▼                                    │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ 4. Voice Dictation Flow                                     │  │
│  │                                                             │  │
│  │    🎤 "Patient reports pain period insert vitals"           │  │
│  │                         │                                   │  │
│  │                         ▼                                   │  │
│  │    ┌──────────────────────────────────────────────┐        │  │
│  │    │        CommandProcessor.process()             │        │  │
│  │    │  • Match "period" → "."                       │        │  │
│  │    │  • Match "insert vitals" → Vitals template    │        │  │
│  │    └──────────────────────────────────────────────┘        │  │
│  │                         │                                   │  │
│  │                         ▼                                   │  │
│  │    📝 Output:                                               │  │
│  │    "Patient reports pain.                                   │  │
│  │                                                             │  │
│  │    Vital Signs:                                             │  │
│  │    • BP: ___/___ mmHg                                       │  │
│  │    • HR: ___ bpm                                            │  │
│  │    ..."                                                     │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘