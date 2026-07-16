"""
map_generation.py

Procedural ASCII map generator for the weather/food world sim.

Tile legend:
    m = mountain
    h = hills
    p = plains
    f = forest
    r = river
    d = desert
    V = village
    C = city

Generation architecture:
    1. elevation layer
    2. moisture layer
    3. river layer, generated from elevation but kept separate
    4. terrain layer, using lower mountain/hill cutoffs than the first draft
    5. river layer merged down for rendering/gameplay
    6. settlement layer

The important change from the first draft is that rivers are no longer owned by
terrain tiles while they are being generated. They are generated on a separate
river layer from high-elevation sources toward edge destinations, then merged
back into the visible map.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from random import Random
from typing import Iterable


class TileKind(StrEnum):
    Mountain = "m"
    Hills = "h"
    Plains = "p"
    Forest = "f"
    River = "r"
    Desert = "d"
    Village = "V"
    City = "C"


@dataclass
class Tile:
    x: int
    y: int
    kind: TileKind = TileKind.Plains
    elevation: float = 0.0
    moisture: float = 0.0
    fertility: float = 0.0
    has_river: bool = False
    settlement: TileKind | None = None

    @property
    def char(self) -> str:
        if self.settlement is not None:
            return self.settlement.value
        if self.has_river:
            return TileKind.River.value
        return self.kind.value

    @property
    def is_settleable(self) -> bool:
        return self.kind in {TileKind.Plains, TileKind.Forest, TileKind.Hills} and not self.has_river


class WorldMap:
    def __init__(
        self,
        width: int = 40,
        height: int = 20,
        seed: int | None = None,
        mountain_percentile: float = 0.95,
        hill_percentile: float = 0.80,
        river_count_min: int = 2,
        river_count_max: int = 3,
    ):
        if width < 8 or height < 8:
            raise ValueError("WorldMap needs at least 8x8 to generate coherent terrain and rivers.")

        self.width = width
        self.height = height
        self.seed = seed
        self.rng = Random(seed)

        # New terrain cutoffs: much less mountainous than the first draft.
        self.mountain_percentile = mountain_percentile
        self.hill_percentile = hill_percentile

        self.river_count_min = river_count_min
        self.river_count_max = max(river_count_min, river_count_max)

        self.tiles: list[list[Tile]] = [
            [Tile(x=x, y=y) for x in range(width)]
            for y in range(height)
        ]

        # Separate layer; merged into Tile.has_river after terrain is assigned.
        self.river_layer: set[tuple[int, int]] = set()

    def __getitem__(self, pos: tuple[int, int]) -> Tile:
        x, y = pos
        return self.tiles[y][x]

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    def neighbors4(self, x: int, y: int) -> Iterable[Tile]:
        for dx, dy in ((0, -1), (1, 0), (0, 1), (-1, 0)):
            nx, ny = x + dx, y + dy
            if self.in_bounds(nx, ny):
                yield self.tiles[ny][nx]

    def neighbors8(self, x: int, y: int) -> Iterable[Tile]:
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                nx, ny = x + dx, y + dy
                if self.in_bounds(nx, ny):
                    yield self.tiles[ny][nx]

    def generate(self) -> WorldMap:
        self._generate_elevation()
        self._generate_moisture()
        self._generate_river_layer()
        self._assign_base_terrain()
        self._merge_river_layer()
        self._grow_forests()
        self._apply_river_valley_effects()
        self._place_settlements()
        return self

    # ------------------------------------------------------------------
    # Terrain layers
    # ------------------------------------------------------------------

    def _generate_elevation(self) -> None:
        elevation = [
            [self.rng.random() * 0.28 for _ in range(self.width)]
            for _ in range(self.height)
        ]

        # Broad continental slope: west/northwest tends high, east/southeast tends low.
        # This gives rivers a consistent reason to cross the map instead of dying early.
        for y in range(self.height):
            for x in range(self.width):
                west = 1.0 - (x / max(1, self.width - 1))
                north = 1.0 - (y / max(1, self.height - 1))
                elevation[y][x] += 0.42 * west + 0.14 * north

        # Fewer, broader uplift regions. The percentile cutoffs will keep true mountains rare.
        blob_count = max(2, (self.width * self.height) // 180)
        for _ in range(blob_count):
            cx = self.rng.randrange(0, max(1, self.width // 2 + 2))
            cy = self.rng.randrange(0, self.height)
            radius = self.rng.uniform(4.0, 8.5)
            strength = self.rng.uniform(0.35, 0.75)

            for y in range(self.height):
                for x in range(self.width):
                    dist = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5
                    if dist <= radius:
                        elevation[y][x] += strength * (1.0 - dist / radius)

        elevation = self._smooth_grid(elevation, passes=3)

        for y in range(self.height):
            for x in range(self.width):
                self.tiles[y][x].elevation = elevation[y][x]

    def _generate_moisture(self) -> None:
        moisture = [
            [self.rng.random() * 0.42 for _ in range(self.width)]
            for _ in range(self.height)
        ]

        for y in range(self.height):
            for x in range(self.width):
                east = x / max(1, self.width - 1)
                south = y / max(1, self.height - 1)
                moisture[y][x] += 0.32 * (1.0 - east)
                moisture[y][x] += 0.08 * (1.0 - south)
                moisture[y][x] -= 0.18 * east * south

        blob_count = max(3, (self.width * self.height) // 120)
        for _ in range(blob_count):
            cx = self.rng.randrange(0, self.width)
            cy = self.rng.randrange(0, self.height)
            radius = self.rng.uniform(3.0, 6.5)
            strength = self.rng.uniform(0.20, 0.50)

            for y in range(self.height):
                for x in range(self.width):
                    dist = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5
                    if dist <= radius:
                        moisture[y][x] += strength * (1.0 - dist / radius)

        moisture = self._smooth_grid(moisture, passes=2)

        for y in range(self.height):
            for x in range(self.width):
                self.tiles[y][x].moisture = moisture[y][x]

    def _assign_base_terrain(self) -> None:
        elevations = sorted(tile.elevation for row in self.tiles for tile in row)
        moistures = sorted(tile.moisture for row in self.tiles for tile in row)

        mountain_cutoff = self._percentile(elevations, self.mountain_percentile)
        hill_cutoff = self._percentile(elevations, self.hill_percentile)
        dry_cutoff = self._percentile(moistures, 0.14)
        forest_cutoff = self._percentile(moistures, 0.66)

        for row in self.tiles:
            for tile in row:
                if tile.elevation >= mountain_cutoff:
                    tile.kind = TileKind.Mountain
                elif tile.elevation >= hill_cutoff:
                    tile.kind = TileKind.Hills
                elif tile.moisture <= dry_cutoff and tile.elevation < hill_cutoff:
                    tile.kind = TileKind.Desert
                elif tile.moisture >= forest_cutoff:
                    tile.kind = TileKind.Forest
                else:
                    tile.kind = TileKind.Plains

    def _grow_forests(self) -> None:
        for _ in range(2):
            to_forest: list[Tile] = []
            for row in self.tiles:
                for tile in row:
                    if tile.kind != TileKind.Plains or tile.has_river:
                        continue
                    forest_neighbors = sum(1 for n in self.neighbors8(tile.x, tile.y) if n.kind == TileKind.Forest)
                    if forest_neighbors >= 3 and self.rng.random() < 0.55:
                        to_forest.append(tile)
                    elif forest_neighbors >= 2 and tile.moisture > 0.58 and self.rng.random() < 0.25:
                        to_forest.append(tile)
            for tile in to_forest:
                tile.kind = TileKind.Forest

    # ------------------------------------------------------------------
    # River layer generation
    # ------------------------------------------------------------------

    def _generate_river_layer(self) -> None:
        """
        Generate rivers on a separate layer.

        Rivers start on high ground and route toward a random edge destination.
        They prefer downhill movement, but they are allowed to cross shallow rises
        so they don't peter out after a few tiles.
        """
        source_pool = self._high_elevation_sources()
        if not source_pool:
            return

        river_count = self._river_count()
        self.rng.shuffle(source_pool)

        selected_sources: list[Tile] = []
        for source in source_pool:
            if all(self._manhattan(source, other) >= 6 for other in selected_sources):
                selected_sources.append(source)
            if len(selected_sources) >= river_count:
                break

        if not selected_sources:
            selected_sources = source_pool[:river_count]

        for source in selected_sources:
            destination = self._choose_river_destination(source)
            self._trace_river_path(source, destination)

    def _high_elevation_sources(self) -> list[Tile]:
        elevations = sorted(tile.elevation for row in self.tiles for tile in row)
        cutoff = self._percentile(elevations, 0.86)
        sources = [
            tile
            for row in self.tiles
            for tile in row
            if tile.elevation >= cutoff and not self._is_map_edge(tile.x, tile.y)
        ]
        sources.sort(key=lambda tile: tile.elevation, reverse=True)
        return sources

    def _river_count(self) -> int:
        area = self.width * self.height
        if area < 300:
            upper = min(self.river_count_max, 2)
        elif area < 700:
            upper = min(self.river_count_max, 3)
        else:
            upper = self.river_count_max
        return self.rng.randint(self.river_count_min, upper)

    def _choose_river_destination(self, source: Tile) -> tuple[int, int]:
        edge_tiles: list[Tile] = []
        for x in range(self.width):
            edge_tiles.append(self.tiles[0][x])
            edge_tiles.append(self.tiles[self.height - 1][x])
        for y in range(1, self.height - 1):
            edge_tiles.append(self.tiles[y][0])
            edge_tiles.append(self.tiles[y][self.width - 1])

        # Prefer lower edge destinations and destinations far from the source.
        def score(tile: Tile) -> float:
            distance = self._manhattan(source, tile)
            low = 1.0 - tile.elevation
            east_or_south = (tile.x / max(1, self.width - 1)) + (tile.y / max(1, self.height - 1))
            return distance * 0.18 + low * 2.0 + east_or_south * 0.35 + self.rng.uniform(-0.25, 0.25)

        edge_tiles.sort(key=score, reverse=True)
        chosen = edge_tiles[0]
        return chosen.x, chosen.y

    def _trace_river_path(self, source: Tile, destination: tuple[int, int]) -> None:
        current = source
        visited: set[tuple[int, int]] = set()
        max_steps = self.width + self.height + max(self.width, self.height)

        for step in range(max_steps):
            pos = (current.x, current.y)
            already_river = pos in self.river_layer
            visited.add(pos)

            # Merge into an existing river only after this river has a real length.
            # Check this before adding the current position, otherwise every river
            # would accidentally merge into itself.
            if step > 6 and already_river:
                return

            # Do not erase the source mountain visually unless the river has left it.
            if step > 0 or current.kind != TileKind.Mountain:
                self.river_layer.add(pos)

            if self._is_map_edge(current.x, current.y):
                return

            candidates = [n for n in self.neighbors8(current.x, current.y) if (n.x, n.y) not in visited]
            if not candidates:
                return

            dx, dy = destination

            def path_score(tile: Tile) -> float:
                dist_now = abs(current.x - dx) + abs(current.y - dy)
                dist_next = abs(tile.x - dx) + abs(tile.y - dy)
                distance_gain = dist_now - dist_next

                downhill = current.elevation - tile.elevation
                uphill_penalty = max(0.0, tile.elevation - current.elevation)

                # River wants to reach destination and flow downhill, but destination
                # pressure prevents it from dying in local basins.
                score = 0.0
                score += distance_gain * 1.20
                score += downhill * 2.50
                score -= uphill_penalty * 1.75
                score += tile.moisture * 0.10
                score += self.rng.uniform(-0.08, 0.08)
                return score

            candidates.sort(key=path_score, reverse=True)
            current = candidates[0]

    def _merge_river_layer(self) -> None:
        for x, y in self.river_layer:
            if self.in_bounds(x, y):
                self.tiles[y][x].has_river = True

    def _apply_river_valley_effects(self) -> None:
        river_tiles = [tile for row in self.tiles for tile in row if tile.has_river]

        for river in river_tiles:
            for tile in self.neighbors8(river.x, river.y):
                tile.moisture += 0.25
                tile.fertility += 0.40

                if tile.kind == TileKind.Desert:
                    tile.kind = TileKind.Plains

                if tile.kind == TileKind.Hills and self.rng.random() < 0.18:
                    tile.kind = TileKind.Plains

    # ------------------------------------------------------------------
    # Settlements
    # ------------------------------------------------------------------

    def _place_settlements(self) -> None:
        candidates = [tile for row in self.tiles for tile in row if tile.is_settleable]
        if not candidates:
            return

        scored = [(self._settlement_score(tile), tile) for tile in candidates]
        scored.sort(key=lambda item: item[0], reverse=True)

        city_tile = scored[0][1]
        city_tile.settlement = TileKind.City

        for _, tile in scored[1:]:
            dist = abs(tile.x - city_tile.x) + abs(tile.y - city_tile.y)
            if dist >= max(5, min(self.width, self.height) // 3):
                tile.settlement = TileKind.Village
                break

    def _settlement_score(self, tile: Tile) -> float:
        score = 0.0

        if tile.kind == TileKind.Plains:
            score += 5.0
        elif tile.kind == TileKind.Forest:
            score += 3.0
        elif tile.kind == TileKind.Hills:
            score += 2.0

        score += tile.moisture * 2.0
        score += tile.fertility * 3.0

        river_neighbors = sum(1 for n in self.neighbors8(tile.x, tile.y) if n.has_river)
        forest_neighbors = sum(1 for n in self.neighbors8(tile.x, tile.y) if n.kind == TileKind.Forest)
        hill_neighbors = sum(1 for n in self.neighbors8(tile.x, tile.y) if n.kind == TileKind.Hills)
        mountain_neighbors = sum(1 for n in self.neighbors8(tile.x, tile.y) if n.kind == TileKind.Mountain)

        score += river_neighbors * 2.75
        score += forest_neighbors * 0.35
        score += hill_neighbors * 0.25
        score += mountain_neighbors * 0.15

        if self._is_map_edge(tile.x, tile.y):
            score -= 1.5

        score += self.rng.uniform(-0.25, 0.25)
        return score

    # ------------------------------------------------------------------
    # Output / utility
    # ------------------------------------------------------------------

    def render(self) -> str:
        return "\n".join("".join(tile.char for tile in row) for row in self.tiles)

    def print(self) -> None:
        print(self.render())

    def counts(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for row in self.tiles:
            for tile in row:
                out[tile.char] = out.get(tile.char, 0) + 1
        return dict(sorted(out.items()))

    @classmethod
    def from_ascii(cls, ascii_map: str) -> WorldMap:
        lines = [line.rstrip() for line in ascii_map.strip().splitlines() if line.strip()]
        height = len(lines)
        width = max(len(line) for line in lines)
        world = cls(width=width, height=height)

        for y, line in enumerate(lines):
            for x, char in enumerate(line.ljust(width)):
                tile = world.tiles[y][x]
                if char == TileKind.River.value:
                    tile.kind = TileKind.Plains
                    tile.has_river = True
                    world.river_layer.add((x, y))
                elif char == TileKind.Village.value:
                    tile.kind = TileKind.Plains
                    tile.settlement = TileKind.Village
                elif char == TileKind.City.value:
                    tile.kind = TileKind.Plains
                    tile.settlement = TileKind.City
                elif char in {kind.value for kind in TileKind}:
                    tile.kind = TileKind(char)
                else:
                    tile.kind = TileKind.Plains

        return world

    def _is_map_edge(self, x: int, y: int) -> bool:
        return x == 0 or y == 0 or x == self.width - 1 or y == self.height - 1

    @staticmethod
    def _manhattan(a: Tile, b: Tile) -> int:
        return abs(a.x - b.x) + abs(a.y - b.y)

    @staticmethod
    def _percentile(values: list[float], q: float) -> float:
        if not values:
            return 0.0
        q = min(max(q, 0.0), 1.0)
        index = int(q * (len(values) - 1))
        return values[index]

    @staticmethod
    def _smooth_grid(grid: list[list[float]], passes: int = 1) -> list[list[float]]:
        height = len(grid)
        width = len(grid[0]) if height else 0
        current = grid

        for _ in range(passes):
            nxt = [[0.0 for _ in range(width)] for _ in range(height)]
            for y in range(height):
                for x in range(width):
                    total = 0.0
                    count = 0
                    for dy in (-1, 0, 1):
                        for dx in (-1, 0, 1):
                            nx, ny = x + dx, y + dy
                            if 0 <= nx < width and 0 <= ny < height:
                                total += current[ny][nx]
                                count += 1
                    nxt[y][x] = total / count
            current = nxt

        return current


def generate_map(width: int = 40, height: int = 20, seed: int | None = None) -> WorldMap:
    return WorldMap(width=width, height=height, seed=seed).generate()


def main() -> None:
    world = generate_map(width=40, height=20, seed=7)
    world.print()
    print()
    print(world.counts())


if __name__ == "__main__":
    main()
