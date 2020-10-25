"""The template component."""
from homeassistant.components import websocket_api
from homeassistant.const import ATTR_ID, SERVICE_RELOAD
from homeassistant.helpers.reload import async_reload_integration_platforms
from homeassistant.helpers.typing import HomeAssistantType

from .common import TEMPLATE_ENTITIES
from .const import DOMAIN, EVENT_TEMPLATE_RELOADED, PLATFORMS


async def async_setup_reload_service(hass):
    """Create the reload service for the template domain."""

    if hass.services.has_service(DOMAIN, SERVICE_RELOAD):
        return

    async def _reload_config(call):
        """Reload the template platform config."""

        await async_reload_integration_platforms(hass, DOMAIN, PLATFORMS)
        hass.bus.async_fire(EVENT_TEMPLATE_RELOADED, context=call.context)

    hass.helpers.service.async_register_admin_service(
        DOMAIN, SERVICE_RELOAD, _reload_config
    )


@websocket_api.websocket_command({"type": "template/list"})
def get_templates(
    hass: HomeAssistantType, connection: websocket_api.ActiveConnection, msg
):
    """Get list of configured template entities."""

    connection.send_result(
        msg[ATTR_ID],
        TEMPLATE_ENTITIES,
    )
