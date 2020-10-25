"""Support for exposing a templated binary sensor."""
from functools import partial
import logging
import typing

import voluptuous as vol

from homeassistant.components.binary_sensor import (
    DEVICE_CLASSES_SCHEMA,
    DOMAIN,
    ENTITY_ID_FORMAT,
    PLATFORM_SCHEMA,
    BinarySensorEntity,
)
from homeassistant.const import (
    ATTR_EDITABLE,
    CONF_DEVICE_CLASS,
    CONF_ENTITY_ID,
    CONF_ENTITY_PICTURE_TEMPLATE,
    CONF_FRIENDLY_NAME,
    CONF_ICON_TEMPLATE,
    CONF_ID,
    CONF_SENSORS,
    CONF_UNIQUE_ID,
    CONF_VALUE_TEMPLATE,
)
from homeassistant.core import callback
from homeassistant.exceptions import TemplateError
from homeassistant.helpers import collection
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import async_generate_entity_id
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.reload import async_setup_reload_service
from homeassistant.helpers.storage import Store
from homeassistant.helpers.template import result_as_boolean
from homeassistant.helpers.typing import ConfigType, HomeAssistantType

from .common import attach_template_listener
from .const import CONF_AVAILABILITY_TEMPLATE, DOMAIN as TEMPLATE_DOMAIN, PLATFORMS
from .template_entity import TemplateEntity

CONF_DELAY_ON = "delay_on"
CONF_DELAY_OFF = "delay_off"
CONF_ATTRIBUTE_TEMPLATES = "attribute_templates"
STORAGE_KEY = f"template.{DOMAIN}"
STORAGE_VERSION = 1

SENSOR_SCHEMA = vol.All(
    cv.deprecated(CONF_ENTITY_ID),
    vol.Schema(
        {
            vol.Required(CONF_VALUE_TEMPLATE): cv.template,
            vol.Optional(CONF_ICON_TEMPLATE): cv.template,
            vol.Optional(CONF_ENTITY_PICTURE_TEMPLATE): cv.template,
            vol.Optional(CONF_AVAILABILITY_TEMPLATE): cv.template,
            vol.Optional(CONF_ATTRIBUTE_TEMPLATES): vol.Schema(
                {cv.string: cv.template}
            ),
            vol.Optional(CONF_FRIENDLY_NAME): cv.string,
            vol.Optional(CONF_ENTITY_ID): cv.entity_ids,
            vol.Optional(CONF_DEVICE_CLASS): DEVICE_CLASSES_SCHEMA,
            vol.Optional(CONF_DELAY_ON): cv.positive_time_period,
            vol.Optional(CONF_DELAY_OFF): cv.positive_time_period,
            vol.Optional(CONF_UNIQUE_ID): cv.string,
        }
    ),
)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {vol.Required(CONF_SENSORS): cv.schema_with_slug_keys(SENSOR_SCHEMA)}
)

STORAGE_SCHEMA = SENSOR_SCHEMA.extend({vol.Required(CONF_ID): cv.string})

CREATE_FIELDS = {
    vol.Required(CONF_FRIENDLY_NAME): vol.All(str, vol.Length(min=1)),
    vol.Required(CONF_VALUE_TEMPLATE): vol.All(cv.template, vol.Length(min=1)),
    vol.Optional(CONF_ICON_TEMPLATE): cv.template,
    vol.Optional(CONF_ENTITY_PICTURE_TEMPLATE): cv.template,
    vol.Optional(CONF_AVAILABILITY_TEMPLATE): cv.template,
    vol.Optional(CONF_DEVICE_CLASS): DEVICE_CLASSES_SCHEMA,
    vol.Optional(CONF_DELAY_ON): vol.All(cv.time_period, cv.positive_timedelta),
    vol.Optional(CONF_DELAY_OFF): vol.All(cv.time_period, cv.positive_timedelta),
    vol.Optional(CONF_ATTRIBUTE_TEMPLATES): vol.Schema({cv.string: cv.template}),
    vol.Optional(CONF_ENTITY_ID): cv.entity_ids,
}

UPDATE_FIELDS = {
    vol.Optional(CONF_FRIENDLY_NAME): cv.string,
    vol.Optional(CONF_VALUE_TEMPLATE): cv.template,
    vol.Optional(CONF_ICON_TEMPLATE): cv.template,
    vol.Optional(CONF_ENTITY_PICTURE_TEMPLATE): cv.template,
    vol.Optional(CONF_AVAILABILITY_TEMPLATE): cv.template,
    vol.Optional(CONF_DEVICE_CLASS): DEVICE_CLASSES_SCHEMA,
    vol.Optional(CONF_DELAY_ON): vol.All(cv.time_period, cv.positive_timedelta),
    vol.Optional(CONF_DELAY_OFF): vol.All(cv.time_period, cv.positive_timedelta),
    vol.Optional(CONF_ATTRIBUTE_TEMPLATES): vol.Schema({cv.string: cv.template}),
    vol.Optional(CONF_ENTITY_ID): cv.entity_ids,
}


async def _async_create_entities(hass, config):
    """Set up the helper storage and WebSockets."""
    storage_collection = BinarySensorStorageCollection(
        Store(hass, STORAGE_VERSION, STORAGE_KEY),
        logging.getLogger(f"{__name__}.storage_collection"),
    )
    collection.attach_entity_component_collection(
        hass.data[DOMAIN],
        storage_collection,
        partial(BinarySensorTemplate.from_storage, hass),
    )
    attach_template_listener(hass, DOMAIN, DOMAIN, storage_collection)

    await storage_collection.async_load()

    collection.StorageCollectionWebsocket(
        storage_collection, f"template/{DOMAIN}", DOMAIN, CREATE_FIELDS, UPDATE_FIELDS
    ).async_setup(hass)

    collection.attach_entity_registry_cleaner(hass, DOMAIN, DOMAIN, storage_collection)

    yaml_collection = collection.YamlCollection(
        logging.getLogger(f"{__name__}.yaml_collection")
    )

    collection.attach_entity_component_collection(
        hass.data[DOMAIN],
        yaml_collection,
        partial(BinarySensorTemplate.from_config, hass),
    )
    attach_template_listener(hass, DOMAIN, DOMAIN, yaml_collection)

    await yaml_collection.async_load(
        [{CONF_ID: id_, **cfg} for id_, cfg in config.get(CONF_SENSORS, {}).items()]
    )

    collection.attach_entity_registry_cleaner(hass, DOMAIN, DOMAIN, yaml_collection)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the template binary sensors."""

    await async_setup_reload_service(hass, TEMPLATE_DOMAIN, PLATFORMS)
    _async_create_entities(hass, config)


class BinarySensorStorageCollection(collection.StorageCollection):
    """Input storage based collection."""

    CREATE_SCHEMA = vol.Schema(CREATE_FIELDS)
    UPDATE_SCHEMA = vol.Schema(UPDATE_FIELDS)

    async def _process_create_data(self, data: typing.Dict) -> typing.Dict:
        """Validate the config is valid."""
        return self.CREATE_SCHEMA(data)

    @callback
    def _get_suggested_id(self, info: typing.Dict) -> str:
        """Suggest an ID based on the config."""
        return info.get(CONF_FRIENDLY_NAME)

    async def _update_data(self, data: dict, update_data: typing.Dict) -> typing.Dict:
        """Return a new updated data object."""
        return {**data, **self.UPDATE_SCHEMA(update_data)}


class BinarySensorTemplate(TemplateEntity, BinarySensorEntity):
    """A virtual binary sensor that triggers from another sensor."""

    def __init__(self, hass: HomeAssistantType, config: ConfigType):
        """Initialize the Template binary sensor."""
        super().__init__(
            attribute_templates=config.get(CONF_ATTRIBUTE_TEMPLATES, {}),
            availability_template=config.get(CONF_AVAILABILITY_TEMPLATE),
            icon_template=config.get(CONF_ICON_TEMPLATE),
            entity_picture_template=config.get(CONF_ENTITY_PICTURE_TEMPLATE),
        )
        self.hass = hass
        self.entity_id = async_generate_entity_id(
            ENTITY_ID_FORMAT, config.get(CONF_ID), hass=hass
        )
        self._attributes[ATTR_EDITABLE] = False

        self._name = config.get(CONF_FRIENDLY_NAME, config.get(CONF_ID))
        self._device_class = config.get(CONF_DEVICE_CLASS)
        self._template = config.get(CONF_VALUE_TEMPLATE)
        self._state = None
        self._delay_cancel = None
        self._delay_on = config.get(CONF_DELAY_ON)
        self._delay_off = config.get(CONF_DELAY_OFF)
        self._unique_id = config.get(CONF_UNIQUE_ID)

    @classmethod
    def from_storage(cls, hass, config: typing.Dict) -> "BinarySensorTemplate":
        """Return entity instance initialized from storage."""
        binary_sensor = cls.from_config(hass, config)
        binary_sensor._attributes[ATTR_EDITABLE] = True
        return binary_sensor

    @classmethod
    def from_config(cls, hass, config: typing.Dict) -> "BinarySensorTemplate":
        """Return entity instance initialized from a config."""
        return cls(hass, STORAGE_SCHEMA(config))

    async def async_added_to_hass(self):
        """Register callbacks."""

        self.add_template_attribute("_state", self._template, None, self._update_state)

        await super().async_added_to_hass()

    async def async_update_config(self, config: typing.Dict) -> None:
        """Handle when the config is updated."""
        self.entity_id = async_generate_entity_id(
            ENTITY_ID_FORMAT, config.get(CONF_ID), hass=self.hass
        )
        # TODO Update config to new Template format
        await self.async_update()
        self.async_write_ha_state()

    @callback
    def _update_state(self, result):
        super()._update_state(result)

        if self._delay_cancel:
            self._delay_cancel()
            self._delay_cancel = None

        state = None if isinstance(result, TemplateError) else result_as_boolean(result)

        if state == self._state:
            return

        # state without delay
        if (
            state is None
            or (state and not self._delay_on)
            or (not state and not self._delay_off)
        ):
            self._state = state
            return

        @callback
        def _set_state(_):
            """Set state of template binary sensor."""
            self._state = state
            self.async_write_ha_state()

        delay = (self._delay_on if state else self._delay_off).seconds
        # state with delay. Cancelled if template result changes.
        self._delay_cancel = async_call_later(self.hass, delay, _set_state)

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def unique_id(self):
        """Return the unique id of this binary sensor."""
        return self._unique_id

    @property
    def is_on(self):
        """Return true if sensor is on."""
        return self._state

    @property
    def device_class(self):
        """Return the sensor class of the binary sensor."""
        return self._device_class
