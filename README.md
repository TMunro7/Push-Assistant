# Push Assistant

A lightweight Windows push-to-talk voice assistant that runs silently
in the system tray.  Hold a key → speak → release → command executes.
No wake word.  No continuous listening.  Near-zero CPU when idle.

---

## Technology Stack

| Layer | Library | Why |
|---|---|---|
| Global hotkey | **pynput** | Event-driven OS hook — zero polling cost |
| Audio capture | **sounddevice** | Thin PortAudio wrapper; stream only open while key held |
| Speech-to-text | **faster-whisper** (tiny) | Local, ~75 MB, int8-quantised, ~1-2 s on CPU |
| System tray | **pystray + Pillow** | Minimal; no Electron, no heavy GUI |
| Config | **PyYAML** | Human-readable, easy to edit |
| Smart home | **requests** (+ HA REST) | Single HTTP call, no persistent connection |

### Why faster-whisper over cloud STT?
- **Private** — audio never leaves the machine
- **No API key or billing** — works offline
- **Fast enough** — tiny model transcribes a 3-second command in ~1-2 s on a modern CPU
- **Low idle cost** — model sits in RAM; CPU usage returns to 0 % between commands

---

## Project Structure

```
PushAssistant/
├── run.py                      ← entry point
├── run.bat                     ← double-click launcher (Windows)
├── requirements.txt
│
├── config/
│   └── config.yaml             ← all user settings
│
├── assistant/                  ← core pipeline
│   ├── main.py                 ← app bootstrap + system tray
│   ├── hotkey_listener.py      ← global key press/release hook
│   ├── audio_recorder.py       ← microphone capture
│   ├── speech_to_text.py       ← faster-whisper wrapper
│   ├── command_parser.py       ← regex-based intent extraction
│   └── action_router.py        ← routes intents to action modules
│
├── actions/                    ← one file per action category
│   ├── web_search.py           ← open browser with search URL
│   ├── open_app.py             ← launch apps / open websites
│   └── smart_home.py           ← delegate to active provider
│
└── providers/                  ← smart home back-ends
    ├── base_provider.py        ← abstract interface + NoOp default
    └── home_assistant_provider.py
```

---

## Setup

### Prerequisites

- **Python 3.10+** (`python --version`)
- **Windows 10 / 11**
- A working microphone

### 1 — Create a virtual environment

```bat
cd C:\Users\SESA667337\dev\PushAssistant
python -m venv .venv
.venv\Scripts\activate
```

### 2 — Install dependencies

```bat
pip install -r requirements.txt
```

> **First-run note:** `faster-whisper` downloads the Whisper *tiny* model
> (~75 MB) the first time it loads.  Subsequent starts are instant.
> The model is cached in `%USERPROFILE%\.cache\huggingface\hub\`.

### 3 — Configure

Open `config\config.yaml` and adjust:

```yaml
hotkey: "scroll_lock"     # key to hold while speaking

speech_to_text:
  model: "base"           # tiny / base / small
  language: "en"

apps:
  discord: "discord"      # add any app or website here
  youtube: "https://youtube.com"

smart_home:
  provider: "none"        # change to "home_assistant" when ready
```

---

## Running

```bat
python run.py
```

Or double-click **`run.bat`**.

The app starts silently in the system tray (look for the green microphone
icon near the clock).  Right-click the icon → **Quit** to exit.

**Usage:**  hold `Scroll Lock` (default) → speak your command → release.

### Hide the console window

Once you are happy with the setup, run with:

```bat
pythonw run.py
```

or edit `run.bat` to use `pythonw` instead of `python`.

---

## Example Commands

| You say | What happens |
|---|---|
| `search google for how to reverse a linked list` | Opens Google search |
| `search youtube for lofi music` | Opens YouTube search |
| `open discord` | Launches Discord |
| `open youtube` | Opens youtube.com |
| `open reddit.com` | Opens reddit.com |
| `turn off the desk lamp` | Calls provider turn_off |
| `turn on bedroom light` | Calls provider turn_on |
| `what is the capital of France` | Googles the question |

---

## Data Flow

```
Hold hotkey
    │
    ▼
AudioRecorder.start()   ← sounddevice InputStream opens
    │
Hold key while speaking…
    │
Release hotkey
    │
    ▼
AudioRecorder.stop()    ← returns float32 numpy array
    │
    ▼
SpeechToText.transcribe()
    │  "turn off desk lamp"
    ▼
CommandParser.parse()
    │  {intent: device_control, action: off, device: desk lamp}
    ▼
ActionRouter.execute()
    │
    ▼
SmartHomeProvider.turn_off("desk lamp")
```

---

## Resource Usage

| State | CPU | RAM |
|---|---|---|
| Idle (tray running) | ~0 % | ~150 MB (Whisper model loaded) |
| Recording (key held) | ~1–2 % | no change |
| Transcribing (~1-2 s) | 50–100 % briefly | no change |

All timing is event-driven — no polling, no wake word, no background audio.

---

## How to Add New Commands

### A — Add an app or website shortcut

Edit `config/config.yaml`:

```yaml
apps:
  slack: "slack"
  whatsapp: "C:\\Users\\YourName\\AppData\\Local\\WhatsApp\\WhatsApp.exe"
  hacker news: "https://news.ycombinator.com"
```

Say *"open slack"* or *"open hacker news"*.

### B — Add a smart home device

Edit `config/config.yaml` (Home Assistant entities):

```yaml
devices:
  "kitchen light":  "light.kitchen_ceiling"
  "tv":             "media_player.living_room_tv"
```

### C — Add a new intent type

1. **Add a regex rule** in `assistant/command_parser.py`:

```python
# Inside the _RULES list, before the catch-all open_app rules:
(
    re.compile(r"^\s*(?:set timer for|timer)\s+(\d+)\s+(second|minute|hour)s?\s*$", re.IGNORECASE),
    lambda m: {"intent": "timer", "amount": int(m.group(1)), "unit": m.group(2).lower()},
),
```

2. **Create an action file** `actions/timer.py`:

```python
def execute(intent: dict) -> None:
    # your logic here
    pass
```

3. **Register it** in `assistant/action_router.py`:

```python
elif kind == "timer":
    from actions.timer import execute
    execute(intent)
```

### D — Add a new smart home provider

1. Create `providers/myprovider_provider.py`:

```python
from providers.base_provider import SmartHomeProvider

class MyProvider(SmartHomeProvider):
    def __init__(self, config): ...
    def turn_on(self, device): ...
    def turn_off(self, device): ...
```

2. Register in `assistant/action_router.py` inside `_load_provider()`:

```python
if name == "myprovider":
    from providers.myprovider_provider import MyProvider
    return MyProvider(config)
```

3. Set `smart_home.provider: myprovider` in `config.yaml`.

---

## Packaging as a Windows Executable

```bat
pip install pyinstaller
pyinstaller --onefile --windowed --name PushAssistant --add-data ".venv\Lib\site-packages\faster_whisper\assets;faster_whisper\assets" run.py
xcopy /E /I config dist\config
```

| Flag | Purpose |
|---|---|
| `--onefile` | Single `.exe` |
| `--windowed` | No console window |
| `--name PushAssistant` | Output filename |

The `.exe` is created in `dist\`.

> **Model note:** PyInstaller does not bundle the Whisper model.
> The first run of the packaged `.exe` will still download it (~75 MB).
> To pre-bundle it, add the model cache directory with `--add-data`.

### Auto-start with Windows

1. Press `Win + R` → `shell:startup`
2. Drop a shortcut to `PushAssistant.exe` in the folder that opens

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| Hotkey not detected in some apps | Run as administrator (`runas /user:Administrator python run.py`) |
| `sounddevice` error on start | Check microphone permissions in Windows Settings → Privacy |
| Whisper says `int8` not supported | Change `compute_type: "float32"` in `config.yaml` |
| App won't open | Add an explicit mapping under `apps:` in `config.yaml` |
| No icon in tray | Right-click taskbar → Taskbar Settings → enable system tray icons |
