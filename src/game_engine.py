import csv
from dataclasses import asdict
from pathlib import Path
from rich.table import Table
from rich.console import Console

from src.biome2 import Biome, BIOMES, DailyBiomeStats
# from src.biome import Biome, BIOMES, DailyBiomeStats
from src.climate import Climate
from src.climate_plots import plot_biome_dashboards
from src.game_weather_state_machine import GameWeatherStateMachine, WeatherType, DEFAULT_WEATHER


class GameEngine:
    def __init__(self, annual_days: int = 112):
        # self.biomes: list[Biome] = []
        self.climate = Climate()
        self.biomes: list[Biome] = []
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
            rain = 0.0
            biome.update_temperature(self.tick_count)
            biome.update_relative_humidity(self.tick_count)
            biome.update_et(self.tick_count)
            biome.update_agriculture()
            # if biome.weather.current_state != WeatherType.Rain:
                # biome.update_humidity(self.tick_count)
            biome.weather.transition(DEFAULT_WEATHER, biome.relative_humidity)
            if biome.weather.current_state == WeatherType.Rain:
                biome.rainfall(self.tick_count)
                # hydro_debug = biome.update_soil_moisture(rain, self.tick_count)
            # else:
            #     hydro_debug = biome.update_soil_moisture(rain, self.tick_count)
            # ag_debug = biome.update_agriculture()
            biome.daily_stats.append(
                DailyBiomeStats(
                    tick=self.tick_count,
                    year=self.tick_count // self.year_length + 1,
                    day_of_year=self.tick_count % self.year_length,
                    temperature=biome.temperature,
                    weather=str(biome.weather.current_state),
                    relative_humidity=biome.relative_humidity,
                    available_water=biome.available_water,
                    agriculture=biome.agriculture
                )
            )
        self.tick_count += 1

    # def tick(self) -> None:
    #     for biome in self.biomes:
    #         rain = 0.0
    #         if biome.weather_machine.current_state != WeatherType.Rain:
    #             biome.update_humidity(self.tick_count)
    #         biome.weather_machine.transition(DEFAULT_WEATHER, biome.humidity)
    #         if biome.weather_machine.current_state == WeatherType.Rain:
    #             rain = biome.rainfall()
    #             hydro_debug = biome.update_soil_moisture(rain, self.tick_count)
    #             biome.humidity = 0.0
    #         else:
    #             hydro_debug = biome.update_soil_moisture(rain, self.tick_count)
    #         ag_debug = biome.update_agriculture()
    #         biome.daily_stats.append(
    #             DailyBiomeStats(
    #                 tick=self.tick_count,
    #                 year=self.tick_count // self.year_length + 1,
    #                 day_of_year=self.tick_count % self.year_length,
    #
    #                 weather=str(biome.weather_machine.current_state),
    #                 humidity=biome.humidity,
    #                 rainfall=rain,
    #
    #                 soil_moisture=biome.soil_moisture,
    #                 soil_percent_full=biome.soil_percent_full(),
    #                 water_table=biome.water_table,
    #                 runoff=biome.runoff,
    #
    #                 groundwater_uptake=hydro_debug["groundwater_uptake"],
    #                 percolation=hydro_debug["percolation"],
    #                 groundwater_outflow=hydro_debug["groundwater_outflow"],
    #                 et_loss=hydro_debug["actual_et"],
    #
    #                 flood_severity=ag_debug["flood_severity"],
    #                 flood_damage=ag_debug["flood_damage"],
    #
    #                 soil_yield_modifier=ag_debug["soil_yield_modifier"],
    #                 weather_yield_modifier=ag_debug["weather_yield_modifier"],
    #                 daily_ag_yield=ag_debug["daily_ag_yield"],
    #                 ag_points=ag_debug["ag_points"],
    #             )
    #         )
    #     self.tick_count += 1

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

    def export_daily_stats(self, output_path: Path) -> None:
        rows = []
        for biome in self.biomes:
            for stat in biome.daily_stats:
                row = asdict(stat)
                row["biome"] = biome.name
                rows.append(row)

        if not rows:
            return

        with output_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)

    def rich_status(self, year: int):
        table = Table(title=f"Year {year} Climate Status")
        table.add_column("Biome")
        table.add_column("Rain, in")
        table.add_column("Drought")
        table.add_column("Runoff, in")
        table.add_column("Flood damage: %")
        table.add_column("Ag Yield, lbs")

        for biome in self.biomes:
            table.add_row(
                biome.name,
                f"{biome.annual_rainfall:.2f}",
                f"{biome.drought_status()}",
                f"{biome.annual_runoff:.2f}",
                f"{biome.flood_damage:.2f}",
                f"{biome.annual_ag_yield:.2f}"
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
                for biome in self.biomes:
                    biome.annual_ag_yield = biome.harvest()
                # self.rich_status(self.tick_count // self.year_length)
                # reset annual totals
                # for biome in self.biomes:
                #     biome.record_yearly_stats(self.tick_count)
                # self.print_yearly_climate_status(self.tick_count // self.year_length, self.biomes)
                for biome in self.biomes:
                    biome.reset_annual_counters(self.tick_count)
            if self.tick_count > (self.year_length * 500):
                break
        saved_plot_paths = self.plot_climate_history()
        for plot_path in saved_plot_paths:
            print(f"Saved climate plot: {plot_path}")
        self.export_daily_stats(Path(__file__).parent / "daily_stats.csv")
        self.export_annual_stats(Path(__file__).parent / "annual_stats.csv")

    def export_annual_stats(self, output_path: Path) -> None:
        rows = []
        for biome in self.biomes:
            for stat in biome.annual_stats:
                row = asdict(stat)
                row["biome"] = biome.name
                rows.append(row)

        if not rows:
            return

        with output_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)


if __name__ == "__main__":
    engine = GameEngine()
    engine.run()
