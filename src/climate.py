import math


class Climate:

    days_in_year: int
    # humidity: float = random.random()

    @classmethod
    def initialize(cls, days_in_year: int):
        cls.days_in_year = days_in_year
        # cls.humidity = humidity

    @classmethod
    def global_oscillator(cls, day_counter: int) -> float:
        """
        Cycles on an 11-year cycle, with actual days depending on the scenario
        :param day_counter:
        :return:
        """
        return 0.5 * math.sin((2 * math.pi / (cls.days_in_year * 11)) * day_counter) + 0.5

    @classmethod
    def seasonal_oscillator(cls, day_counter: int) -> float:
        """
        Annual fluctuation with spring and autumn as the maxima
        :param day_counter:
        :return:
        """
        return math.sin(((math.pi / (cls.days_in_year / 2)) * day_counter) + (math.pi / 4)) ** 2

    # def update_humidity(self, day_counter: int):
    #     self.humidity += (self.global_oscillator(day_counter) * 0.01)
    #     self.humidity += (self.seasonal_oscillator(day_counter) * 0.02)
    #     self.humidity += random.gauss(0, 0.01)
    #
    # def rainfall(self) -> float:
    #     return self.humidity * random.uniform(0.8, 1.2)


# if __name__ == "__main__":
#     # for cycles in range(50):
#     for year in range(55):
#         climate = Climate(112)
#         rain_events = []
#         annual_rainfall = 0
#         for day_counter in range(112):
#             climate.update_humidity(day_counter)
#             if climate.humidity > 1.0:
#                 daily_rainfall = climate.rainfall()
#                 annual_rainfall += daily_rainfall
#                 rain_events.append((day_counter, daily_rainfall))
#                 climate.humidity = 0.0
#             # print(f"humidity: {climate.humidity}")
#         days_between_rain_events = [rain_events[i][0] - rain_events[i - 1][0] for i in range(1, len(rain_events))]
#         print(f"Year {year}, rainfall {annual_rainfall}")
