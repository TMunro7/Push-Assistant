"""
actions/open_app.py — open an application or website.

Resolution order
----------------
1. Target matches a key in config['apps']  → use configured value
   a. Value is a URL  → open in browser
   b. Value is a name / path  → subprocess via shell (trusts config)
2. Target looks like a URL on its own  → open in browser
3. Unknown target  → attempt Windows Start-menu launch via cmd /c start
"""
import re
import subprocess
import webbrowser
import logging

logger = logging.getLogger(__name__)

# Matches bare domain-like strings: youtube.com, reddit.com, etc.
_URL_RE = re.compile(
    r"^(?:https?://)?(?:[a-z0-9-]+\.)+(?:com|org|net|io|gov|edu|co|uk|app|dev|tech|ai)"
    r"(?:/.*)?$",
    re.IGNORECASE,
)


def execute(intent: dict, config: dict) -> None:
    """
    Open an application or website named by intent['target'].

    Expected intent keys
    --------------------
    target : str  — spoken name, e.g. "discord", "youtube", "youtube.com"
    """
    target: str = intent.get("target", "").strip()
    if not target:
        logger.warning("open_app intent has an empty target — skipping")
        return

    apps: dict = config.get("apps", {})
    mapped = apps.get(target.lower())

    # ── 1. Config-mapped entry ─────────────────────────────────────────────────
    if mapped is not None:
        if mapped.startswith("http://") or mapped.startswith("https://"):
            logger.info("Opening URL (config): %s", mapped)
            webbrowser.open(mapped)
        else:
            logger.info("Launching app (config): %r", mapped)
            subprocess.Popen(mapped, shell=True)
        return

    # ── 2. Bare URL ────────────────────────────────────────────────────────────
    if _URL_RE.match(target):
        url = target if target.startswith("http") else "https://" + target
        logger.info("Opening URL: %s", url)
        webbrowser.open(url)
        return

    # ── 3. Unknown — try Windows Start-menu search ─────────────────────────────
    # Using a list avoids shell injection; cmd /c start searches Start Menu / PATH.
    logger.info("Attempting Windows start: %r", target)
    subprocess.Popen(["cmd", "/c", "start", "", target])
