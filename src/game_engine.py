from src.biome import BiomeEnum, Biome, BIOMES
from src.climate import Climate
from src.game_weather_state_machine import GameWeatherStateMachine, WeatherType, DEFAULT_WEATHER


class GameEngine:
    def __init__(self, annual_days: int = 112):
        self.biomes: list[Biome] = []
        self.climate = Climate(annual_days)
        self.tick_count = 0

    def initialize(self) -> None:
        for biome_def in BIOMES:
            b = Biome()
            b.from_json(BIOMES[biome_def])
            w = GameWeatherStateMachine(biome_def)
            b.weather_machine = w
            self.biomes.append(b)

    def tick(self) -> None:
        for biome in self.biomes:
            if biome.weather_machine.current_state != WeatherType.Rain:
                self.climate.update_humidity(self.tick_count)
            biome.weather_machine.current_state = biome.weather_machine.transition(DEFAULT_WEATHER, self.biome.humidity)