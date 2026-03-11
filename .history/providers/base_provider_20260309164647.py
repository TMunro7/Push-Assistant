"""
providers/base_provider.py — abstract SmartHomeProvider interface.

Every provider must implement turn_on() and turn_off().
NoOpProvider is the safe default when no provider is configured.
"""
import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class SmartHomeProvider(ABC):
    """
    Interface that all smart home providers must implement.

    To add a new provider
    ---------------------
    1. Create providers/myprovider_provider.py
    2. Subclass SmartHomeProvider and implement turn_on / turn_off
    3. Add 'myprovider' handling in assistant/action_router.py _load_provider()
    4. Set smart_home.provider: myprovider in config.yaml
    """

    @abstractmethod
    def turn_on(self, device: str) -> None:
        """Turn on the named device."""

    @abstractmethod
    def turn_off(self, device: str) -> None:
        """Turn off the named device."""


class NoOpProvider(SmartHomeProvider):
    """
    Fallback — logs what it would do instead of calling any real API.
    Used when smart_home.provider is 'none' or unrecognised.
    """

    def turn_on(self, device: str) -> None:
        logger.info(
            "[NoOp] Would turn ON %r — set smart_home.provider in config.yaml",
            device,
        )

    def turn_off(self, device: str) -> None:
        logger.info(
            "[NoOp] Would turn OFF %r — set smart_home.provider in config.yaml",
            device,
        )
