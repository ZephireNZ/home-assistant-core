"""Common template functions."""

from typing import List

from homeassistant.core import callback
from homeassistant.helpers import entity_registry
from homeassistant.helpers.collection import (
    CHANGE_ADDED,
    CHANGE_REMOVED,
    CHANGE_UPDATED,
    ObservableCollection,
)
from homeassistant.helpers.typing import HomeAssistantType

TEMPLATE_ENTITIES: List[str] = []


@callback
def attach_template_listener(
    hass: HomeAssistantType,
    domain: str,
    platform: str,
    collection: ObservableCollection,
) -> None:
    """Attach a lister to monitor for template entities added or removed."""

    async def _collection_changed(change_type: str, item_id: str, config: dict) -> None:
        """Handle a collection change."""
        if change_type == CHANGE_UPDATED:
            return

        ent_reg = await entity_registry.async_get_registry(hass)
        entity_id = ent_reg.async_get_entity_id(domain, platform, item_id)

        if change_type == CHANGE_ADDED:
            TEMPLATE_ENTITIES.append(entity_id)
            return

        if change_type == CHANGE_REMOVED:
            TEMPLATE_ENTITIES.pop(entity_id)
            return

    collection.async_add_listener(_collection_changed)
