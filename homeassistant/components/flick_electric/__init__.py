"""The Flick Electric integration."""

import logging

from pyflick import FlickAPI

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .api import HassFlickAuth
from .const import CONF_ACCOUNT_ID, CONF_SUPPLY_NODE_REF
from .coordinator import FlickConfigEntry, FlickElectricDataCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: FlickConfigEntry) -> bool:
    """Set up Flick Electric from a config entry."""
    auth = HassFlickAuth(hass, entry)

    coordinator = FlickElectricDataCoordinator(
        hass, FlickAPI(auth), entry.data[CONF_SUPPLY_NODE_REF]
    )

    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: FlickConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate old entry."""
    _LOGGER.debug(
        "Migrating configuration from version %s.%s",
        config_entry.version,
        config_entry.minor_version,
    )

    if config_entry.version > 2:
        return False

    if config_entry.version == 1:
        api = FlickAPI(HassFlickAuth(hass, config_entry))

        accounts = await api.getCustomerAccounts()
        active_accounts = [
            account for account in accounts if account["status"] == "active"
        ]

        # A single active account can be auto-migrated
        if (len(active_accounts)) == 1:
            account = active_accounts[0]

            new_data = {**config_entry.data}
            new_data[CONF_ACCOUNT_ID] = account["id"]
            new_data[CONF_SUPPLY_NODE_REF] = account["main_consumer"]["supply_node_ref"]
            hass.config_entries.async_update_entry(
                config_entry,
                title=account["address"],
                unique_id=account["id"],
                data=new_data,
                version=2,
            )
            return True

        config_entry.async_start_reauth(hass, data={**config_entry.data})
        return False

    return True
