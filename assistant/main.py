"""
assistant/main.py — application bootstrap and system tray.
"""
import sys
import threading
import logging
from pathlib import Path

import yaml
import pystray
from PIL import Image, ImageDraw

from assistant.hotkey_listener import HotkeyListener
from assistant.audio_recorder import AudioRecorder
from assistant.speech_to_text import SpeechToText
from assistant.command_parser import CommandParser
from assistant.action_router import ActionRouter

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# When frozen by PyInstaller, resolve config relative to the .exe location.
# In dev mode, resolve relative to the project root as before.
if getattr(sys, "frozen", False):
    _BASE_DIR = Path(sys.executable).parent
else:
    _BASE_DIR = Path(__file__).parent.parent

_CONFIG_PATH = _BASE_DIR / "config" / "config.yaml"


# ── Config ─────────────────────────────────────────────────────────────────────
def _load_config() -> dict:
    with open(_CONFIG_PATH, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


# ── Tray icon ──────────────────────────────────────────────────────────────────
def _make_icon(recording: bool = False) -> Image.Image:
    """Render a 64×64 microphone icon.  Green = idle, Red = recording."""
    color = (220, 60, 60) if recording else (60, 200, 100)
    bg = (28, 28, 28)
    img = Image.new("RGB", (64, 64), bg)
    d = ImageDraw.Draw(img)
    # Mic capsule
    d.rounded_rectangle([24, 8, 40, 34], radius=8, fill=color)
    # Stem
    d.rectangle([29, 34, 35, 48], fill=color)
    # Base — horizontal bar + vertical drop
    d.line([20, 48, 44, 48], fill=color, width=3)
    d.line([32, 48, 32, 56], fill=color, width=3)
    return img


# ── Application ────────────────────────────────────────────────────────────────
class PushAssistantApp:
    """
    Owns all components and wires them together.

    Thread model
    ------------
    Main thread  : pystray (system tray event loop)
    Listener     : pynput daemon thread (key events)
    Processing   : one-shot daemon thread per command (transcribe → parse → act)
    """

    def __init__(self) -> None:
        logger.info("Loading configuration…")
        self.config = _load_config()

        logger.info("Initialising audio recorder…")
        self.recorder = AudioRecorder(self.config)

        logger.info("Loading Whisper model (may download ~75 MB on first run)…")
        self.stt = SpeechToText(self.config)

        self.parser = CommandParser()
        self.router = ActionRouter(self.config)

        self._recording: bool = False
        self._processing: bool = False
        self.tray: pystray.Icon | None = None

        hotkey = self.config.get("hotkey", "scroll_lock")
        logger.info(f"Push-to-talk hotkey: [{hotkey}]")
        self.listener = HotkeyListener(
            hotkey=hotkey,
            on_press=self._on_press,
            on_release=self._on_release,
        )

    # ── Hotkey callbacks (called from pynput thread) ───────────────────────────

    def _on_press(self) -> None:
        if self._processing:
            logger.info("Still processing previous command — ignoring key press")
            return
        if self._recording:
            return
        self._recording = True
        self.recorder.start()
        if self.tray is not None:
            self.tray.icon = _make_icon(recording=True)
        logger.info("● Recording…")

    def _on_release(self) -> None:
        if not self._recording:
            return
        self._recording = False
        audio = self.recorder.stop()
        if self.tray is not None:
            self.tray.icon = _make_icon(recording=False)
        logger.info("■ Recording stopped — processing")
        self._processing = True
        threading.Thread(
            target=self._process, args=(audio,), daemon=True, name="processor"
        ).start()

    # ── Processing pipeline (runs in daemon thread) ────────────────────────────

    def _process(self, audio) -> None:
        try:
            text = self.stt.transcribe(audio)
            if not text:
                logger.info("No speech detected")
                return
            logger.info(f"Transcribed : {text!r}")

            intent = self.parser.parse(text)
            if intent is None:
                logger.warning(f"No intent matched for: {text!r}")
                return
            logger.info(f"Intent      : {intent}")

            self.router.execute(intent)
        except Exception:
            logger.exception("Unhandled error in processing pipeline")
        finally:
            self._processing = False

    # ── Tray ───────────────────────────────────────────────────────────────────

    def run(self) -> None:
        self.listener.start()
        hotkey = self.config.get("hotkey", "scroll_lock")
        logger.info(f"Push Assistant ready — hold [{hotkey}] to speak")

        menu = pystray.Menu(
            pystray.MenuItem("Push Assistant", None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit", self._quit),
        )
        self.tray = pystray.Icon(
            name="PushAssistant",
            icon=_make_icon(recording=False),
            title=f"Push Assistant — hold [{hotkey}] to speak",
            menu=menu,
        )
        self.tray.run()  # blocks until quit is chosen

    def _quit(self, icon: pystray.Icon, _item) -> None:
        logger.info("Shutting down…")
        icon.stop()
        self.listener.stop()
        sys.exit(0)


# ── Entrypoint ─────────────────────────────────────────────────────────────────
def main() -> None:
    app = PushAssistantApp()
    app.run()
