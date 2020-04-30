"""The MetService integration."""
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN  # noqa: F401


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the MetService component."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up MetService from a config entry."""
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, "weather")
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    if await hass.config_entries.async_forward_entry_unload(entry, "weather"):
        return True

    return False
