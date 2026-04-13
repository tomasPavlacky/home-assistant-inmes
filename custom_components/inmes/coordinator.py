"""Data update coordinator for INMES."""
from __future__ import annotations

import base64
import logging
from typing import Any

import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import API_BASE, API_V2, CONF_EMAIL, CONF_PASSWORD, DOMAIN, UPDATE_INTERVAL, USER_AGENT

_LOGGER = logging.getLogger(__name__)

TIMEOUT = aiohttp.ClientTimeout(total=30)

HEADERS_BASE = {
    "User-Agent": USER_AGENT,
    "Content-Type": "application/json",
}


class InmesCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Fetch all active meter readings for the configured account."""

    def __init__(self, hass: HomeAssistant, email: str, password: str) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )
        self._email = email
        self._password = password

    async def _async_update_data(self) -> dict[str, Any]:
        """Login and fetch meter data. Returns dict[meter_guid → meter_dict]."""
        session = async_get_clientsession(self.hass)
        try:
            session_token, bearer_token = await self._login(session)
            return await self._fetch_meters(session, session_token, bearer_token)
        except ConfigEntryAuthFailed:
            raise
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Network error communicating with INMES: {err}") from err
        except Exception as err:
            raise UpdateFailed(f"Unexpected error fetching INMES data: {err}") from err

    async def _login(self, session: aiohttp.ClientSession) -> tuple[str, str]:
        """Perform 2-step login. Returns (session_token, bearer_token)."""

        # Step 1: initialise session
        _LOGGER.debug("INMES: requesting session token from %s/session/new", API_BASE)
        async with session.post(
            f"{API_BASE}/session/new",
            json={
                "os": "Mac OS X",
                "platform": "Desktop",
                "browser": "Chrome",
                "version": "120",
                "resolution": "1920x1080",
            },
            headers=HEADERS_BASE,
            timeout=TIMEOUT,
        ) as resp:
            _LOGGER.debug("INMES: session/new response status=%s", resp.status)
            if resp.status != 200:
                raise UpdateFailed(f"Session init failed with HTTP {resp.status}")
            data = await resp.json(content_type=None)
            session_token: str = data["token"]
        _LOGGER.debug("INMES: got session token")

        # Step 2: login with Base64-encoded credentials
        auth = base64.b64encode(f"{self._email}:{self._password}".encode()).decode()
        _LOGGER.debug("INMES: posting login for %s", self._email)
        async with session.post(
            f"{API_V2}/login",
            json={"auth": auth},
            headers={**HEADERS_BASE, "X-Enw-Session": session_token},
            timeout=TIMEOUT,
        ) as resp:
            _LOGGER.debug("INMES: login response status=%s", resp.status)
            if resp.status in (401, 403):
                raise ConfigEntryAuthFailed("Invalid INMES credentials")
            if resp.status != 200:
                raise UpdateFailed(f"Login failed with HTTP {resp.status}")
            data = await resp.json(content_type=None)
        _LOGGER.debug("INMES: login success=%s", data.get("success"))

        if not data.get("success"):
            raise ConfigEntryAuthFailed(
                f"INMES login rejected: {data.get('message', 'unknown error')}"
            )

        bearer_token: str = data["token"]
        return session_token, bearer_token

    async def _fetch_meters(
        self,
        session: aiohttp.ClientSession,
        session_token: str,
        bearer_token: str,
    ) -> dict[str, Any]:
        """Discover client/building/unit hierarchy then fetch meter readings."""
        headers = {
            **HEADERS_BASE,
            "X-Enw-Session": session_token,
            "X-Enw-Auth": f"Bearer {bearer_token}",
        }

        # Clients
        client_guid = await self._get_first_guid(session, headers, "clients", "clients")

        # Buildings
        building_guid = await self._get_first_guid(
            session, headers, f"buildings/{client_guid}", "buildings"
        )

        # Units
        unit_data = await self._get(session, headers, f"units/{client_guid}/{building_guid}")
        units = unit_data.get("units", [])
        if not units:
            raise UpdateFailed("No units found for INMES account")
        unit = units[0]
        unit_guid: str = unit["guid"]

        # Store unit info on coordinator for sensor device_info
        self.unit_name: str = unit.get("name", "INMES Unit")
        self.unit_guid: str = unit_guid

        # Meter readings
        meters_data = await self._get(
            session,
            headers,
            f"overview/unit/meters/{client_guid}/{building_guid}/{unit_guid}/null",
        )

        active_meters: dict[str, Any] = {}
        for meter in meters_data.get("meters", []):
            states = meter.get("states", [])
            if not states:
                continue
            if meter.get("demontage") is not None:
                continue
            if states[0].get("code") == -1:
                continue
            active_meters[meter["guid"]] = meter

        _LOGGER.debug("Fetched %d active meters", len(active_meters))
        return active_meters

    async def _get(
        self,
        session: aiohttp.ClientSession,
        headers: dict,
        path: str,
    ) -> dict:
        async with session.get(
            f"{API_V2}/get/{path}",
            headers=headers,
            timeout=TIMEOUT,
        ) as resp:
            if resp.status in (401, 403):
                raise ConfigEntryAuthFailed("INMES session rejected (re-auth required)")
            resp.raise_for_status()
            data = await resp.json(content_type=None)
        if not data.get("success"):
            raise UpdateFailed(f"INMES API error for {path}: {data.get('message')}")
        return data

    async def _get_first_guid(
        self,
        session: aiohttp.ClientSession,
        headers: dict,
        path: str,
        key: str,
    ) -> str:
        data = await self._get(session, headers, path)
        items = data.get(key, [])
        if not items:
            raise UpdateFailed(f"No {key} found for INMES account")
        guid: str = items[0]["guid"]
        return guid
