from __future__ import annotations

from pathlib import Path
from typing import Iterable, Any

import matplotlib.pyplot as plt


def rolling_average(values: list[float], window: int = 5) -> list[float]:
    """Return a simple trailing rolling average for each value."""
    if window <= 0:
        raise ValueError("rolling window must be greater than zero")

    averages: list[float] = []

    for index in range(len(values)):
        start = max(0, index - window + 1)
        sample = values[start:index + 1]
        averages.append(sum(sample) / len(sample))

    return averages


def _safe_biome_name(biome: Any) -> str:
    name = getattr(biome, "name", "biome")
    name_value = getattr(name, "value", str(name))
    return str(name_value).replace(" ", "_").lower()


def _history_to_series(biome: Any) -> dict[str, list[float]]:
    """
    Convert biome.annual_history into plot-friendly lists.

    Expects each history item to expose:
        year
        rainfall
        rain_events
        soil_moisture
        et_loss
        groundwater_loss
        water_table
        water_balance
        runoff

    This matches the YearlyBiomeStats dataclass in biome.py.
    """
    history = list(getattr(biome, "annual_history", []))

    soil_capacity = float(getattr(biome, "soil_capacity", 0.0) or 0.0)

    years: list[int] = []
    rainfall: list[float] = []
    rain_events: list[float] = []
    soil_percent: list[float] = []
    et_loss: list[float] = []
    groundwater_loss: list[float] = []
    water_table: list[float] = []
    water_balance: list[float] = []
    runoff: list[float] = []

    for stat in history:
        years.append(int(stat.year))
        rainfall.append(float(stat.available_water))
        rain_events.append(float(stat.rain_events))

        if soil_capacity > 0.0:
            soil_percent.append(
                max(0.0, min(100.0, (float(stat.soil_moisture) / soil_capacity) * 100.0))
            )
        else:
            soil_percent.append(0.0)

        et_loss.append(float(stat.et_loss))
        groundwater_loss.append(float(stat.groundwater_loss))
        water_table.append(float(stat.water_table))
        water_balance.append(float(stat.water_balance))
        runoff.append(float(stat.runoff))

    return {
        "years": years,
        "rainfall": rainfall,
        "rain_events": rain_events,
        "soil_percent": soil_percent,
        "et_loss": et_loss,
        "groundwater_loss": groundwater_loss,
        "water_table": water_table,
        "water_balance": water_balance,
        "runoff": runoff,
    }


def plot_biome_dashboard(
    biome: Any,
    output_dir: str | Path,
    rolling_window: int = 5,
    dpi: int = 160,
) -> Path | None:
    """
    Generate a 4-panel hydrology dashboard for one biome.

    Panels:
        1. annual rainfall + rolling average
        2. soil percent full + rolling average + drought guide lines
        3. water balance + rolling average
        4. runoff and water table

    Returns the saved PNG path. Returns None if there is no annual history.
    """
    data = _history_to_series(biome)

    years = data["years"]
    if not years:
        return None

    rainfall = data["rainfall"]
    soil_percent = data["soil_percent"]
    water_balance = data["water_balance"]
    runoff = data["runoff"]
    water_table = data["water_table"]

    rainfall_ma = rolling_average(rainfall, rolling_window)
    soil_ma = rolling_average(soil_percent, rolling_window)
    balance_ma = rolling_average(water_balance, rolling_window)
    runoff_ma = rolling_average(runoff, rolling_window)
    water_table_ma = rolling_average(water_table, rolling_window)

    biome_name = _safe_biome_name(biome)

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    file_path = output_path / f"{biome_name}_climate_dashboard.png"

    fig, axes = plt.subplots(
        4,
        1,
        figsize=(14, 12),
        sharex=True,
    )

    fig.suptitle(f"{biome_name.title()} Climate Dashboard", fontsize=16)

    # 1. Rainfall
    axes[0].bar(years, rainfall, color="lightblue", linewidth=1.5, alpha=0.25, label="Annual rainfall")
    axes[0].plot(years, rainfall_ma, color="blue", linewidth=3.0, label=f"{rolling_window}Y rainfall avg")
    axes[0].set_ylabel("Rainfall, in")
    axes[0].legend(loc="upper right")
    axes[0].grid(alpha=0.25)

    # 2. Soil moisture
    axes[1].plot(years, soil_percent, alpha=0.35, label="Soil % full")
    axes[1].plot(years, soil_ma, linewidth=2.5, label=f"{rolling_window}Y soil avg")
    axes[1].axhline(75, linestyle="--", linewidth=1.0, label="normal threshold")
    axes[1].axhline(50, linestyle="--", linewidth=1.0, label="dry threshold")
    axes[1].axhline(25, linestyle="--", linewidth=1.0, label="drought threshold")
    axes[1].axhspan(
        0,
        25,
        alpha=0.15,
        color="red"
    )

    axes[1].axhspan(
        25,
        50,
        alpha=0.10,
        color="orange"
    )

    axes[1].axhspan(
        50,
        75,
        alpha=0.05,
        color="yellow"
    )
    axes[1].set_ylabel("Soil, % full")
    axes[1].set_ylim(0, 105)
    axes[1].legend(loc="upper right")
    axes[1].grid(alpha=0.25)

    # 3. Water balance
    bar_colors = ["tab:green" if value >= 0 else "tab:red" for value in water_balance]
    axes[2].bar(years, water_balance, color=bar_colors, alpha=0.45, label="Annual balance")
    axes[2].plot(years, balance_ma, linewidth=2.5, color="black", label=f"{rolling_window}Y balance avg")
    axes[2].axhline(0, linestyle="--", linewidth=1.0, color="black")
    axes[2].set_ylabel("Balance, in")
    axes[2].legend(loc="upper right")
    axes[2].grid(alpha=0.25)

    # 4. Runoff and water table
    axes[3].plot(years, runoff, alpha=0.25, label="Annual runoff")
    axes[3].plot(years, runoff_ma, linewidth=2.5, label=f"{rolling_window}Y runoff avg")
    axes[3].plot(years, water_table, alpha=0.25, label="Water table")
    axes[3].plot(years, water_table_ma, linewidth=2.5, label=f"{rolling_window}Y water table avg")
    axes[3].set_xlabel("Year")
    axes[3].set_ylabel("Water, in")
    axes[3].legend(loc="upper right")
    axes[3].grid(alpha=0.25)

    # 4. Agricultural yield


    plt.tight_layout(rect=(0, 0, 1, 0.97))
    fig.savefig(file_path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)

    return file_path


def plot_biome_dashboards(
    biomes: Iterable[Any],
    output_dir: str | Path,
    rolling_window: int = 5,
    dpi: int = 160,
) -> list[Path]:
    """Generate one climate dashboard PNG per biome."""
    saved_paths: list[Path] = []

    for biome in biomes:
        path = plot_biome_dashboard(
            biome=biome,
            output_dir=output_dir,
            rolling_window=rolling_window,
            dpi=dpi,
        )

        if path is not None:
            saved_paths.append(path)

    return saved_paths
