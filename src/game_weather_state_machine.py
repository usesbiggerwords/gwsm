import random
from enum import StrEnum


class WeatherType(StrEnum):
    Clear = "clear"
    Cloudy = "cloudy"
    Rain = "rain"
    Snow = "snow"


DEFAULT_WEATHER = {
    WeatherType.Clear: {
        WeatherType.Cloudy: 0.35,
        WeatherType.Rain: 0.05,
        WeatherType.Clear: 0.6,
    },
    WeatherType.Cloudy: {
        WeatherType.Cloudy: 0.25,
        WeatherType.Rain: 0.50,
        WeatherType.Clear: 0.25,
    },
    WeatherType.Rain: {
        WeatherType.Cloudy: 0.35,
        WeatherType.Rain: 0.1,
        WeatherType.Clear: 0.55,
    }
}

class WeatherTracker:
    def __init__(self):
        self.daily_weather: list[WeatherType] = []
        self.rain_events: list[float] = []

    def total_rainfall(self) -> float:
        return sum(self.rain_events)


class GameWeatherStateMachine:
    def __init__(self, initial_state: WeatherType = WeatherType.Clear):
        self.states: list[str] = []
        self.transitions: dict[str, dict] = {}
        self.current_state: WeatherType = initial_state

    def __repr__(self):
        return f"<GameWeatherStateMachine: {self.current_state}>"

    def __str__(self):
        return f"<GameWeatherStateMachine: {self.current_state}>"

    def transition(self, markov_chain: dict[str, dict], humidity: float):
        try:
            transitions = markov_chain[self.current_state]
        except KeyError as e:
            print(self.current_state)
            raise e

        states = list(transitions.keys())
        weights = list(transitions.values())

        next_state = random.choices(states, weights=weights, k=1)[0]
        if next_state is None:
            print(next_state)
        if next_state == WeatherType.Clear and humidity > 1.0:
            next_state = WeatherType.Rain
        self.states.append(next_state)
        self.current_state = next_state


# weather = GameWeatherStateMachine(BiomeEnum.Plains, initial_state='clear')
# annual_days = 112  # 4 months of 28 days each
# climate = Climate(annual_days)
# for year in range(55):
#     for day_number in range(annual_days):
#         if weather.current_state != WeatherType.Rain:
#             climate.update_humidity(day_number)
#         weather.current_state = weather.transition(DEFAULT_WEATHER, climate.humidity)
#         if weather.current_state == "rainy":
#             daily_rainfall = climate.rainfall()
#             climate.humidity = 0.0
#         time.sleep(0.1)
