"""Config Flow for Flick Electric integration."""

from collections.abc import Mapping
import logging
from typing import Any

from aiohttp import ClientResponseError
from pyflick import FlickAPI
from pyflick.authentication import AbstractFlickAuth
from pyflick.const import DEFAULT_CLIENT_SECRET
from pyflick.types import APIException, AuthException, CustomerAccount
import voluptuous as vol

from homeassistant.config_entries import SOURCE_REAUTH, ConfigFlowResult
from homeassistant.const import (
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_PASSWORD,
    CONF_USERNAME,
)
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_entry_oauth2_flow
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import CONF_ACCOUNT_ID, CONF_SUPPLY_NODE_REF, DOMAIN

_LOGGER = logging.getLogger(__name__)

LOGIN_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Optional(CONF_CLIENT_ID): str,
        vol.Optional(CONF_CLIENT_SECRET): str,
    }
)


class FlickConfigFlow(
    config_entry_oauth2_flow.AbstractOAuth2FlowHandler, domain=DOMAIN
):
    """Flick config flow."""

    VERSION = 2
    DOMAIN = DOMAIN

    auth: AbstractFlickAuth
    accounts: list[CustomerAccount]
    data: dict[str, Any]

    @property
    def logger(self) -> logging.Logger:
        """Return logger."""
        return logging.getLogger(__name__)

    @property
    def extra_authorize_data(self) -> dict[str, Any]:
        """Extra data that needs to be appended to the authorize url."""
        return {"client_secret": DEFAULT_CLIENT_SECRET}

    async def async_step_select_account(
        self, user_input: Mapping[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask user to select account."""

        errors = {}
        if user_input is not None and CONF_ACCOUNT_ID in user_input:
            self.data[CONF_ACCOUNT_ID] = user_input[CONF_ACCOUNT_ID]
            self.data[CONF_SUPPLY_NODE_REF] = self._get_supply_node_ref(
                user_input[CONF_ACCOUNT_ID]
            )
            try:
                # Ensure supply node is active
                await FlickAPI(self.auth).getPricing(self.data[CONF_SUPPLY_NODE_REF])
            except (APIException, ClientResponseError):
                errors["base"] = "cannot_connect"
            except AuthException:
                # We should never get here as we have a valid token
                return self.async_abort(reason="no_permissions")
            else:
                # Supply node is active
                return await self._async_create_entry()

        try:
            self.accounts = await FlickAPI(self.auth).getCustomerAccounts()
        except (APIException, ClientResponseError):
            errors["base"] = "cannot_connect"

        active_accounts = [a for a in self.accounts if a["status"] == "active"]

        if len(active_accounts) == 0:
            return self.async_abort(reason="no_accounts")

        if len(active_accounts) == 1:
            self.data[CONF_ACCOUNT_ID] = active_accounts[0]["id"]
            self.data[CONF_SUPPLY_NODE_REF] = self._get_supply_node_ref(
                active_accounts[0]["id"]
            )

            return await self._async_create_entry()

        return self.async_show_form(
            step_id="select_account",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ACCOUNT_ID): SelectSelector(
                        SelectSelectorConfig(
                            options=[
                                SelectOptionDict(
                                    value=account["id"], label=account["address"]
                                )
                                for account in active_accounts
                            ],
                            mode=SelectSelectorMode.LIST,
                        )
                    )
                }
            ),
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Perform reauth upon an API authentication error."""

        # TODO: Check if this is migration or reauth
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Dialog that informs the user that reauth is required."""
        if user_input is None:
            return self.async_show_form(step_id="reauth_confirm")
        return await self.async_step_user()

    async def _async_create_entry(self) -> ConfigFlowResult:
        """Create an entry for the flow."""

        await self.async_set_unique_id(self.data[CONF_ACCOUNT_ID])

        account = self._get_account(self.data[CONF_ACCOUNT_ID])

        if self.source == SOURCE_REAUTH:
            # Migration completed
            if self._get_reauth_entry().version == 1:
                self.hass.config_entries.async_update_entry(
                    self._get_reauth_entry(),
                    unique_id=self.unique_id,
                    data=self.data,
                    version=self.VERSION,
                )

            return self.async_update_reload_and_abort(
                self._get_reauth_entry(),
                unique_id=self.unique_id,
                title=account["address"],
                data=self.data,
            )

        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title=account["address"],
            data=self.data,
        )

    def _get_account(self, account_id: str) -> CustomerAccount:
        """Get the account for the account ID."""
        return next(a for a in self.accounts if a["id"] == account_id)

    def _get_supply_node_ref(self, account_id: str) -> str:
        """Get the supply node ref for the account."""
        return self._get_account(account_id)["main_consumer"][CONF_SUPPLY_NODE_REF]

    async def async_oauth_create_entry(self, data: dict) -> ConfigFlowResult:
        """Handle successful OAuth from base implementation."""

        self.data = data

        # Before creating an entry, we need to select an account
        return await self.async_step_select_account(data)


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
