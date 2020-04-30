"""Support for Met.no weather service."""
from datetime import timedelta
import logging

from dateutil.parser import isoparse
import pymetservice

from homeassistant.components.weather import (
    ATTR_FORECAST_CONDITION,
    ATTR_FORECAST_PRECIPITATION,
    ATTR_FORECAST_TEMP,
    ATTR_FORECAST_TEMP_LOW,
    ATTR_FORECAST_TIME,
    ATTR_FORECAST_WIND_BEARING,
    ATTR_FORECAST_WIND_SPEED,
    WeatherEntity,
)
from homeassistant.const import CONF_MODE, TEMP_CELSIUS
from homeassistant.util import Throttle, dt

from .const import CONF_CITY_ID, CONF_MODE_DAILY, CONF_MODE_HOURLY

_LOGGER = logging.getLogger(__name__)

ATTRIBUTION = "Data provided by MetService - Te Ratonga Tirorangi"

MIN_TIME_BETWEEN_FORECAST_UPDATES = timedelta(minutes=30)
MIN_TIME_BETWEEN_UPDATES = timedelta(minutes=10)

CONDITION_MAP = {
    "Partly cloudy": "partlycloudy",
    "Few showers": "rainy",
    "Wind rain": "rainy",
    "Showers": "rainy",
    "Fine": "sunny",
    "Rain": "rainy",
    "Cloudy": "cloudy",
    "Fog": "fog",
    "Thunder": "lightning",
    "Windy": "windy",
}


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Add a weather entity from a config_entry."""

    cities = await hass.async_add_executor_job(pymetservice.get_cities_list)
    city_ids = {value: key for key, value in cities.items()}
    name = city_ids[config_entry.data[CONF_CITY_ID]]

    async_add_entities([MetServiceWeather(hass, config_entry.data, name)], True)


class MetServiceWeather(WeatherEntity):
    """Implementation of a Met.no weather condition."""

    def __init__(self, hass, config, name):
        """Initialise the platform with a data instance and site."""
        self._mode = config[CONF_MODE]
        self._hass = hass
        self._name = name
        self._city_id = config[CONF_CITY_ID]

        self._current_weather = None  # Local Obs
        self._forecast = None  # Local Forecast

    async def async_update(self):
        """Get latest data from MetService (throttled)."""
        await self._update_current()
        await self._update_forecast()

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    async def _update_current(self):
        localObs = await self._hass.async_add_executor_job(
            pymetservice.getLocalObs, self._city_id
        )
        self._current_weather = localObs["threeHour"]

    @Throttle(MIN_TIME_BETWEEN_FORECAST_UPDATES)
    async def _update_forecast(self):
        # MetService do not provide live weather condition name, so use the daily condition
        forecast = await self._hass.async_add_executor_job(
            pymetservice.getLocalForecast, self._city_id
        )
        forecast = forecast["days"]

        today = forecast[0]

        self._condition = CONDITION_MAP.get(today["forecastWord"], "sunny")

        # Override to night time if outside of daytime
        sun_rise = isoparse(today["riseSet"]["sunRiseISO"])
        sun_set = isoparse(today["riseSet"]["sunSetISO"])
        now = dt.utcnow()
        if now < sun_rise or now > sun_set:
            self._condition = "clear-night"

        self._forecast = []
        if self._mode == CONF_MODE_DAILY:
            for data in forecast:
                if data["forecastWord"] not in CONDITION_MAP:
                    _LOGGER.warning(
                        "Unrecognised weather condition: %s", data["forecastWord"]
                    )

                self._forecast.append(
                    {
                        ATTR_FORECAST_CONDITION: CONDITION_MAP.get(
                            data["forecastWord"], "sunny"
                        ),
                        ATTR_FORECAST_TIME: isoparse(data["dateISO"]),
                        ATTR_FORECAST_TEMP: int(data["max"]),
                        ATTR_FORECAST_TEMP_LOW: int(data["min"]),
                    }
                )

        elif self._mode == CONF_MODE_HOURLY:
            forecast = await self._hass.async_add_executor_job(
                pymetservice.getHourlyObsAndForecast, self._city_id
            )
            forecast = forecast["forecastData"]

            for data in forecast:
                self._forecast.append(
                    {
                        ATTR_FORECAST_TIME: isoparse(data["dateISO"]),
                        ATTR_FORECAST_PRECIPITATION: float(data["rainFall"]),
                        ATTR_FORECAST_TEMP: int(data["temperature"]),
                        ATTR_FORECAST_WIND_BEARING: data["windDir"],
                        ATTR_FORECAST_WIND_SPEED: data["windSpeed"],
                    }
                )

    async def async_added_to_hass(self):
        """Start fetching data."""
        await self.async_update()
        self.async_write_ha_state()

    @property
    def unique_id(self):
        """Return the unique ID."""
        return f"{self._city_id}_{self._mode}"

    @property
    def name(self):
        """Return the name."""
        return self._name

    @property
    def condition(self):
        """Return the current condition."""
        return self._condition

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
        return self._forecast
