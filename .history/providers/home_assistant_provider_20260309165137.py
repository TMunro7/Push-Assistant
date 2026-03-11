"""
providers/home_assistant_provider.py — Home Assistant REST API provider.

Minimal config (config.yaml)
-----------------------------
smart_home:
  provider: home_assistant
  home_assistant:
    url: http://homeassistant.local:8123      # or IP address
    token: YOUR_LONG_LIVED_ACCESS_TOKEN

devices:
  "desk lamp":    "light.desk_lamp"
  "bedroom lamp": "light.bedroom_lamp"
  "fan":          "switch.fan"

Getting a Long-Lived Access Token
----------------------------------
Home Assistant → Profile → Long-Lived Access Tokens → Create Token
"""
import logging
from typing import Optional

import requests

from providers.base_provider import SmartHomeProvider

logger = logging.getLogger(__name__)


class HomeAssistantProvider(SmartHomeProvider):
    """Calls the Home Assistant REST API to control lights and switches."""

    def __init__(self, config: dict) -> None:
        ha = config["smart_home"]["home_assistant"]
        self._base_url: str = ha["url"].rstrip("/")
        self._headers = {
            "Authorization": f"Bearer {ha['token']}",
            "Content-Type": "application/json",
        }
        # Build a case-insensitive device → entity_id lookup table
        self._device_map: dict[str, str] = {
            str(k).lower(): str(v)
            for k, v in config.get("devices", {}).items()
        }
        logger.info("Home Assistant provider ready: %s", self._base_url)

    # ── SmartHomeProvider interface ────────────────────────────────────────────

    def turn_on(self, device: str) -> None:
        entity_id = self._resolve(device)
        if entity_id:
            domain = entity_id.split(".")[0]
            self._call_service(domain, "turn_on", entity_id)

    def turn_off(self, device: str) -> None:
        entity_id = self._resolve(device)
        if entity_id:
            domain = entity_id.split(".")[0]
            self._call_service(domain, "turn_off", entity_id)

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _resolve(self, device: str) -> Optional[str]:
        entity_id = self._device_map.get(device.lower().strip())
        if not entity_id:
            logger.warning(
                "Device %r not found in devices map. "
                "Add it to config.yaml under 'devices:'.",
                device,
            )
        return entity_id

    def _call_service(self, domain: str, service: str, entity_id: str) -> None:
        url = f"{self._base_url}/api/services/{domain}/{service}"
        try:
            resp = requests.post(
                url,
                json={"entity_id": entity_id},
                headers=self._headers,
                timeout=5,
            )
            resp.raise_for_status()
            logger.info("HA: %s.%s(%s) → %s", domain, service, entity_id, resp.status_code)
        except requests.RequestException as exc:
            logger.error("Home Assistant API error: %s", exc)
