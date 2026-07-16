import logging
import math
from dataclasses import dataclass
from enum import StrEnum

from src.climate import Climate
from src.game_weather_state_machine import GameWeatherStateMachine, WeatherType

logging.basicConfig(filename='biome.log', filemode='w', level=logging.INFO)
logger = logging.Logger(__name__)


@dataclass
class YearlyBiomeStats:
    year: int
    rainfall: float
    ag_yield: float


@dataclass
class DailyBiomeStats:
    tick: int
    year: int
    day_of_year: int

    weather: str
    relative_humidity: float
    temperature: float
    available_water: float
    agriculture: float

    # soil_moisture: float
    # soil_percent_full: float
    # water_table: float
    # runoff: float
    #
    # groundwater_uptake: float
    # percolation: float
    # groundwater_outflow: float
    # et_loss: float
    #
    # flood_severity: float
    # flood_damage: float
    #
    # soil_yield_modifier: float
    # weather_yield_modifier: float
    # daily_ag_yield: float
    # ag_points: float


class BiomeEnum(StrEnum):
    Plains = "plains"
    Forest = "forest"
    Coast = "coast"
    Desert = "desert"
    Hills = "hills"
    Mountains = "mountains"
    Null = "null"
    Ocean = "ocean"


class DroughtLevels(StrEnum):
    Saturated = "saturated"
    Wet = "wet"
    Normal = "normal"
    Dry = "dry"
    Drought = "drought"
    SevereDrought = "severe_drought"


BIOMES = {
    BiomeEnum.Plains: {
        "name": BiomeEnum.Plains,
        "biome_base_temperature": 80.0,
        "temperature": 80.0,
        "temperature_swing": 15,
        "relative_humidity": 0.5,
        "available_water": 3.0,
        "agriculture": 0.0
        # "evapotranspiration": 0.055,
        # "soil_moisture": 6.0,
        # "soil_capacity": 15.0, # was 10.0
        #
        # # Agricultural yields
        # "ag_yield_modifier": 1.0,
        # "harvest_threshold": 100.0,
        #
        # # Percentages: 55% soil, 20% groundwater, 25% runoff.
        # "soil_percent": 80.0,
        # "groundwater_percent": 0.0,
        # "runoff_percent": 20.0,
        #
        # # Fraction of groundwater lost each tick as baseflow/deep drainage.
        # "groundwater_discharge": 0.009,
        #
        # "rainfall_multiplier": 1.0,
        # "hydrology_enabled": True,
    # },

    # BiomeEnum.Forest: {
    #     "name": BiomeEnum.Forest,
    #     "biome_base_temperature": 70.0,
    #     "temperature": 70.0,
    #     "temperature_swing": 20,
    #     "relative_humidity": 0.5,
    #     "available_water": 12.0,
        # "evapotranspiration": 0.075,
        # "soil_moisture": 8.0,
        # "soil_capacity": 42.0, # was 14
        #
        # "ag_yield_modifier": 1.0,
        # "harvest_threshold": 110.0,
        #
        # # Forest: high soil retention, moderate groundwater, low runoff.
        # "soil_percent": 45.0,
        # "groundwater_percent": 40.0,
        # "runoff_percent": 15.0,
        #
        # "groundwater_discharge": 0.007,
        #
        # "rainfall_multiplier": 1.15,
        # "hydrology_enabled": True,
    },

    # BiomeEnum.Coast: {
    #     "name": BiomeEnum.Coast,
    #     "temperature": 85,
    #     "temperature_swing": 8,
    #     "relative_humidity": 0.6,
    #     "evapotranspiration": 0.060,
    #     "soil_moisture": 7.0,
    #     "soil_capacity": 10.0,
    #
    #     # Coast: retains some soil water, recharges groundwater, sheds some runoff.
    #     "soil_percent": 55.0,
    #     "groundwater_percent": 30.0,
    #     "runoff_percent": 15.0,
    #
    #     "groundwater_discharge": 0.020,
    #
    #     "rainfall_multiplier": 1.25,
    #     "hydrology_enabled": True,
    # },
    #
    # BiomeEnum.Desert: {
    #     "name": BiomeEnum.Desert,
    #     "temperature": 95,
    #     "temperature_swing": 20,
    #     "relative_humidity": 0.1,
    #     "evapotranspiration": 0.50,
    #     "soil_moisture": 1.0,
    #     "soil_capacity": 3.0,
    #
    #     # Desert: most rain becomes flash-flood runoff.
    #     "soil_percent": 8.0,
    #     "groundwater_percent": 4.0,
    #     "runoff_percent": 88.0,
    #
    #     "groundwater_discharge": 0.030,
    #
    #     "rainfall_multiplier": 0.45,
    #     "hydrology_enabled": True,
    # },
    #
    # BiomeEnum.Hills: {
    #     "name": BiomeEnum.Hills,
    #     "temperature": 65,
    #     "temperature_swing": 10,
    #     "relative_humidity": 0.4,
    #     "evapotranspiration": 0.08,
    #     "soil_moisture": 5.0,
    #     "soil_capacity": 10.0,
    #
    #     # Hills: decent soil retention, but a lot runs off.
    #     "soil_percent": 50.0,
    #     "groundwater_percent": 25.0,
    #     "runoff_percent": 25.0,
    #
    #     "groundwater_discharge": 0.025,
    #
    #     "rainfall_multiplier": 1.30,
    #     "hydrology_enabled": True,
    # },
    #
    # BiomeEnum.Mountains: {
    #     "name": BiomeEnum.Mountains,
    #     "temperature": 40,
    #     "temperature_swing": 15,
    #     "relative_humidity": 0.2,
    #     "evapotranspiration": 0.020,
    #     "soil_moisture": 2.0,
    #     "soil_capacity": 3.0,
    #
    #     # Mountains: thin rocky soil; most precipitation becomes runoff.
    #     # Some becomes groundwater, but groundwater discharges quickly as springs/headwaters.
    #     "soil_percent": 10.0,
    #     "groundwater_percent": 20.0,
    #     "runoff_percent": 70.0,
    #
    #     "groundwater_discharge": 0.070,
    #
    #     "rainfall_multiplier": 1.80,
    #     "hydrology_enabled": True,
    # },
    #
    # BiomeEnum.Ocean: {
    #     "name": BiomeEnum.Ocean,
    #     "temperature": 70,
    #     "temperature_swing": 8,
    #     "relative_humidity": 0.9,
    #     "evapotranspiration": 0.0,
    #     "soil_moisture": 0.0,
    #     "soil_capacity": 0.0,
    #
    #     # Ocean bypasses land hydrology. Rainfall is effectively surface water.
    #     "soil_percent": 0.0,
    #     "groundwater_percent": 0.0,
    #     "runoff_percent": 100.0,
    #
    #     "groundwater_discharge": 0.0,
    #
    #     "rainfall_multiplier": 1.0,
    #     "hydrology_enabled": False,
    # },
}


def rolling_average(values: list[float], window: int = 5) -> float:
    if not values:
        return 0.0

    sample = values[-window:]
    return sum(sample) / len(sample)


class Biome:
    def __init__(self):
        self.name: BiomeEnum = BiomeEnum.Null
        self.temperature: float = 0.0
        self.biome_base_temperature: float = 0.0
        self.relative_humidity: float = 0.0
        self.available_water: float = 0.0
        self.daily_stats: list[DailyBiomeStats] = []
        self.agriculture: float = 0.0
        self.annual_rainfall: float = 0.0
        self.weather = GameWeatherStateMachine()
        self.annual_stats: list[YearlyBiomeStats] = []

    def from_json(self, json_obj):
        self.name = BiomeEnum(json_obj["name"])
        self.temperature = json_obj["temperature"]
        self.biome_base_temperature = json_obj["biome_base_temperature"]
        self.relative_humidity = json_obj["relative_humidity"]
        self.available_water = json_obj["available_water"]
        self.agriculture = json_obj["agriculture"]

    def update_temperature(self, tick_value: int) -> None:
        new_temperature: float = self.biome_base_temperature
        new_temperature *= Climate.seasonal_temperature_oscillator(tick_value)
        new_temperature *= Climate.global_temperature_oscillator(tick_value)
        self.temperature = new_temperature

    def update_relative_humidity(self, tick_value: int) -> None:
        new_relative_humidity: float = self.relative_humidity
        relative_humidity_delta = self.relative_humidity * (
                Climate.global_humidity_oscillator(tick_value) *
                Climate.seasonal_humidity_oscillator(tick_value) *
                Climate.truncated_normal())
        new_relative_humidity = (new_relative_humidity + relative_humidity_delta) if self.temperature > 32 else (
            new_relative_humidity - relative_humidity_delta
        )
        new_relative_humidity = min(new_relative_humidity, 1.0)
        new_relative_humidity = max(new_relative_humidity, 0.1)
        self.relative_humidity = new_relative_humidity

    def rainfall(self, tick_count: int):
        temp_ratio = self.temperature / self.biome_base_temperature
        rainfall_ratio = max(0.1, 2.0 - temp_ratio)
        rain = self.relative_humidity * rainfall_ratio * 1.2
        self.annual_rainfall += rain
        # print(temp_ratio, rainfall_ratio, rain)
        self.available_water += rain
        heat_factor = min(1.0, self.temperature / self.biome_base_temperature)
        humidity_retention = 0.1 + (heat_factor * 0.4)
        self.relative_humidity *= humidity_retention
        # print(tick_count, self.temperature, rainfall_ratio, self.relative_humidity, rain, self.available_water)

    def update_et(self, tick_count: int) -> None:
        temp_ratio = max(0.0, (self.temperature - 32) / 32)  # evap should be zero if temp is below freezing
        evaporation_multi = 0.02 * temp_ratio
        crop_usage_multi = 0.008 * self.agriculture  # crop usage should scale with growth (more biomass more usage)
        water_usage = (evaporation_multi + crop_usage_multi)
        self.available_water = max(self.available_water - water_usage, 0.0)
        # print(tick_count, temp_ratio, evaporation_multi, crop_usage_multi, water_usage, self.available_water)

    def update_agriculture(self):
        base_growth = 1.0
        base_growth *= self.temperature_growth_factor()
        base_growth *= self.water_growth_factor()
        base_growth *= self.weather_growth_factor()
        self.agriculture += base_growth

    def temperature_growth_factor(self) -> float:
        if self.temperature < 32:
            return 0.0
        elif self.temperature < 100:
            return (self.temperature - 32) / (75 - 32)
        else:
            return 0.0

    def water_growth_factor(self):
        if self.available_water <= 0:
            return 0.0
        if self.available_water < 5:
            return self.available_water / 5
        if self.available_water <= 8:
            return 1.0
        if self.available_water <= 10:
            return (10 - self.available_water) / 2
        return 0.0

    def weather_growth_factor(self) -> float:
        if self.weather.current_state == WeatherType.Rain:
            return 0.0
        if self.weather.current_state == WeatherType.Cloudy:
            return 0.8
        if self.weather.current_state == WeatherType.Clear:
            return 1.0
        return 0.0

    def harvest(self):
        ag_yield = self.agriculture
        return ag_yield

    def reset_annual_counters(self, tick_count: int) -> None:
        self.annual_stats.append(
            YearlyBiomeStats(
                year=tick_count // 112,
                ag_yield=self.agriculture,
                rainfall=self.annual_rainfall
            )
        )
        self.annual_rainfall = 0.0
        self.agriculture = 0.0









        
