"""Config flow for OPNSense integration."""
from __future__ import annotations

from http import HTTPStatus
import logging
import socket
from typing import Any
from urllib.parse import urlparse

from pyopnsense import diagnostics
from pyopnsense.exceptions import APIException
import voluptuous as vol

from homeassistant import config_entries, data_entry_flow
from homeassistant.const import CONF_API_KEY, CONF_NAME, CONF_URL, CONF_VERIFY_SSL
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
import homeassistant.helpers.config_validation as cv

from .const import CONF_API_SECRET, CONF_TRACKER_INTERFACES, DOMAIN

_LOGGER = logging.getLogger(__name__)

ERROR_INVALID_URL = "invalid_url"
ERROR_INVALID_AUTH = "invalid_auth"
ERROR_PERMISSION_ARP_TABLE = "missing_permision_arp_table"
ERROR_PERMISSION_NETWORK_INSIGHT = "missing_permision_network_insight"
ERROR_UNKNOWN = "unknown"

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME, default="OPNSense"): str,
        vol.Required(CONF_URL): str,
        vol.Required(CONF_API_KEY): str,
        vol.Required(CONF_API_SECRET): str,
        vol.Optional(CONF_VERIFY_SSL, default=False): bool,
        vol.Optional(CONF_TRACKER_INTERFACES): list[str],
    }
)


async def async_validate_input(hass: HomeAssistant, data: dict[str, Any]) -> str | None:
    """Validate the user input allows us to connect."""

    try:
        cv.url(data[CONF_URL])
    except vol.Invalid:
        return ERROR_INVALID_URL

    params = {
        "api_key": data[CONF_API_KEY],
        "api_secret": data[CONF_API_SECRET],
        "base_url": data[CONF_URL],
        "verify_cert": [CONF_VERIFY_SSL],
        "timeout": 20,
    }

    try:
        api_permission = ERROR_PERMISSION_ARP_TABLE
        await hass.async_add_executor_job(diagnostics.InterfaceClient(**params).get_arp)

        api_permission = ERROR_PERMISSION_NETWORK_INSIGHT
        await hass.async_add_executor_job(
            diagnostics.NetworkInsightClient(**params).get_interfaces
        )
    except APIException as e:
        _LOGGER.exception("Failed to connect to OPNSense")
        if e.status_code == HTTPStatus.UNAUTHORIZED:
            return ERROR_INVALID_AUTH

        if e.status_code == HTTPStatus.FORBIDDEN:
            return api_permission

        return ERROR_UNKNOWN
    except Exception:  # pylint: disable=broad-except
        _LOGGER.exception("Failed to connect to OPNSense")
        return ERROR_UNKNOWN

    return None


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for OPNSense."""

    VERSION = 1
    MINOR_VERSION = 1

    async def async_check_configured_entry(self, user_input: dict[str, Any]) -> None:
        """Check if entry is configured."""
        await self.async_set_unique_id(user_input[CONF_URL])
        self._abort_if_unique_id_configured()

        # Also check if URL resolves to the same host
        new_host = await self.hass.async_add_executor_job(
            socket.gethostbyname, urlparse(str(user_input[CONF_URL])).hostname
        )

        for entry in self._async_current_entries(include_ignore=False):
            entry_host = await self.hass.async_add_executor_job(
                socket.gethostbyname, urlparse(str(entry.data[CONF_URL])).hostname
            )
            if entry_host == new_host:
                raise data_entry_flow.AbortFlow("already_configured")

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            await self.async_check_configured_entry(user_input)

            error_reason = await async_validate_input(self.hass, user_input)

            if error_reason:
                errors["base"] = error_reason
            else:
                return self.async_create_entry(
                    title=user_input[CONF_NAME], data=user_input
                )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_import(self, import_data: dict[str, Any]) -> FlowResult:
        """Import existing config from configuration.yaml."""
        return await self.async_step_user(import_data)
