"""Config flow for INMES integration."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_EMAIL, CONF_PASSWORD, DOMAIN
from .coordinator import InmesCoordinator

_LOGGER = logging.getLogger(__name__)

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EMAIL): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


async def _validate_credentials(hass: HomeAssistant, email: str, password: str) -> None:
    """Attempt login to verify credentials. Raises on failure."""
    coordinator = InmesCoordinator(hass, email, password)
    session = async_get_clientsession(hass)
    await coordinator._login(session)


class InmesConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the INMES config flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            email = user_input[CONF_EMAIL]
            password = user_input[CONF_PASSWORD]

            try:
                await _validate_credentials(self.hass, email, password)
            except ConfigEntryAuthFailed:
                errors["base"] = "invalid_auth"
            except aiohttp.ClientError as err:
                _LOGGER.error("INMES cannot_connect: %s: %s", type(err).__name__, err)
                errors["base"] = "cannot_connect"
            except Exception as err:
                _LOGGER.exception("INMES unexpected error during login: %s: %s", type(err).__name__, err)
                errors["base"] = "unknown"

            if not errors:
                await self.async_set_unique_id(email.lower())
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=email,
                    data={CONF_EMAIL: email, CONF_PASSWORD: password},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_SCHEMA,
            errors=errors,
        )

    async def async_step_reauth(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Handle re-authentication when credentials expire."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            email = user_input[CONF_EMAIL]
            password = user_input[CONF_PASSWORD]

            try:
                await _validate_credentials(self.hass, email, password)
            except ConfigEntryAuthFailed:
                errors["base"] = "invalid_auth"
            except aiohttp.ClientError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error during INMES re-auth")
                errors["base"] = "unknown"

            if not errors:
                self.hass.config_entries.async_update_entry(
                    self._get_reauth_entry(),
                    data={CONF_EMAIL: email, CONF_PASSWORD: password},
                )
                await self.hass.config_entries.async_reload(
                    self._get_reauth_entry().entry_id
                )
                return self.async_abort(reason="reauth_successful")

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=STEP_USER_SCHEMA,
            errors=errors,
        )
