from pathlib import Path

from src.biome import Biome, BIOMES
from src.climate import Climate
from src.game_weather_state_machine import GameWeatherStateMachine, WeatherType, DEFAULT_WEATHER


class GameEngine:
    def __init__(self, annual_days: int = 112):
        self.biomes: list[Biome] = []
        self.climate = Climate()
        self.climate.initialize(annual_days)
        self.tick_count = 0
        self.log_file: Path = Path(__file__).parent / "results.log"

    def initialize(self) -> None:
        for biome_def in BIOMES:
            b = Biome()
            b.from_json(BIOMES[biome_def])
            w = GameWeatherStateMachine()
            b.weather_machine = w
            self.biomes.append(b)

    def tick(self) -> None:
        for biome in self.biomes:
            if biome.weather_machine.current_state != WeatherType.Rain:
                biome.update_humidity(self.tick_count)
            biome.weather_machine.transition(DEFAULT_WEATHER, biome.humidity)
            if biome.weather_machine.current_state == WeatherType.Rain:
                rain = biome.rainfall()
                biome.update_soil_moisture(rain)
                biome.humidity = 0.0
        self.tick_count += 1

    def status(self):
        for biome in self.biomes:
            # print(biome.report())
            with self.log_file.open(mode="a", encoding="utf-8") as f:
                f.write(f"{biome.to_minimal_json()}\n")



    def run(self):
        self.initialize()
        while True:
            self.tick()
            self.status()
            if self.tick_count > (112 * 22):
                break


if __name__ == "__main__":
    engine = GameEngine()
    engine.run()
