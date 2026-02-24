"""
随机地图生成器

设计思路（方向 A + B 轻量组合）：
  1. 世界类型（World Recipe）：种子高位决定世界类型，影响大陆/海洋分布模板。
  2. POI 优先：先按种子撒城市/洞府/宗门点，再根据 POI 位置影响周围地形。
  3. 噪声地形：用纯 Python 实现的双重正弦叠加+坐标哈希噪声，无需 numpy/scipy。
  4. 区域连通块：对每块同类地形做简单 BFS 连通，按地形类型分配 normal_region。
  5. 建筑放置（2×2 大块）：城市、洞府/遗迹、宗门总部，保证不重叠且地形匹配。
"""
import math
import random
from typing import TYPE_CHECKING, Optional

from src.classes.environment.map import Map
from src.classes.environment.tile import Tile, TileType
from src.classes.environment.region import NormalRegion, CultivateRegion, CityRegion
from src.classes.environment.sect_region import SectRegion
from src.classes.essence import EssenceType

if TYPE_CHECKING:
    from src.classes.core.sect import Sect


# ---------------------------------------------------------------------------
# 世界类型定义
# ---------------------------------------------------------------------------

WORLD_TYPES = [
    "continent",    # 大陆型：北冰南林，中部平原
    "archipelago",  # 群岛型：大量海洋，散布岛屿
    "two_shores",   # 一江两岸：中间大河，两侧陆地
    "oasis",        # 荒漠绿洲：外围沙漠，中心平原+水域
    "polar_south",  # 极北南蛮：北冰南热带，中部温带
]


# ---------------------------------------------------------------------------
# 地形到 normal_region 映射（地形 TileType → region_id 候选列表）
# 每个 region_id 对应 normal_region.csv 中的一行
# ---------------------------------------------------------------------------

TERRAIN_TO_REGION_IDS: dict[TileType, list[int]] = {
    TileType.PLAIN:        [101],          # 平原地带
    TileType.DESERT:       [102],          # 西域流沙
    TileType.RAINFOREST:   [103],          # 南疆蛮荒
    TileType.GLACIER:      [104],          # 极北冰原
    TileType.SEA:          [105],          # 无边碧海
    TileType.WATER:        [106],          # 天河奔流
    TileType.MOUNTAIN:     [107, 114],     # 青峰山脉 / 十万大山
    TileType.SNOW_MOUNTAIN:[108],          # 万丈雪峰
    TileType.GRASSLAND:    [109],          # 碧野千里
    TileType.FOREST:       [110],          # 青云林海
    TileType.VOLCANO:      [111],          # 炎狱火山
    TileType.FARM:         [112],          # 沃土良田
    TileType.SWAMP:        [113],          # 幽冥毒泽
    TileType.BAMBOO:       [115],          # 紫竹幽境
    TileType.TUNDRA:       [116],          # 凛霜荒原
    TileType.GOBI:         [117],          # 碎星戈壁
    TileType.ISLAND:       [118],          # 蓬莱遗岛
    TileType.MARSH:        [113],          # 湿地 → 幽冥毒泽
}

# 城市建议周边地形（建城候选格的地形）
CITY_FRIENDLY_TERRAIN = {TileType.PLAIN, TileType.GRASSLAND, TileType.FARM, TileType.FOREST}
# 洞府建议周边地形
CAVE_FRIENDLY_TERRAIN = {
    TileType.MOUNTAIN, TileType.SNOW_MOUNTAIN, TileType.FOREST, TileType.RAINFOREST,
    TileType.BAMBOO, TileType.VOLCANO,
}
# 遗迹建议周边地形
RUIN_FRIENDLY_TERRAIN = {
    TileType.RAINFOREST, TileType.SWAMP, TileType.SEA, TileType.WATER,
    TileType.DESERT, TileType.GOBI,
}


# ---------------------------------------------------------------------------
# 简易 2D 噪声（纯 Python，无外部依赖）
# ---------------------------------------------------------------------------

def _hash_noise(x: int, y: int, seed: int) -> float:
    """返回 [0, 1] 之间基于坐标和种子的伪随机值。"""
    n = x * 1619 + y * 31337 + seed * 6971
    n = (n ^ (n >> 8)) * 0x27d4eb2d
    n = (n ^ (n >> 15)) & 0xFFFFFFFF
    return (n & 0xFFFF) / 65535.0


def _smooth_noise(x: float, y: float, seed: int, scale: float = 0.1) -> float:
    """
    多频正弦+哈希叠加噪声，返回 [-1, 1]。
    低频决定大尺度地貌，高频增加细节。
    """
    # 低频波（大陆/海洋轮廓）
    low = (
        math.sin(x * scale + y * scale * 0.7 + seed * 0.001) +
        math.cos(y * scale * 0.9 - x * scale * 0.3 + seed * 0.002)
    )
    # 中频波（山脉/平原）
    mid_scale = scale * 2.5
    mid = 0.5 * (
        math.sin(x * mid_scale + seed * 0.003) +
        math.cos(y * mid_scale + seed * 0.004)
    )
    # 高频哈希扰动（地形细节）
    hi = 0.25 * (_hash_noise(int(x), int(y), seed) * 2 - 1)
    return (low + mid + hi) / 3.75  # 归一化到约 [-1, 1]


# ---------------------------------------------------------------------------
# 世界类型生成函数
# ---------------------------------------------------------------------------

def _make_continent_heightmap(width: int, height: int, seed: int) -> list[list[float]]:
    """大陆型：中央大陆，四周海洋，北冰南林。"""
    h = []
    cx, cy = width / 2, height / 2
    for y in range(height):
        row = []
        for x in range(width):
            # 椭圆距中心的距离衰减（大陆形状）
            dx = (x - cx) / (cx * 0.85)
            dy = (y - cy) / (cy * 0.85)
            dist_fade = 1.0 - min(1.0, math.sqrt(dx * dx + dy * dy))
            noise = _smooth_noise(x, y, seed, scale=0.07)
            row.append(dist_fade * 0.6 + noise * 0.4)
        h.append(row)
    return h


def _make_archipelago_heightmap(width: int, height: int, seed: int) -> list[list[float]]:
    """群岛型：整体偏低（海洋），用更高频噪声制造分散岛屿。"""
    h = []
    for y in range(height):
        row = []
        for x in range(width):
            noise = _smooth_noise(x, y, seed, scale=0.12)
            row.append(noise - 0.1)  # 整体下移，海洋为主
        h.append(row)
    return h


def _make_two_shores_heightmap(width: int, height: int, seed: int) -> list[list[float]]:
    """一江两岸：中间竖向河道，两侧陆地。"""
    h = []
    cx = width / 2
    for y in range(height):
        row = []
        for x in range(width):
            dist_from_center = abs(x - cx) / (width * 0.5)
            # 中间低（水），两侧高（陆）
            base = (dist_from_center - 0.25) * 2.0
            noise = _smooth_noise(x, y, seed, scale=0.08)
            row.append(base * 0.6 + noise * 0.4)
        h.append(row)
    return h


def _make_oasis_heightmap(width: int, height: int, seed: int) -> list[list[float]]:
    """荒漠绿洲：四周沙漠，中心平原/水域。"""
    h = []
    cx, cy = width / 2, height / 2
    for y in range(height):
        row = []
        for x in range(width):
            dx = (x - cx) / (cx * 0.7)
            dy = (y - cy) / (cy * 0.7)
            dist = math.sqrt(dx * dx + dy * dy)
            # 中心高（绿洲），外围低（沙漠虽然高度不一定，用另一个通道决定沙漠）
            center_fade = 1.0 - min(1.0, dist)
            noise = _smooth_noise(x, y, seed, scale=0.09)
            row.append(center_fade * 0.7 + noise * 0.3)
        h.append(row)
    return h


def _make_polar_south_heightmap(width: int, height: int, seed: int) -> list[list[float]]:
    """极北南蛮：北边极寒（低），中部平原（高），南边热带（高但不同类型）。"""
    h = []
    for y in range(height):
        row = []
        # 北边 (y=0) 和南边 (y=height-1) 都适合，中间适当
        north_factor = 1.0 - (y / height)  # 越北越大
        for x in range(width):
            noise = _smooth_noise(x, y, seed, scale=0.08)
            row.append(0.4 + noise * 0.4 - north_factor * 0.2)
        h.append(row)
    return h


_HEIGHTMAP_FUNCS = {
    "continent":    _make_continent_heightmap,
    "archipelago":  _make_archipelago_heightmap,
    "two_shores":   _make_two_shores_heightmap,
    "oasis":        _make_oasis_heightmap,
    "polar_south":  _make_polar_south_heightmap,
}


# ---------------------------------------------------------------------------
# 高度值 → TileType 映射（考虑纬度/世界类型）
# ---------------------------------------------------------------------------

def _height_to_tiletype(
    h_val: float,
    x: int,
    y: int,
    width: int,
    height: int,
    world_type: str,
    secondary_noise: float,
) -> TileType:
    """
    根据高度值、坐标、世界类型、辅助噪声决定地形类型。
    h_val 约在 [-1, 1] 范围，用阈值分段。
    """
    lat = y / height        # 归一化纬度 0(北) ~ 1(南)
    lon = x / width         # 归一化经度

    # --- 水域 ---
    if h_val < -0.25:
        if h_val < -0.55:
            return TileType.SEA
        return TileType.WATER if secondary_noise > 0.5 else TileType.SEA

    # --- 海岸/岛 ---
    if h_val < -0.05:
        # 孤立水块中可能出现岛
        if secondary_noise > 0.8:
            return TileType.ISLAND
        return TileType.SEA

    # --- 陆地 ---
    # 根据世界类型和纬度决定地貌偏向

    if world_type == "oasis":
        # 外围沙漠
        cx, cy = width / 2, height / 2
        dist = math.sqrt(((x - cx) / (cx * 0.7)) ** 2 + ((y - cy) / (cy * 0.7)) ** 2)
        if dist > 0.85:
            return TileType.DESERT if secondary_noise > 0.3 else TileType.GOBI
        if dist > 0.55:
            return TileType.GOBI if secondary_noise > 0.5 else TileType.DESERT

    # 极北（lat < 0.15）
    if lat < 0.12:
        if h_val > 0.5:
            return TileType.SNOW_MOUNTAIN
        if secondary_noise > 0.5:
            return TileType.GLACIER
        return TileType.TUNDRA

    # 北区（0.12 ~ 0.25）
    if lat < 0.25:
        if h_val > 0.55:
            return TileType.SNOW_MOUNTAIN
        if h_val > 0.35:
            return TileType.MOUNTAIN
        if secondary_noise > 0.6:
            return TileType.TUNDRA
        return TileType.PLAIN

    # 南区偏热带（lat > 0.78）
    if lat > 0.78:
        if h_val > 0.5:
            return TileType.MOUNTAIN
        if secondary_noise > 0.5:
            return TileType.RAINFOREST
        if secondary_noise > 0.2:
            return TileType.SWAMP
        return TileType.FOREST

    # 中部：主要地貌
    if h_val > 0.65:
        return TileType.VOLCANO if (secondary_noise > 0.7 and lat > 0.4) else TileType.SNOW_MOUNTAIN
    if h_val > 0.45:
        return TileType.MOUNTAIN
    if h_val > 0.25:
        # 山地过渡：林/雪/竹
        if secondary_noise > 0.75:
            return TileType.BAMBOO
        if secondary_noise > 0.4:
            return TileType.FOREST
        return TileType.MOUNTAIN
    if h_val > 0.1:
        # 低地：多样化
        sn = secondary_noise
        if world_type == "archipelago":
            if sn > 0.85:
                return TileType.ISLAND
            return TileType.PLAIN
        if sn > 0.85:
            return TileType.FARM
        if sn > 0.7:
            return TileType.GRASSLAND
        if sn > 0.55:
            return TileType.FOREST
        if sn > 0.3:
            return TileType.PLAIN
        return TileType.GRASSLAND

    # 平原/湿地/沙漠（高度 0 ~ 0.1）
    if world_type in ("continent", "polar_south"):
        if secondary_noise > 0.75:
            return TileType.MARSH
        if secondary_noise > 0.4:
            return TileType.PLAIN
        return TileType.FARM

    if secondary_noise > 0.7:
        return TileType.SWAMP
    return TileType.PLAIN


# ---------------------------------------------------------------------------
# 2×2 建筑放置助手
# ---------------------------------------------------------------------------

def _can_place_2x2(tile_grid: list[list[TileType]], x: int, y: int, width: int, height: int) -> bool:
    """检查 (x, y), (x+1, y), (x, y+1), (x+1, y+1) 是否都是陆地且不是已占用的特殊地形。"""
    if x + 1 >= width or y + 1 >= height:
        return False
    blocked = {TileType.SEA, TileType.WATER, TileType.CITY, TileType.SECT, TileType.CAVE, TileType.RUIN}
    for dy in range(2):
        for dx in range(2):
            if tile_grid[y + dy][x + dx] in blocked:
                return False
    return True


def _place_2x2(tile_grid: list[list[TileType]], x: int, y: int, t: TileType) -> None:
    """在 (x,y) 起始放置 2×2 的 tile 类型。"""
    for dy in range(2):
        for dx in range(2):
            tile_grid[y + dy][x + dx] = t


def _find_candidates(
    tile_grid: list[list[TileType]],
    width: int,
    height: int,
    friendly_terrain: set[TileType],
    rng: random.Random,
    min_dist: int = 10,
    placed: Optional[list[tuple[int, int]]] = None,
) -> list[tuple[int, int]]:
    """
    找到所有可以放置 2×2 建筑的候选格（至少一个邻格为 friendly_terrain，且与已放置点距离 >= min_dist）。
    """
    if placed is None:
        placed = []
    candidates = []
    for y in range(0, height - 1, 2):
        for x in range(0, width - 1, 2):
            if not _can_place_2x2(tile_grid, x, y, width, height):
                continue
            # 检查是否邻近 friendly_terrain
            has_friendly = False
            for dy in range(-1, 3):
                for dx in range(-1, 3):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < width and 0 <= ny < height:
                        if tile_grid[ny][nx] in friendly_terrain:
                            has_friendly = True
                            break
                if has_friendly:
                    break
            if not has_friendly:
                continue
            # 检查最小间距
            too_close = False
            for px, py in placed:
                if abs(x - px) < min_dist and abs(y - py) < min_dist:
                    too_close = True
                    break
            if not too_close:
                candidates.append((x, y))
    rng.shuffle(candidates)
    return candidates


# ---------------------------------------------------------------------------
# 区域 BFS 连通分块
# ---------------------------------------------------------------------------

def _bfs_flood_fill(
    tile_grid: list[list[TileType]],
    visited: list[list[bool]],
    start_x: int,
    start_y: int,
    width: int,
    height: int,
    target_type: TileType,
) -> list[tuple[int, int]]:
    """BFS 找到与 (start_x, start_y) 连通的同类型格子集合。"""
    queue = [(start_x, start_y)]
    visited[start_y][start_x] = True
    result = []
    while queue:
        cx, cy = queue.pop()
        result.append((cx, cy))
        for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
            nx, ny = cx + dx, cy + dy
            if 0 <= nx < width and 0 <= ny < height and not visited[ny][nx]:
                if tile_grid[ny][nx] == target_type:
                    visited[ny][nx] = True
                    queue.append((nx, ny))
    return result


# ---------------------------------------------------------------------------
# 主生成函数
# ---------------------------------------------------------------------------

def generate_map(
    width: int,
    height: int,
    seed: int,
    existed_sects: Optional[list["Sect"]] = None,
    city_count: Optional[int] = None,
    cave_count: Optional[int] = None,
) -> tuple[Map, int]:
    """
    随机生成地图。

    Args:
        width: 地图宽度（格子数）
        height: 地图高度（格子数）
        seed: 随机种子（保证同 seed 可复现）
        existed_sects: 本局启用的宗门列表（用于放置宗门总部 2×2 块）
        city_count: 城市数量（None 则按面积自动推导）
        cave_count: 洞府/遗迹数量（None 则按面积自动推导）

    Returns:
        (Map 对象, 实际使用的 seed)
    """
    if existed_sects is None:
        existed_sects = []

    rng = random.Random(seed)

    # 1. 确定世界类型
    world_type_idx = seed % len(WORLD_TYPES)
    world_type = WORLD_TYPES[world_type_idx]
    print(f"[MapGenerator] seed={seed}, world_type={world_type}, size={width}x{height}")

    # 2. 生成高度图
    heightmap_fn = _HEIGHTMAP_FUNCS[world_type]
    h_map = heightmap_fn(width, height, seed)

    # 辅助噪声图（用于地形多样化）
    s2_seed = seed ^ 0xDEADBEEF
    s2_map = [[_hash_noise(x, y, s2_seed) for x in range(width)] for y in range(height)]

    # 3. 高度值 → TileType 网格
    tile_grid: list[list[TileType]] = []
    for y in range(height):
        row = []
        for x in range(width):
            t = _height_to_tiletype(
                h_map[y][x], x, y, width, height, world_type, s2_map[y][x]
            )
            row.append(t)
        tile_grid.append(row)

    # 4. 决定建筑数量
    area = width * height
    if city_count is None:
        city_count = max(3, area // 2500)
    if cave_count is None:
        cave_count = max(4, area // 2000)
    sect_count = len(existed_sects)

    print(f"[MapGenerator] planning: {city_count} cities, {cave_count} caves, {sect_count} sects")

    # 5. POI 优先放置（建筑位置决定后，可小幅修整周边地形让其"更合理"）
    placed_positions: list[tuple[int, int]] = []

    # 5a. 宗门（最高优先级）—— 宗门有各自适合的地形，但都退而求其次放在任意陆地
    sect_placed: list[tuple[int, int]] = []
    all_land = {TileType.PLAIN, TileType.GRASSLAND, TileType.FARM, TileType.FOREST,
                TileType.MOUNTAIN, TileType.SNOW_MOUNTAIN, TileType.BAMBOO,
                TileType.VOLCANO, TileType.RAINFOREST, TileType.SWAMP, TileType.TUNDRA,
                TileType.GOBI, TileType.DESERT}
    sect_candidates = _find_candidates(tile_grid, width, height, all_land, rng, min_dist=15, placed=placed_positions)
    for i, sect in enumerate(existed_sects):
        if not sect_candidates:
            break
        sx, sy = sect_candidates.pop()
        # 放置 SECT 类型（统一标记，具体 sect_id 后面绑 Region）
        _place_2x2(tile_grid, sx, sy, TileType.SECT)
        sect_placed.append((sx, sy))
        placed_positions.append((sx, sy))

    # 5b. 城市
    city_placed: list[tuple[int, int]] = []
    city_candidates = _find_candidates(tile_grid, width, height, CITY_FRIENDLY_TERRAIN, rng, min_dist=12, placed=placed_positions)
    for i in range(min(city_count, len(city_candidates))):
        cx, cy = city_candidates.pop()
        _place_2x2(tile_grid, cx, cy, TileType.CITY)
        city_placed.append((cx, cy))
        placed_positions.append((cx, cy))

    # 5c. 洞府和遗迹
    cave_placed: list[tuple[int, int]] = []
    ruin_placed: list[tuple[int, int]] = []
    cave_all_friendly = CAVE_FRIENDLY_TERRAIN | RUIN_FRIENDLY_TERRAIN | {TileType.PLAIN, TileType.GRASSLAND}
    cave_candidates = _find_candidates(tile_grid, width, height, cave_all_friendly, rng, min_dist=10, placed=placed_positions)
    ruin_split = max(1, cave_count // 3)  # 约 1/3 为遗迹
    for i in range(min(cave_count, len(cave_candidates))):
        pos = cave_candidates.pop()
        tile_type = TileType.RUIN if i < ruin_split else TileType.CAVE
        _place_2x2(tile_grid, pos[0], pos[1], tile_type)
        if tile_type == TileType.CAVE:
            cave_placed.append(pos)
        else:
            ruin_placed.append(pos)
        placed_positions.append(pos)

    # 6. 构造 Map 对象（创建 Tile）
    game_map = Map(width=width, height=height)
    for y in range(height):
        for x in range(width):
            game_map.create_tile(x, y, tile_grid[y][x])

    # 7. 建立 Region —— 普通区域（连通块 BFS）
    visited = [[False] * width for _ in range(height)]
    normal_region_id_counter = [101]  # 从 101 开始轮流分配

    # 建立地形 → region_id 的映射分配器（每种地形有自己的候选列表）
    region_type_assigned: dict[TileType, int] = {}

    def _get_or_assign_region_id(tt: TileType, rng_local: random.Random) -> int:
        if tt not in region_type_assigned:
            candidates = TERRAIN_TO_REGION_IDS.get(tt, [101])
            region_type_assigned[tt] = rng_local.choice(candidates)
        return region_type_assigned[tt]

    # 跳过特殊格（CITY/SECT/CAVE/RUIN）不参与连通块
    special_types = {TileType.CITY, TileType.SECT, TileType.CAVE, TileType.RUIN}

    # 加载 normal_region 元数据（复用已有配置）
    from src.utils.df import game_configs, get_str, get_int
    normal_region_meta: dict[int, dict] = {}
    for row in game_configs["normal_region"]:
        rid = get_int(row, "id")
        normal_region_meta[rid] = {
            "name": get_str(row, "name"),
            "desc": get_str(row, "desc"),
            "animal_ids": _parse_list(get_str(row, "animal_ids")),
            "plant_ids": _parse_list(get_str(row, "plant_ids")),
            "lode_ids": _parse_list(get_str(row, "lode_ids")),
            "essence_density": get_int(row, "essence_density", 0),
        }

    # BFS 连通块 → NormalRegion，但每种地形只分配同一个 region_id，合并同类区域
    region_tile_map: dict[int, list[tuple[int, int]]] = {}  # region_id → 格子列表

    for y in range(height):
        for x in range(width):
            if visited[y][x]:
                continue
            tt = tile_grid[y][x]
            if tt in special_types:
                visited[y][x] = True
                continue
            # BFS
            cluster = _bfs_flood_fill(tile_grid, visited, x, y, width, height, tt)
            rid = _get_or_assign_region_id(tt, rng)
            if rid not in region_tile_map:
                region_tile_map[rid] = []
            region_tile_map[rid].extend(cluster)

    # 创建 NormalRegion 对象并注册
    for rid, cors in region_tile_map.items():
        if rid not in normal_region_meta:
            continue
        meta = normal_region_meta[rid]
        region_obj = NormalRegion(
            id=rid,
            name=meta["name"],
            desc=meta["desc"],
            cors=cors,
            animal_ids=meta["animal_ids"],
            plant_ids=meta["plant_ids"],
            lode_ids=meta["lode_ids"],
            essence_density=meta.get("essence_density", 0),
        )
        game_map.regions[rid] = region_obj
        game_map.region_cors[rid] = cors
        for tx, ty in cors:
            if game_map.is_in_bounds(tx, ty):
                game_map.tiles[(tx, ty)].region = region_obj

    # 8. 建立 Region —— 特殊建筑

    # 加载配置元数据
    city_meta_list = _load_city_meta(game_configs)
    cultivate_meta_list = _load_cultivate_meta(game_configs)
    sect_meta_list = _load_sect_meta(game_configs, existed_sects)

    # 城市
    from src.classes.core.sect import sects_by_id as _sects_by_id
    city_ids = [301, 302, 303, 304, 305]
    for i, (cx, cy) in enumerate(city_placed):
        meta_idx = i % len(city_meta_list)
        meta = city_meta_list[meta_idx]
        cors = [(cx + dx, cy + dy) for dy in range(2) for dx in range(2)]
        region_obj = CityRegion(
            id=meta["id"],
            name=meta["name"],
            desc=meta["desc"],
            cors=cors,
            sell_item_ids=meta.get("sell_item_ids", []),
        )
        _register_region(game_map, region_obj)

    # 洞府
    cave_essence_cycle = [
        EssenceType.GOLD, EssenceType.WOOD, EssenceType.WATER,
        EssenceType.FIRE, EssenceType.EARTH
    ]
    for i, (cx, cy) in enumerate(cave_placed):
        meta_idx = i % max(1, len([m for m in cultivate_meta_list if m.get("sub_type") == "cave"]))
        cave_metas = [m for m in cultivate_meta_list if m.get("sub_type") == "cave"]
        if not cave_metas:
            break
        meta = cave_metas[i % len(cave_metas)]
        cors = [(cx + dx, cy + dy) for dy in range(2) for dx in range(2)]
        region_obj = CultivateRegion(
            id=meta["id"],
            name=meta["name"],
            desc=meta["desc"],
            cors=cors,
            essence_type=EssenceType.from_str(meta.get("root_type", "GOLD")),
            essence_density=meta.get("root_density", 8),
            sub_type="cave",
        )
        _register_region(game_map, region_obj)

    # 遗迹
    ruin_metas = [m for m in cultivate_meta_list if m.get("sub_type") == "ruin"]
    for i, (cx, cy) in enumerate(ruin_placed):
        if not ruin_metas:
            break
        meta = ruin_metas[i % len(ruin_metas)]
        cors = [(cx + dx, cy + dy) for dy in range(2) for dx in range(2)]
        region_obj = CultivateRegion(
            id=meta["id"],
            name=meta["name"],
            desc=meta["desc"],
            cors=cors,
            essence_type=EssenceType.from_str(meta.get("root_type", "WOOD")),
            essence_density=meta.get("root_density", 8),
            sub_type="ruin",
        )
        _register_region(game_map, region_obj)

    # 宗门
    for i, ((sx, sy), sect) in enumerate(zip(sect_placed, existed_sects)):
        meta = sect_meta_list[i] if i < len(sect_meta_list) else None
        cors = [(sx + dx, sy + dy) for dy in range(2) for dx in range(2)]
        region_obj = SectRegion(
            id=400 + sect.id,
            name=meta["name"] if meta else sect.name,
            desc=meta["desc"] if meta else f"{sect.name}驻地",
            cors=cors,
            sect_id=sect.id,
            sect_name=sect.name,
        )
        _register_region(game_map, region_obj)

    game_map.update_sect_regions()
    print(f"[MapGenerator] complete: {len(game_map.regions)} regions")
    return game_map, seed


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

def _register_region(game_map: Map, region_obj) -> None:
    """注册一个 Region 到 Map，并绑定到 Tile。"""
    game_map.regions[region_obj.id] = region_obj
    game_map.region_cors[region_obj.id] = region_obj.cors
    for tx, ty in region_obj.cors:
        if game_map.is_in_bounds(tx, ty):
            game_map.tiles[(tx, ty)].region = region_obj


def _parse_list(s: str) -> list[int]:
    if not s:
        return []
    res = []
    for x in s.split(","):
        x = x.strip()
        if x:
            try:
                res.append(int(float(x)))
            except (ValueError, TypeError):
                pass
    return res


def _load_city_meta(game_configs) -> list[dict]:
    from src.utils.df import get_str, get_int
    import ast
    metas = []
    for row in game_configs["city_region"]:
        rid = get_int(row, "id")
        if not isinstance(rid, int) or rid < 100:
            continue
        sell_ids = []
        sell_str = get_str(row, "sell_item_ids")
        if sell_str:
            try:
                ids = ast.literal_eval(sell_str)
                if isinstance(ids, list):
                    sell_ids = ids
            except Exception:
                pass
        metas.append({
            "id": rid,
            "name": get_str(row, "name"),
            "desc": get_str(row, "desc"),
            "sell_item_ids": sell_ids,
        })
    return metas


def _load_cultivate_meta(game_configs) -> list[dict]:
    from src.utils.df import get_str, get_int
    metas = []
    for row in game_configs["cultivate_region"]:
        rid = get_int(row, "id")
        if not isinstance(rid, int) or rid < 100:
            continue
        metas.append({
            "id": rid,
            "name": get_str(row, "name"),
            "desc": get_str(row, "desc"),
            "sub_type": get_str(row, "sub_type") or "cave",
            "root_type": get_str(row, "root_type") or "GOLD",
            "root_density": get_int(row, "root_density") or 8,
        })
    return metas


def _load_sect_meta(game_configs, existed_sects) -> list[dict]:
    from src.utils.df import get_str, get_int
    from src.classes.core.sect import sects_by_id as _sects_by_id
    metas = []
    for sect in existed_sects:
        # 从 sect_region 配置找对应的驻地名/描述
        found = None
        for row in game_configs["sect_region"]:
            sid = get_int(row, "sect_id")
            if sid == sect.id:
                found = {
                    "name": get_str(row, "name"),
                    "desc": get_str(row, "desc"),
                }
                break
        if found:
            metas.append(found)
        else:
            metas.append({"name": f"{sect.name}驻地", "desc": f"{sect.name}的总部所在地。"})
    return metas
