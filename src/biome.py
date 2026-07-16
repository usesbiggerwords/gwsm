import logging
import random
from dataclasses import dataclass
from enum import StrEnum

from src.climate import Climate
from src.game_weather_state_machine import GameWeatherStateMachine, WeatherType

logging.basicConfig(filename='biome.log', filemode='w', level=logging.INFO)
logger = logging.Logger(__name__)


@dataclass
class YearlyBiomeStats:
    year: int
    humidity: float
    rainfall: float
    rain_events: int
    soil_moisture: float
    et_loss: float
    groundwater_loss: float
    water_table: float
    water_balance: float
    runoff: float


@dataclass
class DailyBiomeStats:
    tick: int
    year: int
    day_of_year: int

    weather: str
    humidity: float
    rainfall: float

    soil_moisture: float
    soil_percent_full: float
    water_table: float
    runoff: float

    groundwater_uptake: float
    percolation: float
    groundwater_outflow: float
    et_loss: float

    flood_severity: float
    flood_damage: float

    soil_yield_modifier: float
    weather_yield_modifier: float
    daily_ag_yield: float
    ag_points: float


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
        "temperature": 80,
        "temperature_swing": 15,
        "humidity": 0.5,
        "evapotranspiration": 0.055,
        "soil_moisture": 6.0,
        "soil_capacity": 15.0, # was 10.0

        # Agricultural yields
        "ag_yield_modifier": 1.0,
        "harvest_threshold": 100.0,

        # Percentages: 55% soil, 20% groundwater, 25% runoff.
        "soil_percent": 80.0,
        "groundwater_percent": 0.0,
        "runoff_percent": 20.0,

        # Fraction of groundwater lost each tick as baseflow/deep drainage.
        "groundwater_discharge": 0.009,

        "rainfall_multiplier": 1.0,
        "hydrology_enabled": True,
    },

    BiomeEnum.Forest: {
        "name": BiomeEnum.Forest,
        "temperature": 70,
        "temperature_swing": 8,
        "humidity": 0.6,
        "evapotranspiration": 0.075,
        "soil_moisture": 8.0,
        "soil_capacity": 42.0, # was 14

        "ag_yield_modifier": 1.0,
        "harvest_threshold": 110.0,

        # Forest: high soil retention, moderate groundwater, low runoff.
        "soil_percent": 45.0,
        "groundwater_percent": 40.0,
        "runoff_percent": 15.0,

        "groundwater_discharge": 0.007,

        "rainfall_multiplier": 1.15,
        "hydrology_enabled": True,
    },

    # BiomeEnum.Coast: {
    #     "name": BiomeEnum.Coast,
    #     "temperature": 85,
    #     "temperature_swing": 8,
    #     "humidity": 0.6,
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
    #     "humidity": 0.1,
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
    #     "humidity": 0.4,
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
    #     "humidity": 0.2,
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
    #     "humidity": 0.9,
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
        self.drought: DroughtLevels = DroughtLevels.Normal
        self.harvest_threshold = 0.0
        self.annual_runoff: float = 0.0
        self.name: BiomeEnum = BiomeEnum.Null

        self.temperature: float = 0.0
        self.temperature_swing: float = 0.0
        self.humidity: float = 0.0

        self.evapotranspiration: float = 0.0

        self.soil_moisture: float = 0.0
        self.soil_capacity: float = 0.0

        # User-facing configuration values.
        self.soil_percent: float = 0.0
        self.groundwater_percent: float = 0.0
        self.runoff_percent: float = 0.0

        # Internal normalized fractions derived from percentages.
        self.soil_fraction: float = 0.0
        self.groundwater_fraction: float = 0.0
        self.runoff_fraction: float = 0.0

        self.groundwater_discharge: float = 0.0

        self.runoff: float = 0.0

        self.rainfall_multiplier: float = 0.0
        self.hydrology_enabled: bool = True
        self.rain_events: list[tuple[str, float]] = []
        # Agricultural yields
        self.ag_yield_modifier: float = 0.0
        self.ag_points: float = 0.0
        self.flood_damage: float = 0.0
        
        # Annual totals
        self.annual_rainfall: float = 0.0
        self.annual_et_loss: float = 0.0
        self.annual_groundwater_loss: float = 0.0
        self.annual_average_humidity: float = 0.0
        self.annual_ag_yield: float = 0.0
        self.annual_history: list[YearlyBiomeStats] = []
        self.daily_stats: list[DailyBiomeStats] = []
        self.water_table: float = 0.0

        self.weather_machine: GameWeatherStateMachine | None = None

    def report(self):
        parts = [f"{k}: {v}\n" for k, v in self.__dict__.items() if v is not None]
        return "".join(parts)

    def from_json(self, json_obj):
        self.name = json_obj["name"]

        self.temperature = json_obj["temperature"]
        self.temperature_swing = json_obj["temperature_swing"]
        self.humidity = json_obj["humidity"]

        self.evapotranspiration = json_obj["evapotranspiration"]

        self.soil_moisture = json_obj["soil_moisture"]
        self.soil_capacity = json_obj["soil_capacity"]

        self.soil_percent = json_obj["soil_percent"]
        self.groundwater_percent = json_obj["groundwater_percent"]
        self.runoff_percent = json_obj["runoff_percent"]

        self.groundwater_discharge = json_obj["groundwater_discharge"]

        self.rainfall_multiplier = json_obj["rainfall_multiplier"]
        self.hydrology_enabled = json_obj.get("hydrology_enabled", True)

        self._normalize_water_percentages()

        self.ag_yield_modifier = json_obj["ag_yield_modifier"]
        self.harvest_threshold = json_obj["harvest_threshold"]

    def to_json(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if v is not None}

    def to_minimal_json(self) -> dict:
        return {
            "name": self.name,
            "temperature": self.temperature,
            "humidity": self.humidity,
            "runoff": self.runoff,
            "soil_moisture": self.soil_moisture,
            "soil_capacity": self.soil_capacity,
            "soil_percent_full": self.soil_percent_full(),
            "annual_rainfall": self.annual_rainfall,
            "water_table": self.water_table,
            "available_water": self.available_water(),
            "drought_index": self.drought_index(),
            "drought_status": self.drought_status(),
        }

    def _normalize_water_percentages(self):
        if not self.hydrology_enabled:
            self.soil_fraction = 0.0
            self.groundwater_fraction = 0.0
            self.runoff_fraction = 1.0
            return

        total = self.soil_percent + self.groundwater_percent + self.runoff_percent

        if total <= 0.0:
            raise ValueError(
                f"{self.name} water percentages must sum to a positive value."
            )

        self.soil_fraction = self.soil_percent / total
        self.groundwater_fraction = self.groundwater_percent / total
        self.runoff_fraction = self.runoff_percent / total

    def record_yearly_stats(self, year: int) -> None:
        self.annual_history.append(
            YearlyBiomeStats(
                year=year,
                humidity=self.annual_average_humidity / 112,
                rainfall=self.annual_rainfall,
                rain_events=len(self.rain_events),
                soil_moisture=self.soil_moisture,
                et_loss=self.annual_et_loss,
                groundwater_loss=self.annual_groundwater_loss,
                water_table=self.water_table,
                water_balance=self.annual_water_balance(),
                runoff=self.annual_runoff
            )
        )

    def five_year_averages(self) -> dict[str, float]:
        history = self.annual_history

        return {
            "rainfall": rolling_average(
                [year.rainfall for year in history],
                window=5,
            ),
            "rain_events": rolling_average(
                [year.rain_events for year in history],
                window=5,
            ),
            "soil_moisture": rolling_average(
                [year.soil_moisture for year in history],
                window=5,
            ),
            "et_loss": rolling_average(
                [year.et_loss for year in history],
                window=5,
            ),
            "groundwater_loss": rolling_average(
                [year.groundwater_loss for year in history],
                window=5,
            ),
            "water_table": rolling_average(
                [year.water_table for year in history],
                window=5,
            ),
            "water_balance": rolling_average(
                [year.water_balance for year in history],
                window=5,
            ),
        }

    def reset_annual_counters(self):
        self.annual_et_loss = 0.0
        self.annual_groundwater_loss = 0.0
        self.annual_rainfall = 0.0
        self.annual_runoff = 0.0
        self.annual_ag_yield = 0.0
        self.ag_points = 0.0
        self.flood_damage = 0.0
        self.rain_events = []

    def annual_water_balance(self) -> float:
        return (
                self.annual_rainfall
                - self.annual_et_loss
                - self.annual_groundwater_loss
        )

    def soil_percent_full(self) -> float:
        if self.soil_capacity <= 0.0:
            return 0.0

        return max(
            0.0,
            min(100.0, (self.soil_moisture / self.soil_capacity) * 100.0),
        )

    def available_water(self) -> float:
        """
        Combined availability score for downstream systems.

        Soil water is immediately available.
        Groundwater is partially available because it supports springs,
        roots, recharge, and drought buffering but is less direct than soil moisture.
        """
        return self.soil_moisture + (self.water_table * 0.25)

    def drought_index(self) -> float:
        """
        0.0 = no available water
        1.0 = roughly normal/full water availability
        >1.0 = unusually wet/saturated
        """
        if not self.hydrology_enabled or self.soil_capacity <= 0.0:
            return 1.0

        normal_available_water = self.soil_capacity

        return max(0.0, self.available_water() / normal_available_water)

    def drought_status(self) -> str:
        yield_index = self.annual_ag_yield / self.harvest_threshold
        if yield_index < 0.1:
            return DroughtLevels.SevereDrought.value
        if yield_index < 0.35:
            return DroughtLevels.Drought.value
        if yield_index < 0.50:
            return DroughtLevels.Dry.value
        if yield_index < 1.0:
            return DroughtLevels.Normal.value
        return DroughtLevels.Wet.value
    
    def flood_severity(self) -> float:
        if self.runoff <= 0.25:
            return 0.0
        if self.runoff <= 0.5:
            return 0.05
        if self.runoff <= 1.0:
            return 0.10
        if self.runoff <= 1.5:
            return 0.15
        return 0.20

    def soil_yield_modifier(self):
        soil_pct = self.soil_percent_full() / 100.0
        if soil_pct <= 0.1:
            return 0.0
        if soil_pct <= 0.5:
            return (soil_pct - 0.1) / 0.4
        if soil_pct <= 0.85:
            return 1.0
        return max(0.0, 1.0 - (soil_pct - 0.85) / 0.15)

    def update_soil_moisture(self, rainfall: float, day: int) -> dict:
        rainfall = max(0.0, rainfall)
        self.runoff = 0.0

        debug = {
            "rainfall": rainfall,
            "groundwater_uptake": 0.0,
            "soil_input": 0.0,
            "groundwater_input": 0.0,
            "runoff_input": 0.0,
            "percolation": 0.0,
            "overflow": 0.0,
            "actual_et": 0.0,
            "groundwater_outflow": 0.0,
            "runoff": 0.0,
            "soil_moisture": self.soil_moisture,
            "water_table": self.water_table,
        }

        if not self.hydrology_enabled:
            self.runoff = rainfall
            debug["runoff"] = self.runoff
            return debug

        groundwater_uptake = 0.0
        if self.soil_moisture < self.soil_capacity and self.water_table > 0.0:
            available_soil_space = self.soil_capacity - self.soil_moisture
            groundwater_uptake = min(
                self.water_table * 0.01,
                available_soil_space,
            )

        self.soil_moisture += groundwater_uptake
        self.water_table -= groundwater_uptake
        debug["groundwater_uptake"] = groundwater_uptake

        soil_input = rainfall * self.soil_fraction
        groundwater_input = rainfall * self.groundwater_fraction
        runoff_input = rainfall * self.runoff_fraction

        self.soil_moisture += soil_input
        self.water_table += groundwater_input
        self.runoff += runoff_input

        debug["soil_input"] = soil_input
        debug["groundwater_input"] = groundwater_input
        debug["runoff_input"] = runoff_input

        percolation = self.soil_moisture * 0.01
        self.soil_moisture -= percolation
        self.water_table += percolation
        debug["percolation"] = percolation

        over_capacity = max(self.soil_moisture - self.soil_capacity, 0.0)
        if over_capacity > 0.0:
            self.soil_moisture = self.soil_capacity
            debug["overflow"] = over_capacity

            non_soil_fraction = self.groundwater_fraction + self.runoff_fraction
            if non_soil_fraction > 0.0:
                overflow_groundwater_share = self.groundwater_fraction / non_soil_fraction
                overflow_runoff_share = self.runoff_fraction / non_soil_fraction
            else:
                overflow_groundwater_share = 0.0
                overflow_runoff_share = 1.0

            self.water_table += over_capacity * overflow_groundwater_share
            self.runoff += over_capacity * overflow_runoff_share

        effective_temperature = (
                self.temperature
                + Climate.seasonal_oscillator(day) * self.temperature_swing
        )
        temperature_mod = max(0.25, effective_temperature / 65.0)
        soil_stress = min(1.0, self.soil_moisture / (self.soil_capacity * 0.5))

        actual_et = self.evapotranspiration * temperature_mod * soil_stress
        self.soil_moisture -= actual_et
        self.annual_et_loss += actual_et
        self.soil_moisture = max(0.0, self.soil_moisture)
        debug["actual_et"] = actual_et

        groundwater_outflow = self.water_table * self.groundwater_discharge
        self.water_table -= groundwater_outflow
        self.runoff += groundwater_outflow
        self.annual_groundwater_loss += groundwater_outflow

        self.water_table = max(0.0, self.water_table)
        self.runoff = max(0.0, self.runoff)
        self.annual_runoff += self.runoff

        debug["groundwater_outflow"] = groundwater_outflow
        debug["runoff"] = self.runoff
        debug["soil_moisture"] = self.soil_moisture
        debug["soil_percent_full"] = self.soil_percent_full()
        debug["water_table"] = self.water_table

        return debug

    def daily_agricultural_yield(self) -> tuple[float, dict]:
        weather_mod = self.weather_yield_modifier()
        soil_mod = self.soil_yield_modifier()
        flood_severity = self.flood_severity()

        base_yield = (
                1.0
                * self.ag_yield_modifier
                * weather_mod
                * soil_mod
        )

        self.flood_damage += flood_severity * (1 - self.flood_damage)

        debug = {
            "weather_yield_modifier": weather_mod,
            "soil_yield_modifier": soil_mod,
            "flood_severity": flood_severity,
            "flood_damage": self.flood_damage,
            "daily_ag_yield": base_yield,
        }

        return base_yield, debug


    def update_humidity(self, day_counter: int):
        self.humidity += Climate.global_oscillator(day_counter) * 0.01
        self.humidity += Climate.seasonal_oscillator(day_counter) * 0.02
        self.humidity += random.gauss(0, 0.01)

        self.humidity += (0.5 - self.humidity) * 0.01
        drought_modifier = self.drought_index()
        drought_modifier = min(max(0.5, drought_modifier), 1.5)
        self.humidity += self.evapotranspiration * drought_modifier * 0.1

        self.humidity = min(max(0.0, self.humidity), 1.0)
        self.annual_average_humidity += self.humidity

    def rainfall(self) -> float:
        daily_rainfall = self.humidity * self.rainfall_multiplier
        daily_rainfall *= random.uniform(0.8, 1.2)

        storm_severity: tuple[float, str] = random.choices(
            [
                (0.75, "drizzle"),
                (4.0, "rain"),
                (8.0, "heavy"),
                (12.0, "storm"),
            ],
            weights=[5, 40, 40, 15],
            k=1,
        )[0]

        daily_rainfall *= storm_severity[0]
        self.annual_rainfall += daily_rainfall
        self.rain_events.append((storm_severity[1], daily_rainfall))

        return daily_rainfall

    def update_agriculture(self) -> dict:
        daily_yield, debug = self.daily_agricultural_yield()
        self.update_drought_status(daily_yield)
        self.ag_points += daily_yield
        debug["ag_points"] = self.ag_points
        return debug

    def harvest(self):
        biomass = self.ag_points
        return biomass * (1 - self.flood_damage)

    def weather_yield_modifier(self) -> float:
        if self.weather_machine.current_state == WeatherType.Cloudy:
            return 0.8
        if self.weather_machine.current_state == WeatherType.Rain:
            return 0.2
        return 1.0

    def update_drought_status(self, daily_yield):
        yield_fraction = daily_yield / self.harvest_threshold
        if yield_fraction < 0.1:
            self.drought = DroughtLevels.SevereDrought
        elif yield_fraction < 0.35:
            self.drought = DroughtLevels.Drought
        elif yield_fraction < 0.50:
            self.drought = DroughtLevels.Dry
        else:
            self.drought = DroughtLevels.Normal

