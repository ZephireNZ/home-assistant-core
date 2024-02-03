"""Data Coordinator for OPNSense integration."""
from datetime import timedelta
import logging
from typing import TypedDict

from homeassistant.core import HomeAssistant
from homeassistant.helpers import update_coordinator

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class UpdateCoordinatorDataType(TypedDict):
    """Update coordinator data type."""


class OPNSenseDataCoordinator(
    update_coordinator.DataUpdateCoordinator[UpdateCoordinatorDataType]
):
    """OPNSense Data Coordinator."""

    def __init__(
        self,
        hass: HomeAssistant,
        name: str,
        base_url: str,
        api_key: str,
        api_secret: str,
        verify_ssl: bool,
        tracker_interfaces: list[str],
    ) -> None:
        """Initialize OPNSense data coordinator."""
        super().__init__(
            hass=hass,
            logger=_LOGGER,
            name=f"{DOMAIN}-{name}-coordinator",
            update_interval=timedelta(seconds=30),
        )
        self.base_url = base_url
        self.api_key = api_key
        self.api_secret = api_secret
        self.verify_ssl = verify_ssl
