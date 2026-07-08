import random
from enum import StrEnum

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
        "evaporation_rate": 0.1,
        "soil_moisture": 0.1,
        "infiltration_rate": 0.1,
        "runoff_rate": 0.1,
        "crop_water_use": 0.1,
        "rainfall_multiplier": 0.1,
    },
    BiomeEnum.Forest: {
        "name": BiomeEnum.Forest,
        "temperature": 25,
        "humidity": 0.6,
        "evaporation_rate": 0.08,
        "soil_moisture": 0.12,
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
        self.infiltration_rate: float = 0.0
        self.runoff_rate: float = 0.0
        self.crop_water_use: float = 0.0
        self.rainfall_multiplier: float = 0.0
        self.weather_machine: GameWeatherStateMachine = None

    def from_json(self, json_obj):
        self.name = json_obj["name"]
        self.temperature = json_obj["temperature"]
        self.humidity = json_obj["humidity"]
        self.evaporation_rate = json_obj["evaporation_rate"]
        self.soil_moisture = json_obj["soil_moisture"]
        self.infiltration_rate = json_obj["infiltration_rate"]
        self.runoff_rate = json_obj["runoff_rate"]
        self.crop_water_use = json_obj["crop_water_use"]
        self.rainfall_multiplier = json_obj["rainfall_multiplier"]

    def to_json(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if v is not None}

    def update_soil_moisture(self, rainfall: float):
        self.soil_moisture = rainfall * self.infiltration_rate
        self.soil_moisture -= self.evaporation_rate
        self.soil_moisture -= self.crop_water_use

    def update_humidity(self, day_counter: int):
        self.humidity += (self.cl.global_oscillator(day_counter) * 0.01)
        self.humidity += (self.seasonal_oscillator(day_counter) * 0.02)
        self.humidity += random.gauss(0, 0.01)

    def rainfall(self) -> float:
        return self.humidity * random.uniform(0.8, 1.2)

