"""
assistant/action_router.py — maps parsed intents to action handlers.

Action modules are imported lazily (on first use) so startup time and
memory are not bloated by unused dependencies.
"""
import logging

logger = logging.getLogger(__name__)


class ActionRouter:
    """Routes an intent dict to the appropriate action module."""

    def __init__(self, config: dict) -> None:
        self.config = config
        self._provider = self._load_provider(config)

    # ── Provider loading ───────────────────────────────────────────────────────

    @staticmethod
    def _load_provider(config: dict):
        name = config.get("smart_home", {}).get("provider", "none").lower()
        if name == "home_assistant":
            from providers.home_assistant_provider import HomeAssistantProvider
            return HomeAssistantProvider(config)
        # Default: log-only no-op
        from providers.base_provider import NoOpProvider
        return NoOpProvider()

    # ── Routing ────────────────────────────────────────────────────────────────

    def execute(self, intent: dict) -> None:
        kind = intent.get("intent")
        try:
            if kind == "search":
                from actions.web_search import execute
                execute(intent)

            elif kind == "open_app":
                from actions.open_app import execute
                execute(intent, self.config)

            elif kind == "device_control":
                from actions.smart_home import execute
                execute(intent, self._provider)

            else:
                logger.warning("Unknown intent kind: %r", kind)

        except Exception:
            logger.exception("Error executing intent: %s", intent)
