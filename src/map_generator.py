from __future__ import annotations

from collections import deque
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
    flow_to: tuple[int, int] | None = None
    flow_accumulation: float = 1.0
    settlement: TileKind | None = None
    owner_id: int | None = None
    parent_city_id: int | None = None

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


@dataclass
class PoliticalRegion:
    id: int
    city: Tile
    villages: list[Tile]

    @property
    def label(self) -> str:
        return chr(ord("A") + (self.id % 26))


class WorldMap:
    def __init__(
        self,
        width: int = 40,
        height: int = 20,
        seed: int | None = None,
        mountain_percentile: float = 0.95,
        hill_percentile: float = 0.80,
        river_threshold: float | None = None,
        city_count_min: int = 2,
        city_count_max: int = 3,
        villages_per_city_min: int = 2,
        villages_per_city_max: int = 3,
        min_city_distance: int | None = None,
        rivers_are_borders: bool = True,
    ):
        if width < 8 or height < 8:
            raise ValueError("WorldMap needs at least 8x8.")
        self.width = width
        self.height = height
        self.seed = seed
        self.rng = Random(seed)
        self.mountain_percentile = mountain_percentile
        self.hill_percentile = hill_percentile
        self.river_threshold = river_threshold
        self.city_count_min = city_count_min
        self.city_count_max = max(city_count_min, city_count_max)
        self.villages_per_city_min = villages_per_city_min
        self.villages_per_city_max = max(villages_per_city_min, villages_per_city_max)
        self.min_city_distance = min_city_distance or max(8, min(width, height) // 3)
        self.rivers_are_borders = rivers_are_borders
        self.tiles = [[Tile(x=x, y=y) for x in range(width)] for y in range(height)]
        self.political_regions: list[PoliticalRegion] = []

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
        self._build_flow_field()
        self._calculate_flow_accumulation()
        self._generate_rivers_from_accumulation()
        self._assign_base_terrain()
        self._grow_forests()
        self._apply_river_valley_effects()
        self._generate_political_layer()
        return self

    # Terrain generation -------------------------------------------------

    def _generate_elevation(self) -> None:
        continent = self._fractal_value_noise([(4, 0.55), (8, 0.30), (16, 0.15)])
        ridges = self._ridge_layer()
        field = [[0.0 for _ in range(self.width)] for _ in range(self.height)]
        for y in range(self.height):
            for x in range(self.width):
                west = 1.0 - x / max(1, self.width - 1)
                north = 1.0 - y / max(1, self.height - 1)
                slope = 0.32 * west + 0.10 * north
                field[y][x] = continent[y][x] * 0.55 + ridges[y][x] * 0.65 + slope
        field = self._smooth_grid(self._normalize_grid(field), 1)
        for y in range(self.height):
            for x in range(self.width):
                self.tiles[y][x].elevation = field[y][x]

    def _generate_moisture(self) -> None:
        noise = self._fractal_value_noise([(3, 0.50), (7, 0.35), (14, 0.15)])
        field = [[0.0 for _ in range(self.width)] for _ in range(self.height)]
        for y in range(self.height):
            for x in range(self.width):
                east = x / max(1, self.width - 1)
                south = y / max(1, self.height - 1)
                field[y][x] = noise[y][x] * 0.65 + (1.0 - east) * 0.25 + (1.0 - south) * 0.10 - east * south * 0.18
        field = self._normalize_grid(self._smooth_grid(field, 1))
        for y in range(self.height):
            for x in range(self.width):
                self.tiles[y][x].moisture = field[y][x]

    def _assign_base_terrain(self) -> None:
        elevations = sorted(t.elevation for row in self.tiles for t in row)
        moistures = sorted(t.moisture for row in self.tiles for t in row)
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
            spread = []
            for row in self.tiles:
                for tile in row:
                    if tile.kind != TileKind.Plains or tile.has_river:
                        continue
                    forest_neighbors = sum(1 for n in self.neighbors8(tile.x, tile.y) if n.kind == TileKind.Forest)
                    if forest_neighbors >= 3 and self.rng.random() < 0.55:
                        spread.append(tile)
                    elif forest_neighbors >= 2 and tile.moisture > 0.58 and self.rng.random() < 0.25:
                        spread.append(tile)
            for tile in spread:
                tile.kind = TileKind.Forest

    # Flow accumulation rivers ------------------------------------------

    def _build_flow_field(self) -> None:
        for row in self.tiles:
            for tile in row:
                tile.flow_to = self._choose_flow_neighbor(tile)

    def _choose_flow_neighbor(self, tile: Tile) -> tuple[int, int] | None:
        if self._is_map_edge(tile.x, tile.y):
            return None
        current = self._effective_elevation(tile)
        candidates = list(self.neighbors8(tile.x, tile.y))
        lower = [n for n in candidates if self._effective_elevation(n) < current]
        if lower:
            choice = min(lower, key=self._effective_elevation)
        else:
            choice = min(candidates, key=lambda n: self._effective_elevation(n) + self._edge_distance(n) * 0.01)
        return choice.x, choice.y

    def _effective_elevation(self, tile: Tile) -> float:
        return tile.elevation + self._edge_distance(tile) * 0.003

    def _calculate_flow_accumulation(self) -> None:
        for row in self.tiles:
            for tile in row:
                tile.flow_accumulation = 1.0
        ordered = sorted((t for row in self.tiles for t in row), key=self._effective_elevation, reverse=True)
        for tile in ordered:
            if tile.flow_to is None:
                continue
            nx, ny = tile.flow_to
            if self.in_bounds(nx, ny):
                self.tiles[ny][nx].flow_accumulation += tile.flow_accumulation

    def _generate_rivers_from_accumulation(self) -> None:
        area = self.width * self.height
        threshold = self.river_threshold if self.river_threshold is not None else max(10.0, area * 0.030)
        for row in self.tiles:
            for tile in row:
                tile.has_river = tile.flow_accumulation >= threshold and not self._is_map_edge(tile.x, tile.y)
        for row in self.tiles:
            for tile in row:
                if tile.has_river and not self._river_reaches_edge(tile):
                    tile.has_river = False

    def _river_reaches_edge(self, source: Tile) -> bool:
        current = source
        seen = set()
        for _ in range(self.width + self.height + max(self.width, self.height)):
            if (current.x, current.y) in seen:
                return False
            seen.add((current.x, current.y))
            if self._is_map_edge(current.x, current.y):
                return True
            if current.flow_to is None:
                return False
            nx, ny = current.flow_to
            if not self.in_bounds(nx, ny):
                return False
            current = self.tiles[ny][nx]
        return False

    def _apply_river_valley_effects(self) -> None:
        for river in [t for row in self.tiles for t in row if t.has_river]:
            for tile in self.neighbors8(river.x, river.y):
                tile.moisture += 0.25
                tile.fertility += 0.40
                if tile.kind == TileKind.Desert:
                    tile.kind = TileKind.Plains
                if tile.kind == TileKind.Hills and self.rng.random() < 0.18:
                    tile.kind = TileKind.Plains

    # Political layer ----------------------------------------------------

    def _generate_political_layer(self) -> None:
        cities = self._place_cities()
        if not cities:
            return
        self._assign_political_ownership_river_aware(cities)
        self.political_regions = []
        for city_id, city in enumerate(cities):
            city.settlement = TileKind.City
            city.owner_id = city_id
            city.parent_city_id = city_id
            villages = self._place_villages_for_city(city_id, city)
            self.political_regions.append(PoliticalRegion(city_id, city, villages))

    def _place_cities(self) -> list[Tile]:
        candidates = [t for row in self.tiles for t in row if t.is_settleable]
        scored = sorted(((self._city_score(t), t) for t in candidates), key=lambda item: item[0], reverse=True)
        desired = self.rng.randint(self.city_count_min, self.city_count_max)
        cities = []
        for _, tile in scored:
            if len(cities) >= desired:
                break
            if all(self._manhattan(tile, c) >= self.min_city_distance for c in cities):
                cities.append(tile)
        relaxed = max(4, self.min_city_distance // 2)
        if len(cities) < desired:
            for _, tile in scored:
                if len(cities) >= desired:
                    break
                if tile not in cities and all(self._manhattan(tile, c) >= relaxed for c in cities):
                    cities.append(tile)
        return cities

    def _assign_political_ownership_river_aware(self, cities: list[Tile]) -> None:
        for row in self.tiles:
            for tile in row:
                tile.owner_id = None
                tile.parent_city_id = None
        q = deque()
        for city_id, city in enumerate(cities):
            city.owner_id = city_id
            city.parent_city_id = city_id
            q.append(city)
        while q:
            tile = q.popleft()
            for n in self.neighbors4(tile.x, tile.y):
                if n.owner_id is not None:
                    continue
                if self.rivers_are_borders and n.has_river:
                    continue
                n.owner_id = tile.owner_id
                q.append(n)
        for row in self.tiles:
            for tile in row:
                if tile.owner_id is None:
                    tile.owner_id = min(range(len(cities)), key=lambda cid: self._manhattan(tile, cities[cid]) + (2 if tile.has_river else 0))

    def _place_villages_for_city(self, city_id: int, city: Tile) -> list[Tile]:
        desired = self.rng.randint(self.villages_per_city_min, self.villages_per_city_max)
        search_radius = max(6, self.min_city_distance)
        candidates = [
            t for row in self.tiles for t in row
            if t.owner_id == city_id and t.is_settleable and t.settlement is None
            and 2 <= self._manhattan(t, city) <= search_radius
        ]
        if len(candidates) < desired:
            candidates = [
                t for row in self.tiles for t in row
                if t.owner_id == city_id and t.is_settleable and t.settlement is None
                and self._manhattan(t, city) >= 2
            ]
        scored = sorted(((self._village_score(t, city), t) for t in candidates), key=lambda item: item[0], reverse=True)
        villages = []
        for _, tile in scored:
            if len(villages) >= desired:
                break
            if all(self._manhattan(tile, v) >= 3 for v in villages):
                tile.settlement = TileKind.Village
                tile.owner_id = city_id
                tile.parent_city_id = city_id
                villages.append(tile)
        if len(villages) < desired:
            for _, tile in scored:
                if len(villages) >= desired:
                    break
                if tile not in villages and tile.settlement is None:
                    tile.settlement = TileKind.Village
                    tile.owner_id = city_id
                    tile.parent_city_id = city_id
                    villages.append(tile)
        return villages

    def _city_score(self, tile: Tile) -> float:
        river_neighbors = sum(1 for n in self.neighbors8(tile.x, tile.y) if n.has_river)
        plains_neighbors = sum(1 for n in self.neighbors8(tile.x, tile.y) if n.kind == TileKind.Plains)
        forest_neighbors = sum(1 for n in self.neighbors8(tile.x, tile.y) if n.kind == TileKind.Forest)
        hill_neighbors = sum(1 for n in self.neighbors8(tile.x, tile.y) if n.kind == TileKind.Hills)
        edge_penalty = 2.0 if self._is_map_edge(tile.x, tile.y) else 0.0
        return self._base_settlement_score(tile) + river_neighbors * 3.25 + plains_neighbors * 0.55 + forest_neighbors * 0.20 + hill_neighbors * 0.15 - edge_penalty + self.rng.uniform(-0.35, 0.35)

    def _village_score(self, tile: Tile, city: Tile) -> float:
        river_neighbors = sum(1 for n in self.neighbors8(tile.x, tile.y) if n.has_river)
        plains_neighbors = sum(1 for n in self.neighbors8(tile.x, tile.y) if n.kind == TileKind.Plains)
        forest_neighbors = sum(1 for n in self.neighbors8(tile.x, tile.y) if n.kind == TileKind.Forest)
        distance = self._manhattan(tile, city)
        distance_score = 1.0 if 3 <= distance <= 7 else -abs(distance - 5) * 0.15
        return self._base_settlement_score(tile) + river_neighbors * 2.25 + plains_neighbors * 0.45 + forest_neighbors * 0.25 + distance_score + self.rng.uniform(-0.30, 0.30)

    def _base_settlement_score(self, tile: Tile) -> float:
        score = 0.0
        if tile.kind == TileKind.Plains:
            score += 5.0
        elif tile.kind == TileKind.Forest:
            score += 3.0
        elif tile.kind == TileKind.Hills:
            score += 2.0
        elif tile.kind == TileKind.Desert:
            score -= 4.0
        elif tile.kind == TileKind.Mountain:
            score -= 5.0
        score += tile.moisture * 2.0 + tile.fertility * 3.0
        return score

    # Output -------------------------------------------------------------

    def political_summary(self) -> list[dict[str, object]]:
        return [
            {
                "id": r.id,
                "label": r.label,
                "city": (r.city.x, r.city.y),
                "villages": [(v.x, v.y) for v in r.villages],
                "tile_count": sum(1 for row in self.tiles for t in row if t.owner_id == r.id),
            }
            for r in self.political_regions
        ]

    def render(self) -> str:
        return "\n".join("".join(t.char for t in row) for row in self.tiles)

    def render_political(self, show_rivers: bool = True) -> str:
        rows = []
        for row in self.tiles:
            chars = []
            for tile in row:
                if tile.settlement is not None:
                    chars.append(tile.settlement.value)
                elif show_rivers and tile.has_river:
                    chars.append(TileKind.River.value)
                elif tile.owner_id is None:
                    chars.append(".")
                else:
                    chars.append(chr(ord("a") + (tile.owner_id % 26)))
            rows.append("".join(chars))
        return "\n".join(rows)

    def counts(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for row in self.tiles:
            for tile in row:
                out[tile.char] = out.get(tile.char, 0) + 1
        return dict(sorted(out.items()))

    @classmethod
    def from_ascii(cls, ascii_map: str) -> WorldMap:
        lines = [line.rstrip() for line in ascii_map.strip().splitlines() if line.strip()]
        world = cls(width=max(len(line) for line in lines), height=len(lines))
        for y, line in enumerate(lines):
            for x, char in enumerate(line.ljust(world.width)):
                tile = world.tiles[y][x]
                if char == TileKind.River.value:
                    tile.kind = TileKind.Plains
                    tile.has_river = True
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

    # Math utilities -----------------------------------------------------

    def _is_map_edge(self, x: int, y: int) -> bool:
        return x == 0 or y == 0 or x == self.width - 1 or y == self.height - 1

    def _edge_distance(self, tile: Tile) -> int:
        return min(tile.x, tile.y, self.width - 1 - tile.x, self.height - 1 - tile.y)

    @staticmethod
    def _manhattan(a: Tile, b: Tile) -> int:
        return abs(a.x - b.x) + abs(a.y - b.y)

    @staticmethod
    def _percentile(values: list[float], q: float) -> float:
        if not values:
            return 0.0
        q = min(max(q, 0.0), 1.0)
        return values[int(q * (len(values) - 1))]

    @staticmethod
    def _smoothstep(t: float) -> float:
        return t * t * (3.0 - 2.0 * t)

    @staticmethod
    def _lerp(a: float, b: float, t: float) -> float:
        return a + (b - a) * t

    @staticmethod
    def _distance_to_segment(px: float, py: float, ax: float, ay: float, bx: float, by: float) -> float:
        vx = bx - ax
        vy = by - ay
        wx = px - ax
        wy = py - ay
        length_sq = vx * vx + vy * vy
        if length_sq == 0:
            return ((px - ax) ** 2 + (py - ay) ** 2) ** 0.5
        t = max(0.0, min(1.0, (wx * vx + wy * vy) / length_sq))
        cx = ax + t * vx
        cy = ay + t * vy
        return ((px - cx) ** 2 + (py - cy) ** 2) ** 0.5

    def _fractal_value_noise(self, octaves: list[tuple[int, float]]) -> list[list[float]]:
        out = [[0.0 for _ in range(self.width)] for _ in range(self.height)]
        weight_sum = sum(weight for _, weight in octaves)
        for cells, weight in octaves:
            layer = self._value_noise_layer(cells)
            for y in range(self.height):
                for x in range(self.width):
                    out[y][x] += layer[y][x] * weight
        for y in range(self.height):
            for x in range(self.width):
                out[y][x] /= weight_sum
        return self._normalize_grid(out)

    def _value_noise_layer(self, cells: int) -> list[list[float]]:
        grid_w = max(2, cells + 1)
        grid_h = max(2, int(cells * self.height / self.width) + 2)
        lattice = [[self.rng.random() for _ in range(grid_w)] for _ in range(grid_h)]
        out = [[0.0 for _ in range(self.width)] for _ in range(self.height)]
        for y in range(self.height):
            gy = y / max(1, self.height - 1) * (grid_h - 1)
            y0 = int(gy)
            y1 = min(y0 + 1, grid_h - 1)
            ty = self._smoothstep(gy - y0)
            for x in range(self.width):
                gx = x / max(1, self.width - 1) * (grid_w - 1)
                x0 = int(gx)
                x1 = min(x0 + 1, grid_w - 1)
                tx = self._smoothstep(gx - x0)
                a = self._lerp(lattice[y0][x0], lattice[y0][x1], tx)
                b = self._lerp(lattice[y1][x0], lattice[y1][x1], tx)
                out[y][x] = self._lerp(a, b, ty)
        return out

    def _ridge_layer(self) -> list[list[float]]:
        field = [[0.0 for _ in range(self.width)] for _ in range(self.height)]
        ridge_count = max(1, (self.width * self.height) // 500)
        for _ in range(ridge_count):
            x0 = self.rng.uniform(0, self.width * 0.35)
            y0 = self.rng.uniform(0, self.height)
            x1 = self.rng.uniform(self.width * 0.10, self.width * 0.65)
            y1 = self.rng.uniform(0, self.height)
            radius = self.rng.uniform(2.5, 5.0)
            strength = self.rng.uniform(0.6, 1.0)
            for y in range(self.height):
                for x in range(self.width):
                    d = self._distance_to_segment(x, y, x0, y0, x1, y1)
                    if d < radius:
                        field[y][x] += strength * (1.0 - d / radius)
        return self._normalize_grid(self._smooth_grid(field, 1))

    @staticmethod
    def _normalize_grid(grid: list[list[float]]) -> list[list[float]]:
        values = [v for row in grid for v in row]
        lo = min(values)
        hi = max(values)
        if hi == lo:
            return [[0.0 for _ in row] for row in grid]
        return [[(v - lo) / (hi - lo) for v in row] for row in grid]

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
                            nx = x + dx
                            ny = y + dy
                            if 0 <= nx < width and 0 <= ny < height:
                                total += current[ny][nx]
                                count += 1
                    nxt[y][x] = total / count
            current = nxt
        return current


def generate_map(width: int = 40, height: int = 20, seed: int | None = None) -> WorldMap:
    return WorldMap(width=width, height=height, seed=seed, river_threshold=9).generate()


def main() -> None:
    world = generate_map(seed=9)
    print(world.render())
    print()
    print(world.counts())
    print()
    print("Political regions:")
    for region in world.political_summary():
        print(region)
    print()
    print("Political map:")
    print(world.render_political())


if __name__ == "__main__":
    main()
