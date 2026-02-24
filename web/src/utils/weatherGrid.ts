/**
 * 天气分区网格：根据地图地形与确定性噪声，为每个分区计算天气类型。
 * 供 WeatherLayer 使用，实现“地图不同地方天气不一样”。
 */
import type { MapMatrix } from '../types/core'

export type WeatherType = 'clear' | 'rain' | 'storm' | 'wind' | 'snow'

/** 分区大小（格数），每 ZONE_SIZE x ZONE_SIZE 格为一个天气分区 */
export const ZONE_SIZE = 8

/** 地形 → 天气倾向（主天气 + 可选次要）。分区内按主要地形或中心格取倾向，再叠加噪声。 */
const TERRAIN_WEATHER_TENDENCY: Record<string, { main: WeatherType; alt?: WeatherType; weight?: number }> = {
  DESERT: { main: 'clear' },
  GOBI: { main: 'clear' },
  PLAIN: { main: 'clear', alt: 'rain', weight: 0.4 },
  GRASSLAND: { main: 'clear', alt: 'rain', weight: 0.45 },
  FARM: { main: 'clear', alt: 'rain', weight: 0.35 },
  RAINFOREST: { main: 'rain', alt: 'storm', weight: 0.15 },
  FOREST: { main: 'rain', alt: 'clear', weight: 0.3 },
  BAMBOO: { main: 'rain', alt: 'clear', weight: 0.25 },
  SWAMP: { main: 'rain', alt: 'storm', weight: 0.2 },
  MARSH: { main: 'rain', alt: 'storm', weight: 0.2 },
  SEA: { main: 'wind', alt: 'rain', weight: 0.2 },
  WATER: { main: 'wind', alt: 'rain', weight: 0.25 },
  ISLAND: { main: 'wind', alt: 'rain', weight: 0.3 },
  MOUNTAIN: { main: 'clear', alt: 'rain', weight: 0.2 },
  SNOW_MOUNTAIN: { main: 'snow', alt: 'clear', weight: 0.2 },
  GLACIER: { main: 'snow', alt: 'wind', weight: 0.15 },
  TUNDRA: { main: 'snow', alt: 'wind', weight: 0.25 },
  VOLCANO: { main: 'clear' },
}

/** 确定性伪随机 [0, 1)，基于分区坐标与种子 */
function hashNoise(zx: number, zy: number, seed: number): number {
  const n = zx * 1619 + zy * 31337 + seed * 6971
  const mixed = (n ^ (n >>> 8)) * 0x27d4eb2d
  const u = (mixed ^ (mixed >>> 15)) & 0xffffffff
  return (u & 0xffff) / 65535
}

/** 未知地形时用位置噪声分配天气，保证地图上总有可见天气变化 */
function weatherFromNoise(zx: number, zy: number, seed: number): WeatherType {
  const r = hashNoise(zx, zy, seed)
  if (r < 0.35) return 'rain'
  if (r < 0.6) return 'wind'
  if (r < 0.8) return 'clear'
  return r < 0.9 ? 'snow' : 'storm'
}

/** 取分区 (zx, zy) 内的“主要地形”：中心格或多数格地形 */
function getZoneDominantTerrain(mapData: MapMatrix, zx: number, zy: number): string {
  const rows = mapData.length
  const cols = mapData[0]?.length ?? 0
  const count: Record<string, number> = {}
  for (let dy = 0; dy < ZONE_SIZE; dy++) {
    for (let dx = 0; dx < ZONE_SIZE; dx++) {
      const tx = zx * ZONE_SIZE + dx
      const ty = zy * ZONE_SIZE + dy
      if (ty >= 0 && ty < rows && tx >= 0 && tx < cols) {
        const t = mapData[ty][tx] ?? ''
        count[t] = (count[t] || 0) + 1
      }
    }
  }
  let max = 0
  let dominant = ''
  for (const [terrain, c] of Object.entries(count)) {
    if (c > max) {
      max = c
      dominant = terrain
    }
  }
  return dominant || (mapData[zy * ZONE_SIZE]?.[zx * ZONE_SIZE] ?? '')
}

/**
 * 构建整张地图的天气网格。
 * @param mapData 地形二维数组
 * @param seed 可选种子，保证同一地图同一种子结果稳定
 * @returns 二维数组 weatherGrid[zy][zx] = WeatherType，分区索引为格坐标除以 ZONE_SIZE
 */
export function buildWeatherGrid(mapData: MapMatrix, seed: number = 12345): WeatherType[][] {
  const rows = mapData.length
  const cols = mapData[0]?.length ?? 0
  if (!rows || !cols) return []

  const zoneRows = Math.ceil(rows / ZONE_SIZE)
  const zoneCols = Math.ceil(cols / ZONE_SIZE)
  const grid: WeatherType[][] = []

  for (let zy = 0; zy < zoneRows; zy++) {
    const row: WeatherType[] = []
    for (let zx = 0; zx < zoneCols; zx++) {
      const terrain = getZoneDominantTerrain(mapData, zx, zy)
      let tendency = TERRAIN_WEATHER_TENDENCY[terrain]
      const r = hashNoise(zx, zy, seed)
      if (!tendency) {
        row.push(weatherFromNoise(zx, zy, seed))
        continue
      }
      const weight = tendency.weight ?? 0
      const useAlt = tendency.alt && r < weight
      let weather: WeatherType = useAlt ? tendency.alt! : tendency.main

      // 雨区有小概率升级为雷暴
      if (weather === 'rain' && hashNoise(zx + 1, zy, seed) < 0.12) {
        weather = 'storm'
      }
      row.push(weather)
    }
    grid.push(row)
  }
  return grid
}

/**
 * 将世界像素坐标 (px, py) 转换为天气分区索引 (zx, zy)。
 * 与 MapLayer 一致：每格 TILE_SIZE=64 像素。
 */
const TILE_SIZE = 64
export function worldToZone(px: number, py: number): { zx: number; zy: number } {
  const tx = Math.floor(px / TILE_SIZE)
  const ty = Math.floor(py / TILE_SIZE)
  return {
    zx: Math.floor(tx / ZONE_SIZE),
    zy: Math.floor(ty / ZONE_SIZE),
  }
}

/**
 * 获取视口可见范围内的天气分区及其像素边界（世界坐标）。
 * 用于 WeatherLayer 只对可见分区生成粒子。
 */
export function getVisibleZones(
  cornerX: number,
  cornerY: number,
  visibleWidth: number,
  visibleHeight: number,
  zoneRows: number,
  zoneCols: number
): Array<{ zx: number; zy: number; x: number; y: number; width: number; height: number }> {
  const zonePxW = ZONE_SIZE * TILE_SIZE
  const zonePxH = ZONE_SIZE * TILE_SIZE
  const start = worldToZone(cornerX, cornerY)
  const end = worldToZone(cornerX + visibleWidth, cornerY + visibleHeight)
  const result: Array<{ zx: number; zy: number; x: number; y: number; width: number; height: number }> = []
  for (let zy = start.zy; zy <= end.zy; zy++) {
    if (zy < 0 || zy >= zoneRows) continue
    for (let zx = start.zx; zx <= end.zx; zx++) {
      if (zx < 0 || zx >= zoneCols) continue
      result.push({
        zx,
        zy,
        x: zx * zonePxW,
        y: zy * zonePxH,
        width: zonePxW,
        height: zonePxH,
      })
    }
  }
  return result
}
