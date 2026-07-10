from pathlib import Path
from rich.table import Table
from rich.console import Console

from src.biome import Biome, BIOMES
from src.climate import Climate
from src.climate_plots import plot_biome_dashboards
from src.game_weather_state_machine import GameWeatherStateMachine, WeatherType, DEFAULT_WEATHER


class GameEngine:
    def __init__(self, annual_days: int = 112):
        self.biomes: list[Biome] = []
        self.climate = Climate()
        self.climate.initialize(annual_days)
        self.tick_count: int = 0
        self.year_length: int = annual_days
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
            else:
                biome.update_soil_moisture(0.0)
        self.tick_count += 1

    def print_yearly_climate_status(self, year: int, biomes: list[Biome]) -> None:
        table = Table(title=f"Year {year} Climate Status")

        table.add_column("Biome")
        # table.add_column("Rain")
        table.add_column("5Y Rain")
        # table.add_column("Events")
        table.add_column("5Y Events")
        # table.add_column("Soil")
        table.add_column("5Y Soil")
        # table.add_column("ET Loss")
        table.add_column("5Y ET")
        # table.add_column("Balance")
        table.add_column("5Y Balance")
        # table.add_column("Water Table")
        table.add_column("5Y WT")

        for biome in self.biomes:
            averages = biome.five_year_averages()

            current_balance = (
                    biome.annual_rainfall
                    - biome.annual_et_loss
                    - biome.annual_groundwater_loss
            )

            table.add_row(
                str(biome.name),
                # f"{biome.annual_rainfall:.2f}",
                f"{averages['rainfall']:.2f}",
                # f"{len(biome.rain_events):.0f}",
                f"{averages['rain_events']:.1f}",
                # f"{biome.soil_moisture:.2f}",
                f"{averages['soil_moisture']:.2f}",
                # f"{biome.annual_et_loss:.2f}",
                f"{averages['et_loss']:.2f}",
                # f"{current_balance:.2f}",
                f"{averages['water_balance']:.2f}",
                # f"{biome.water_table:.2f}",
                f"{averages['water_table']:.2f}",
            )

        console = Console()
        console.print(table)

    def rich_status(self, year: int):
        table = Table(title=f"Year {year} Climate Status")
        table.add_column("Biome")
        table.add_column("Rain Events")
        table.add_column("Rain, in")
        table.add_column("Soil, %full")
        table.add_column("ET Loss, in")
        table.add_column("Drought")
        table.add_column("Runoff, in")

        for biome in self.biomes:
            table.add_row(
                biome.name,
                f"{len(biome.rain_events):.2f}",
                f"{biome.annual_rainfall:.2f}",
                f"{biome.soil_percent_full():.2f}",
                f"{biome.annual_et_loss:.2f}",
                f"{biome.drought_status()}",
                f"{biome.annual_runoff:.2f}",
            )

        console = Console()
        console.print(table)

    def plot_climate_history(self, output_dir: Path | None = None, rolling_window: int = 5) -> list[Path]:
        """
        Generate climate dashboard plots for each biome.

        This assumes each Biome has annual_history populated with YearlyBiomeStats.
        Call this after the simulation run completes, or after each year if you want
        progressively updated images.
        """
        if output_dir is None:
            output_dir = Path(__file__).parent / "plots"

        return plot_biome_dashboards(
            biomes=self.biomes,
            output_dir=output_dir,
            rolling_window=rolling_window,
        )

    def status(self):
        for biome in self.biomes:
            # print(biome.report())
            with self.log_file.open(mode="a", encoding="utf-8") as f:
                f.write(f"{biome.to_minimal_json()}\n")



    def run(self):
        self.initialize()
        while True:
            self.tick()
            # self.status()
            if self.tick_count % self.year_length == 0:
                self.rich_status(self.tick_count // self.year_length)
                # reset annual totals
                for biome in self.biomes:
                    biome.record_yearly_stats(self.tick_count)
                self.print_yearly_climate_status(self.tick_count // self.year_length, self.biomes)
                for biome in self.biomes:
                    biome.reset_annual_counters()
            if self.tick_count > (self.year_length * 100):
                break
        saved_plot_paths = self.plot_climate_history()
        for plot_path in saved_plot_paths:
            print(f"Saved climate plot: {plot_path}")


if __name__ == "__main__":
    engine = GameEngine()
    engine.run()
