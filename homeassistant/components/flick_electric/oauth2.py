"""OAuth2 implementations for Toon."""

from __future__ import annotations

from typing import Any

from pyflick.const import DEFAULT_CLIENT_ID, DEFAULT_CLIENT_SECRET

from homeassistant.core import HomeAssistant
from homeassistant.helpers.config_entry_oauth2_flow import LocalOAuth2Implementation

from .const import DOMAIN, OAUTH2_AUTHORIZE, OAUTH2_TOKEN


class FlickElectricLocalOAuth2Implementation(LocalOAuth2Implementation):
    """Local OAuth2 implementation for Flick Electric."""

    def __init__(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Set up Flick Electric oauth."""
        super().__init__(
            hass=hass,
            domain=DOMAIN,
            client_id=DEFAULT_CLIENT_ID,
            client_secret=DEFAULT_CLIENT_SECRET,
            authorize_url=OAUTH2_AUTHORIZE,
            token_url=OAUTH2_TOKEN,
        )

    @property
    def name(self) -> str:
        """Name of the implementation."""
        return "Flick Electric"

    @property
    def extra_authorize_data(self) -> dict[str, Any]:
        """Extra data that needs to be appended to the authorize url."""
        return {"client_secret": self.client_secret}

    async def _async_refresh_token(self, token: dict) -> dict:
        """Refresh tokens."""
        new_token = await self._token_request(
            {
                "grant_type": "refresh_token",
                "refresh_token": token["refresh_token"],
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            }
        )
        return {**token, **new_token}
