"""API authentication for Flick Electric integration."""

from pyflick.authentication import AbstractFlickAuth

from homeassistant.core import HomeAssistant
from homeassistant.helpers import aiohttp_client, config_entry_oauth2_flow


class HassFlickAuth(AbstractFlickAuth):
    """Implementation of AbstractFlickAuth based on a Home Assistant entity config."""

    def __init__(
        self, hass: HomeAssistant, oauth_session: config_entry_oauth2_flow.OAuth2Session
    ) -> None:
        """Flick authentication based on a Home Assistant entity config."""
        super().__init__(aiohttp_client.async_get_clientsession(hass))
        self._oauth_session = oauth_session
        self._hass = hass

    async def async_get_access_token(self):
        """Get Access Token from OAuth session."""
        await self._oauth_session.async_ensure_token_valid()

        return self._oauth_session.token["id_token"]
