"""OAuth2 implementations for Toon."""

from __future__ import annotations

from typing import Any

from homeassistant.components.application_credentials import (
    AuthImplementation,
    AuthorizationServer,
    ClientCredential,
)
from homeassistant.core import HomeAssistant


class FlickElectricLocalOAuth2Implementation(AuthImplementation):
    """Local OAuth2 implementation for Flick Electric."""

    def __init__(
        self,
        hass: HomeAssistant,
        domain: str,
        client_credential: ClientCredential,
        authorization_server: AuthorizationServer,
    ) -> None:
        """Set up Flick Electric oauth."""
        super().__init__(
            hass=hass,
            auth_domain=domain,
            credential=client_credential,
            authorization_server=authorization_server,
        )

        self._name = client_credential.name

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
