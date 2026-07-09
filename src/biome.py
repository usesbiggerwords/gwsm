import random
from enum import StrEnum

from src.climate import Climate
from src.game_weather_state_machine import GameWeatherStateMachine


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
        "temperature": 30,
        "humidity": 0.5,
        "evaporation_rate": 0.05,
        "soil_moisture": 0.1,
        "soil_capacity": 1.0,
        "infiltration_rate": 0.1,
        "runoff_rate": 0.1,
        "crop_water_use": 0.05,
        "rainfall_multiplier": 0.1,
    },
    BiomeEnum.Forest: {
        "name": BiomeEnum.Forest,
        "temperature": 25,
        "humidity": 0.6,
        "evaporation_rate": 0.08,
        "soil_moisture": 0.12,
        "soil_capacity": 1.0,
        "infiltration_rate": 0.2,
        "runoff_rate": 0.05,
        "crop_water_use": 0.15,
        "rainfall_multiplier": 0.12,
    },
    BiomeEnum.Coast: {
        "name": BiomeEnum.Coast,
        "temperature": 30,
        "humidity": 0.6,
        "evaporation_rate": 0.2,
        "soil_moisture": 0.1,
        "soil_capacity": 1.0,
        "infiltration_rate": 0.3,
        "runoff_rate": 0.2,
        "crop_water_use": 0.1,
        "rainfall_multiplier": 0.3,
    },
    BiomeEnum.Desert: {
        "name": BiomeEnum.Desert,
        "temperature": 35,
        "humidity": 0.1,
        "evaporation_rate": 0.5,
        "soil_moisture": 0.02,
        "soil_capacity": 0.2,
        "infiltration_rate": 0.4,
        "runoff_rate": 0.3,
        "crop_water_use": 0.05,
        "rainfall_multiplier": 0.05,
    },
    BiomeEnum.Hills: {
        "name": BiomeEnum.Hills,
        "temperature": 20,
        "humidity": 0.6,
        "evaporation_rate": 0.1,
        "soil_moisture": 0.2,
        "soil_capacity": 1.0,
        "infiltration_rate": 0.1,
        "runoff_rate": 0.4,
        "crop_water_use": 0.15,
        "rainfall_multiplier": 0.2,
    },
    BiomeEnum.Mountains: {
        "name": BiomeEnum.Mountains,
        "temperature": 10,
        "humidity": 0.2,
        "evaporation_rate": 0.02,
        "soil_moisture": 0.02,
        "soil_capacity": 0.1,
        "infiltration_rate": 0.01,
        "runoff_rate": 0.8,
        "crop_water_use": 0.0,
        "rainfall_multiplier": 0.4,
    },
    BiomeEnum.Ocean: {
        "name": BiomeEnum.Ocean,
        "temperature": 30,
        "humidity": 0.9,
        "evaporation_rate": 0.8,
        "soil_moisture": 0.0,
        "soil_capacity": 10.0,
        "infiltration_rate": 1.0,
        "runoff_rate": 0.0,
        "crop_water_use": 0.0,
        "rainfall_multiplier": 0.9,
    }
}

class Biome:
    def __init__(self):
        self.name: BiomeEnum = BiomeEnum.Null
        self.temperature: float = 0.0
        self.humidity: float = 0.0
        self.evaporation_rate: float = 0.0
        self.soil_moisture: float = 0.0
        self.soil_capacity: float = 0.0
        self.infiltration_rate: float = 0.0
        self.runoff_rate: float = 0.0
        self.runoff: float = 0.0
        self.crop_water_use: float = 0.0
        self.rainfall_multiplier: float = 0.0
        self.rain_events: list[tuple[str, float]] = []
        self.annual_rainfall: float = 0.0
        self.water_table: float = 0.0
        self.weather_machine: GameWeatherStateMachine = None

    def report(self):
        parts = [f"{k}: {v}\n" for k, v in self.__dict__.items() if v is not None]
        return "".join(parts)

    def from_json(self, json_obj):
        self.name = json_obj["name"]
        self.temperature = json_obj["temperature"]
        self.humidity = json_obj["humidity"]
        self.evaporation_rate = json_obj["evaporation_rate"]
        self.soil_moisture = json_obj["soil_moisture"]
        self.soil_capacity = json_obj["soil_capacity"]
        self.infiltration_rate = json_obj["infiltration_rate"]
        self.runoff_rate = json_obj["runoff_rate"]
        self.crop_water_use = json_obj["crop_water_use"]
        self.rainfall_multiplier = json_obj["rainfall_multiplier"]

    def to_json(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if v is not None}

    def to_minimal_json(self) -> dict:
        result = {
            "name": self.name,
            "temperature": self.temperature,
            "humidity": self.humidity,
            "runoff": self.runoff,
            "soil_moisture": self.soil_moisture,
            "annual_rainfall": self.annual_rainfall,
            "water_table": self.water_table,
        }
        return result

    def update_soil_moisture(self, rainfall: float):
        groundwater_uptake = 0.0
        if self.soil_moisture < self.water_table:
            groundwater_uptake = self.water_table * 0.1
        self.soil_moisture += groundwater_uptake
        self.water_table -= groundwater_uptake
        self.soil_moisture += rainfall
        over_capacity = max(self.soil_moisture - self.soil_capacity, 0.0)
        self.soil_moisture = min(self.soil_moisture, self.soil_capacity)
        self.soil_moisture -= self.evaporation_rate
        self.soil_moisture -= self.crop_water_use
        self.soil_moisture = max(0.0, self.soil_moisture)
        self.water_table += over_capacity * 0.5
        self.water_table = max(0.0, self.water_table)
        self.runoff = (over_capacity * 0.5) * self.runoff_rate

    def update_humidity(self, day_counter: int):
        self.humidity += (Climate.global_oscillator(day_counter) * 0.01)
        self.humidity += (Climate.seasonal_oscillator(day_counter) * 0.02)
        self.humidity += random.gauss(0, 0.01)
        self.humidity = max(0.0, self.humidity)

    def rainfall(self) -> float:
        daily_rainfall = self.humidity * random.uniform(0.8, 1.2)
        storm_severity: tuple[float, str] = random.choices(
            [
                (0.25, "drizzle"),
                (1.0, "rain"),
                (3.0, "heavy"),
                (6.0, "storm"),
            ],
            weights=[10, 40, 35, 15],
            k=1
        )[0]
        daily_rainfall *= storm_severity[0]
        self.annual_rainfall += daily_rainfall
        self.rain_events.append((storm_severity[1], daily_rainfall))
        return daily_rainfall

