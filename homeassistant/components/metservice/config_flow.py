"""Config flow for MetService integration."""
import logging

from pymetservice import get_cities_list
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_MODE

from .const import CONF_CITY, CONF_CITY_ID, CONF_MODE_DAILY, CONF_MODE_HOURLY, DOMAIN

_LOGGER = logging.getLogger(__name__)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for MetService."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    _cities: dict = None

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if self._cities is None:
            self._cities = get_cities_list()

        if user_input is not None:
            city_id = self._cities[user_input[CONF_CITY]]

            await self.async_set_unique_id(f"{city_id}-{user_input[CONF_MODE]}")
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=user_input[CONF_CITY],
                data={CONF_CITY_ID: city_id, CONF_MODE: user_input[CONF_MODE]},
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_CITY): vol.In(self._cities.keys()),
                    vol.Required(CONF_MODE, default=CONF_MODE_DAILY): vol.In(
                        [CONF_MODE_DAILY, CONF_MODE_HOURLY]
                    ),
                }
            ),
            errors=errors,
        )
