"""
assistant/command_parser.py — regex-based intent extraction.

Rules are evaluated in order; the first match wins.
Add new patterns at the appropriate priority level to extend the parser.

Supported intents
-----------------
device_control  : {"intent": "device_control", "action": "on"|"off", "device": str}
search          : {"intent": "search", "engine": str, "query": str}
open_app        : {"intent": "open_app", "target": str}
"""
import re
import logging
from typing import Optional, Callable

logger = logging.getLogger(__name__)


# Each entry: (compiled_pattern, builder_callable)
# builder receives a re.Match object and returns an intent dict.
_RULES: list[tuple[re.Pattern, Callable]] = [

    # ── Device control ─────────────────────────────────────────────────────────

    # "turn|switch  on|off  [the|my]  <device>"
    (
        re.compile(
            r"^\s*(?:turn|switch)\s+(on|off)\s+(?:(?:the|my)\s+)?(.+?)\s*\.?\s*$",
            re.IGNORECASE,
        ),
        lambda m: {
            "intent": "device_control",
            "action": m.group(1).lower(),
            "device": m.group(2).strip(),
        },
    ),

    # "turn|switch  [the|my]  <device>  on|off"
    (
        re.compile(
            r"^\s*(?:turn|switch)\s+(?:(?:the|my)\s+)?(.+?)\s+(on|off)\s*\.?\s*$",
            re.IGNORECASE,
        ),
        lambda m: {
            "intent": "device_control",
            "action": m.group(2).lower(),
            "device": m.group(1).strip(),
        },
    ),

    # ── Web search ─────────────────────────────────────────────────────────────

    # "search|look up  <query>  on  <engine>"
    (
        re.compile(
            r"^\s*(?:search|look\s+up)\s+(?:for\s+)?(.+?)\s+on\s+"
            r"(google|bing|youtube|duckduckgo)\s*\.?\s*$",
            re.IGNORECASE,
        ),
        lambda m: {
            "intent": "search",
            "query": m.group(1).strip(),
            "engine": m.group(2).lower(),
        },
    ),

    # "search|look up  <engine>  for  <query>"  (e.g. "search google for cats")
    (
        re.compile(
            r"^\s*(?:search|look\s+up)\s+(google|bing|youtube|duckduckgo)\s+"
            r"(?:for\s+)?(.+?)\s*\.?\s*$",
            re.IGNORECASE,
        ),
        lambda m: {
            "intent": "search",
            "query": m.group(2).strip(),
            "engine": m.group(1).lower(),
        },
    ),

    # "search [for] <query>"  /  "google <query>"  /  "bing <query>"
    (
        re.compile(
            r"^\s*(?:search(?:\s+for)?|google|bing)\s+(.+?)\s*\.?\s*$",
            re.IGNORECASE,
        ),
        lambda m: {
            "intent": "search",
            "query": m.group(1).strip(),
            "engine": "google",
        },
    ),

    # "look up <query>"  /  "find <query>"
    (
        re.compile(
            r"^\s*(?:look\s+up|find)\s+(.+?)\s*\.?\s*$",
            re.IGNORECASE,
        ),
        lambda m: {
            "intent": "search",
            "query": m.group(1).strip(),
            "engine": "google",
        },
    ),

    # Question-style: "what is X", "how do I X", "why does X", …
    # The entire utterance becomes the search query.
    (
        re.compile(
            r"^\s*((?:what(?:'s| is)|who(?:'s| is)|how (?:do(?:es)?|to|can)|"
            r"why (?:is|are|does)|where (?:is|can)).+?)\s*\.?\s*$",
            re.IGNORECASE,
        ),
        lambda m: {
            "intent": "search",
            "query": m.group(1).strip(),
            "engine": "google",
        },
    ),

    # ── Open app / website ─────────────────────────────────────────────────────

    # "open|launch|start|run [up] <target>"
    (
        re.compile(
            r"^\s*(?:open(?:\s+up)?|launch|start|run)\s+(.+?)\s*\.?\s*$",
            re.IGNORECASE,
        ),
        lambda m: {
            "intent": "open_app",
            "target": m.group(1).strip(),
        },
    ),

    # "go to|navigate to|visit|show me <target>"
    (
        re.compile(
            r"^\s*(?:go\s+to|navigate\s+to|visit|show\s+me)\s+(.+?)\s*\.?\s*$",
            re.IGNORECASE,
        ),
        lambda m: {
            "intent": "open_app",
            "target": m.group(1).strip(),
        },
    ),
]


class CommandParser:
    """Stateless, thread-safe pattern-based command parser."""

    def parse(self, text: str) -> Optional[dict]:
        """
        Return the first matching intent dict, or None if nothing matches.
        All field values are already cleaned (stripped, lowercased where appropriate).
        """
        text = text.strip()
        if not text:
            return None

        for pattern, build in _RULES:
            m = pattern.match(text)
            if m:
                return build(m)

        logger.warning("No intent matched for: %r", text)
        return None
