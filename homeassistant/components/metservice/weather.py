"""Support for Met.no weather service."""
from datetime import timedelta
import logging

import pymetservice
import voluptuous as vol

from homeassistant.components.weather import PLATFORM_SCHEMA, WeatherEntity
from homeassistant.const import CONF_NAME, TEMP_CELSIUS
from homeassistant.helpers import config_validation as cv
from homeassistant.util import Throttle

from .const import CONF_CITY_ID

_LOGGER = logging.getLogger(__name__)

ATTRIBUTION = "Weather forecast from MetService - Te Ratonga Tirorangi"
DEFAULT_NAME = "MetService"

MIN_TIME_BETWEEN_FORECAST_UPDATES = timedelta(minutes=30)
MIN_TIME_BETWEEN_UPDATES = timedelta(minutes=10)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Required(CONF_CITY_ID): cv.string,
    }
)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Add a weather entity from a config_entry."""
    async_add_entities([MetServiceWeather(config_entry.data)], True)


class MetServiceWeather(WeatherEntity):
    """Implementation of a Met.no weather condition."""

    def __init__(self, config):
        """Initialise the platform with a data instance and site."""
        self._config = config

        cities = pymetservice.get_cities_list()
        city_ids = {value: key for key, value in cities.items()}

        self._city_id = config[CONF_CITY_ID]
        self._name = city_ids[self._city_id]

        self._current_weather = None  # Local Obs
        self._forecast_daily = None  # Local Forecast
        self._forecast_hourly = None  # Hourly Obs and Forecast

    async def async_update(self):
        """Get latest data from MetService (throttled)."""
        await self._update_current()
        await self._update_forecast()

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    async def _update_current(self):
        localObs = pymetservice.getLocalObs(self._city_id)
        self._current_weather = localObs["threeHour"]

    @Throttle(MIN_TIME_BETWEEN_FORECAST_UPDATES)
    async def _update_forecast(self):
        # TODO
        localForecast = pymetservice.getLocalForecast(self._city_id)
        hourlyObs = pymetservice.getHourlyObsAndForecast(self._city_id)
        self._forecast_daily = localForecast["days"]
        self._forecast_hourly = hourlyObs["forecastData"]

    async def async_added_to_hass(self):
        """Start fetching data."""
        await self.async_update()
        self.async_write_ha_state

    @property
    def unique_id(self):
        """Return the unique ID."""
        return self._city_id

    @property
    def name(self):
        """Return the name."""
        return self._name

    @property
    def condition(self):
        """Return the current condition."""
        return "WIP"

    @property
    def temperature(self):
        """Return the temperature."""
        return int(self._current_weather.get("temp"))

    @property
    def temperature_unit(self):
        """Return the unit of measurement."""
        return TEMP_CELSIUS

    @property
    def pressure(self):
        """Return the pressure."""
        return int(self._current_weather.get("pressure"))

    @property
    def humidity(self):
        """Return the humidity."""
        return int(self._current_weather.get("humidity"))

    @property
    def wind_speed(self):
        """Return the wind speed."""
        return int(self._current_weather.get("windSpeed"))

    @property
    def wind_bearing(self):
        """Return the wind direction."""
        return str(self._current_weather.get("windDirection"))

    @property
    def attribution(self):
        """Return the attribution."""
        return ATTRIBUTION

    @property
    def forecast(self):
        """Return the forecast array."""
        return []
