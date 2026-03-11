"""
assistant/hotkey_listener.py — global keyboard hook for push-to-talk.
"""
import logging
from typing import Callable

from pynput import keyboard

logger = logging.getLogger(__name__)


class HotkeyListener:
    """
    Installs a global keyboard listener that fires callbacks when a
    specific key is pressed and released anywhere on the system.

    Key parsing
    -----------
    Named key  : "scroll_lock", "f9", "right_ctrl", "caps_lock", …
    Single char: "z", "x", …  (matches lower-cased character)
    """

    def __init__(
        self,
        hotkey: str,
        on_press: Callable[[], None],
        on_release: Callable[[], None],
    ) -> None:
        self._hotkey = self._parse_key(hotkey)
        self._on_press_cb = on_press
        self._on_release_cb = on_release
        self._is_held = False

        self._listener = keyboard.Listener(
            on_press=self._handle_press,
            on_release=self._handle_release,
        )
        self._listener.daemon = True

    # ── Key parsing ────────────────────────────────────────────────────────────

    @staticmethod
    def _parse_key(key_str: str):
        """Return a pynput Key enum value or KeyCode for the given string."""
        # Try named special key first (e.g. "scroll_lock", "f9")
        try:
            return keyboard.Key[key_str.lower()]
        except KeyError:
            pass
        # Single character key (e.g. "z")
        if len(key_str) == 1:
            return keyboard.KeyCode.from_char(key_str.lower())
        raise ValueError(
            f"Unknown hotkey {key_str!r}. "
            "Use a Key name (e.g. 'scroll_lock', 'f9') or a single character."
        )

    # ── Listener callbacks (called from pynput thread) ─────────────────────────

    def _handle_press(self, key) -> None:
        if key == self._hotkey and not self._is_held:
            self._is_held = True
            try:
                self._on_press_cb()
            except Exception:
                logger.exception("Error in on_press callback")

    def _handle_release(self, key) -> None:
        if key == self._hotkey and self._is_held:
            self._is_held = False
            try:
                self._on_release_cb()
            except Exception:
                logger.exception("Error in on_release callback")

    # ── Lifecycle ──────────────────────────────────────────────────────────────

    def start(self) -> None:
        self._listener.start()

    def stop(self) -> None:
        self._listener.stop()
