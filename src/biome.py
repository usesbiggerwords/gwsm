import random
from dataclasses import dataclass, field
from enum import StrEnum

from src.climate import Climate
from src.game_weather_state_machine import GameWeatherStateMachine


@dataclass
class YearlyBiomeStats:
    year: int
    rainfall: float
    rain_events: int
    soil_moisture: float
    et_loss: float
    groundwater_loss: float
    water_table: float
    water_balance: float
    runoff: float


class BiomeEnum(StrEnum):
    Plains = "plains"
    Forest = "forest"
    Coast = "coast"
    Desert = "desert"
    Hills = "hills"
    Mountains = "mountains"
    Null = "null"
    Ocean = "ocean"


BIOMES = {
    BiomeEnum.Plains: {
        "name": BiomeEnum.Plains,
        "temperature": 80,
        "humidity": 0.5,
        "evapotranspiration": 0.055,
        "soil_moisture": 6.0,
        "soil_capacity": 10.0,

        # Percentages: 55% soil, 20% groundwater, 25% runoff.
        "soil_percent": 55.0,
        "groundwater_percent": 20.0,
        "runoff_percent": 25.0,

        # Fraction of groundwater lost each tick as baseflow/deep drainage.
        "groundwater_discharge": 0.018,

        "rainfall_multiplier": 1.0,
        "hydrology_enabled": True,
    },

    BiomeEnum.Forest: {
        "name": BiomeEnum.Forest,
        "temperature": 70,
        "humidity": 0.6,
        "evapotranspiration": 0.075,
        "soil_moisture": 8.0,
        "soil_capacity": 14.0,

        # Forest: high soil retention, moderate groundwater, low runoff.
        "soil_percent": 70.0,
        "groundwater_percent": 20.0,
        "runoff_percent": 10.0,

        "groundwater_discharge": 0.015,

        "rainfall_multiplier": 1.15,
        "hydrology_enabled": True,
    },

    BiomeEnum.Coast: {
        "name": BiomeEnum.Coast,
        "temperature": 85,
        "humidity": 0.6,
        "evapotranspiration": 0.060,
        "soil_moisture": 7.0,
        "soil_capacity": 10.0,

        # Coast: retains some soil water, recharges groundwater, sheds some runoff.
        "soil_percent": 55.0,
        "groundwater_percent": 30.0,
        "runoff_percent": 15.0,

        "groundwater_discharge": 0.020,

        "rainfall_multiplier": 1.25,
        "hydrology_enabled": True,
    },

    BiomeEnum.Desert: {
        "name": BiomeEnum.Desert,
        "temperature": 95,
        "humidity": 0.1,
        "evapotranspiration": 0.50,
        "soil_moisture": 1.0,
        "soil_capacity": 3.0,

        # Desert: most rain becomes flash-flood runoff.
        "soil_percent": 8.0,
        "groundwater_percent": 4.0,
        "runoff_percent": 88.0,

        "groundwater_discharge": 0.030,

        "rainfall_multiplier": 0.45,
        "hydrology_enabled": True,
    },

    BiomeEnum.Hills: {
        "name": BiomeEnum.Hills,
        "temperature": 65,
        "humidity": 0.4,
        "evapotranspiration": 0.105,
        "soil_moisture": 5.0,
        "soil_capacity": 9.0,

        # Hills: decent soil retention, but a lot runs off.
        "soil_percent": 35.0,
        "groundwater_percent": 15.0,
        "runoff_percent": 50.0,

        "groundwater_discharge": 0.025,

        "rainfall_multiplier": 1.30,
        "hydrology_enabled": True,
    },

    BiomeEnum.Mountains: {
        "name": BiomeEnum.Mountains,
        "temperature": 40,
        "humidity": 0.2,
        "evapotranspiration": 0.020,
        "soil_moisture": 2.0,
        "soil_capacity": 3.0,

        # Mountains: thin rocky soil; most precipitation becomes runoff.
        # Some becomes groundwater, but groundwater discharges quickly as springs/headwaters.
        "soil_percent": 10.0,
        "groundwater_percent": 20.0,
        "runoff_percent": 70.0,

        "groundwater_discharge": 0.070,

        "rainfall_multiplier": 1.80,
        "hydrology_enabled": True,
    },

    BiomeEnum.Ocean: {
        "name": BiomeEnum.Ocean,
        "temperature": 70,
        "humidity": 0.9,
        "evapotranspiration": 0.0,
        "soil_moisture": 0.0,
        "soil_capacity": 0.0,

        # Ocean bypasses land hydrology. Rainfall is effectively surface water.
        "soil_percent": 0.0,
        "groundwater_percent": 0.0,
        "runoff_percent": 100.0,

        "groundwater_discharge": 0.0,

        "rainfall_multiplier": 1.0,
        "hydrology_enabled": False,
    },
}


def rolling_average(values: list[float], window: int = 5) -> float:
    if not values:
        return 0.0

    sample = values[-window:]
    return sum(sample) / len(sample)


class Biome:

    def __init__(self):
        self.annual_runoff: float = 0.0
        self.name: BiomeEnum = BiomeEnum.Null

        self.temperature: float = 0.0
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
        # Annual totals
        self.annual_rainfall: float = 0.0
        self.annual_et_loss: float = 0.0
        self.annual_groundwater_loss: float = 0.0
        self.annual_history: list[YearlyBiomeStats] = []
        self.water_table: float = 0.0

        self.weather_machine: GameWeatherStateMachine | None = None

    def report(self):
        parts = [f"{k}: {v}\n" for k, v in self.__dict__.items() if v is not None]
        return "".join(parts)

    def from_json(self, json_obj):
        self.name = json_obj["name"]

        self.temperature = json_obj["temperature"]
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
        index = self.drought_index()

        if index < 0.10:
            return "extreme drought"
        if index < 0.25:
            return "severe drought"
        if index < 0.50:
            return "drought"
        if index < 0.75:
            return "dry"
        if index <= 1.15:
            return "normal"
        if index <= 1.50:
            return "wet"

        return "saturated"

    def update_soil_moisture(self, rainfall: float):
        """
        Update biome hydrology.

        Recommended usage:
            Call this every tick.
            Pass rainfall=0.0 on non-rain days.

        Rainfall is partitioned by percentages into:
            - soil moisture
            - groundwater recharge
            - runoff

        Excess soil water above capacity is repartitioned into groundwater/runoff.
        Groundwater discharge becomes runoff/baseflow.
        """
        rainfall = max(0.0, rainfall)
        self.runoff = 0.0

        if not self.hydrology_enabled:
            self.runoff = rainfall
            return

        # Existing groundwater can wick upward into unsaturated soil.
        groundwater_uptake = 0.0

        if self.soil_moisture < self.soil_capacity and self.water_table > 0.0:
            available_soil_space = self.soil_capacity - self.soil_moisture
            groundwater_uptake = min(
                self.water_table * 0.1,
                available_soil_space,
            )

        self.soil_moisture += groundwater_uptake
        self.water_table -= groundwater_uptake

        # Direct rainfall partitioning.
        soil_input = rainfall * self.soil_fraction
        groundwater_input = rainfall * self.groundwater_fraction
        runoff_input = rainfall * self.runoff_fraction

        self.soil_moisture += soil_input
        self.water_table += groundwater_input
        self.runoff += runoff_input

        # If soil exceeds capacity, move excess into groundwater/runoff.
        over_capacity = max(self.soil_moisture - self.soil_capacity, 0.0)

        if over_capacity > 0.0:
            self.soil_moisture = self.soil_capacity

            non_soil_fraction = self.groundwater_fraction + self.runoff_fraction

            if non_soil_fraction > 0.0:
                overflow_groundwater_share = (
                    self.groundwater_fraction / non_soil_fraction
                )
                overflow_runoff_share = self.runoff_fraction / non_soil_fraction
            else:
                overflow_groundwater_share = 0.0
                overflow_runoff_share = 1.0

            self.water_table += over_capacity * overflow_groundwater_share
            self.runoff += over_capacity * overflow_runoff_share

        # Evapotranspiration loss from soil.
        self.soil_moisture -= self.evapotranspiration
        self.annual_et_loss += self.evapotranspiration
        self.soil_moisture = max(0.0, self.soil_moisture)

        # Groundwater discharge becomes baseflow/runoff.
        groundwater_outflow = self.water_table * self.groundwater_discharge
        self.water_table -= groundwater_outflow
        self.runoff += groundwater_outflow
        self.annual_groundwater_loss += groundwater_outflow

        self.water_table = max(0.0, self.water_table)
        self.runoff = max(0.0, self.runoff)
        self.annual_runoff += self.runoff

    def update_humidity(self, day_counter: int):
        self.humidity += Climate.global_oscillator(day_counter) * 0.01
        self.humidity += Climate.seasonal_oscillator(day_counter) * 0.02
        self.humidity += random.gauss(0, 0.01)

        self.humidity = max(0.0, self.humidity)

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
