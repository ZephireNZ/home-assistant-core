"""Support for OPNSense Routers."""
from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import (
    CONF_API_KEY,
    CONF_NAME,
    CONF_URL,
    CONF_VERIFY_SSL,
    Platform,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .const import CONF_API_SECRET, CONF_TRACKER_INTERFACES, DOMAIN
from .coordinator import OPNSenseDataCoordinator

PLATFORMS: list[Platform] = [Platform.DEVICE_TRACKER]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up OPNSense from a config entry."""

    hass.data.setdefault(DOMAIN, {})

    hass.data[DOMAIN][entry.entry_id] = OPNSenseDataCoordinator(
        hass,
        entry.title,
        entry.data[CONF_URL],
        entry.data[CONF_API_KEY],
        entry.data[CONF_API_SECRET],
        entry.data[CONF_VERIFY_SSL],
        entry.data[CONF_TRACKER_INTERFACES],
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the OPNSense component."""
    if DOMAIN not in config:
        return True

    conf = config[DOMAIN]

    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_IMPORT},
            data={
                CONF_NAME: "OPNSense",
                CONF_URL: conf[CONF_URL],
                CONF_API_KEY: conf[CONF_API_KEY],
                CONF_API_SECRET: conf[CONF_API_SECRET],
                CONF_VERIFY_SSL: conf.get(CONF_VERIFY_SSL, False),
                CONF_TRACKER_INTERFACES: conf.get(CONF_TRACKER_INTERFACES, []),
            },
        )
    )

    return True
