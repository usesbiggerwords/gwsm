import random
import time

DEFAULT_WEATHER = {
    "clear": {
        "cloudy": 0.35,
        "rainy": 0.05,
        "clear": 0.5,
    },
    "cloudy": {
        "cloudy": 0.25,
        "rainy": 0.50,
        "clear": 0.25,
    },
    "rainy": {
        "cloudy": 0.35,
        "rainy": 0.1,
        "clear": 0.55,
    }
}

class GameWeatherStateMachine:
    def __init__(self, initial_state: str = 'clear'):
        self.states: list[str] = []
        self.transitions: dict[str, dict] = {}
        self.current_state: str = initial_state

    def transition(self, markov_chain: dict[str, dict], humidity: float) -> str:
        transitions = markov_chain[self.current_state]

        states = list(transitions.keys())
        weights = list(transitions.values())

        next_state = random.choices(states, weights=weights, k=1)[0]
        if next_state == "clear" and humidity > 1.0:
            next_state = "rainy"
        self.states.append(next_state)
        return next_state


weather = GameWeatherStateMachine()
humidity = random.random()
for i in range(100):
    print(weather.current_state, humidity)
    print(DEFAULT_WEATHER.get(weather.current_state))
    weather.current_state = weather.transition(DEFAULT_WEATHER, humidity)
    if weather.current_state == "rainy":
        humidity = 0.0
    else:
        humidity += random.random() * 0.1
    time.sleep(0.1)
