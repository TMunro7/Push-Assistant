"""
actions/smart_home.py — delegate device control to the active provider.
"""
import logging

logger = logging.getLogger(__name__)


def execute(intent: dict, provider) -> None:
    """
    Call provider.turn_on / turn_off based on the intent.

    Expected intent keys
    --------------------
    device : str        — spoken device name, e.g. "desk lamp"
    action : "on"|"off" — desired state
    """
    device: str = intent.get("device", "").strip()
    action: str = intent.get("action", "").lower()

    if not device:
        logger.warning("device_control intent is missing 'device' — skipping")
        return

    if action == "on":
        provider.turn_on(device)
    elif action == "off":
        provider.turn_off(device)
    else:
        logger.warning("Unknown device action: %r (expected 'on' or 'off')", action)
