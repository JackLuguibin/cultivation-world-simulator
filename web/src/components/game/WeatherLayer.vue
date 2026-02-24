<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { Container, Graphics, Sprite, Ticker } from 'pixi.js'
import { useWorldStore } from '../../stores/world'
import { useAudio } from '../../composables/useAudio'
import { useTextures } from './composables/useTextures'
import {
  buildWeatherGrid,
  getVisibleZones,
  type WeatherType,
} from '../../utils/weatherGrid'

type WeatherDisplayObject = Graphics | Sprite

const props = defineProps<{
  width: number
  height: number
}>()

const worldStore = useWorldStore()
const { textures } = useTextures()
const container = ref<Container>()
let ticker: Ticker | null = null

// 配置：炫酷效果 - 更多粒子与更频闪电
const WEATHER_LEVEL = {
  none: { rain: 0, wind: 0, snow: 0, stormChance: 0 },
  low: { rain: 120, wind: 35, snow: 45, stormChance: 0.015 },
  high: { rain: 320, wind: 90, snow: 110, stormChance: 0.035 },
} as const

function getWeatherLevel() {
  const level = (worldStore.frontendConfig?.weather as keyof typeof WEATHER_LEVEL) ?? 'high'
  return WEATHER_LEVEL[level] ?? WEATHER_LEVEL.high
}

const mapData = computed(() => worldStore.mapData)
const weatherGrid = ref<WeatherType[][]>([])

watch(
  mapData,
  (data) => {
    if (data?.length && data[0]?.length) {
      weatherGrid.value = buildWeatherGrid(data)
    } else {
      weatherGrid.value = []
    }
  },
  { immediate: true }
)

// --- 雨粒子：贴图或斜向下落的短线 ---
interface RainParticle {
  g: WeatherDisplayObject
  x: number
  y: number
  vx: number
  vy: number
  zoneX: number
  zoneY: number
  zoneW: number
  zoneH: number
}
const rainPool = ref<RainParticle[]>([])
const rainContainer = ref<Container | null>(null)

// --- 风粒子：贴图或短线 ---
interface WindParticle {
  g: WeatherDisplayObject
  x: number
  y: number
  vx: number
  zoneX: number
  zoneW: number
}
const windPool = ref<WindParticle[]>([])

// --- 雪粒子：贴图或圆点，带飘动相位 ---
interface SnowParticle {
  g: WeatherDisplayObject
  x: number
  y: number
  vy: number
  phase: number
  zoneX: number
  zoneY: number
  zoneW: number
  zoneH: number
}
const snowPool = ref<SnowParticle[]>([])

// --- 闪电：双闪 + 蓝白炫光 ---
let lightningGraphics: Graphics | null = null
let lightningAlpha = 0
let lightningPhase: 'first' | 'dim' | 'second' | 'out' = 'out'
// --- 雷暴氛围：暗色遮罩 ---
let stormOverlay: Graphics | null = null

function getViewportBounds(): { x: number; y: number; w: number; h: number } {
  const vp = (window as any).__viewport
  if (vp?.corner != null && typeof vp.scaled === 'number') {
    const scale = vp.scaled
    return {
      x: vp.corner.x,
      y: vp.corner.y,
      w: vp.screenWidth / scale,
      h: vp.screenHeight / scale,
    }
  }
  // 视口未就绪时使用全图范围，确保仍有天气粒子
  return { x: 0, y: 0, w: props.width, h: props.height }
}

function createRainParticle(): WeatherDisplayObject {
  const rainTex = textures.value['weather_rain_light'] ?? textures.value['weather_rain_dark']
  if (rainTex) {
    const s = new Sprite(rainTex)
    s.anchor.set(0.5, 0)
    s.eventMode = 'none'
    s.scale.set(0.7 + Math.random() * 1.0)
    s.rotation = 0.3 + Math.random() * 0.4
    s.alpha = 0.8 + Math.random() * 0.2
    s.tint = 0xc8e4ff
    if ('blendMode' in s) (s as any).blendMode = 'add'
    return s
  }
  const len = 12 + Math.random() * 10
  const slant = 2.5 + Math.random() * 2
  const g = new Graphics()
  g.eventMode = 'none'
  const dx = slant * len
  g.moveTo(0, 0)
  g.lineTo(dx, len)
  g.stroke({ width: 2, color: 0xd4ebff, alpha: 0.9 })
  g.moveTo(-1, 0)
  g.lineTo(dx - 1, len)
  g.stroke({ width: 1, color: 0xe8f4ff, alpha: 0.5 })
  if ('blendMode' in g) (g as any).blendMode = 'add'
  return g
}

function createWindParticle(): WeatherDisplayObject {
  const tex = textures.value['weather_wind_leaf']
  if (tex) {
    const s = new Sprite(tex)
    s.anchor.set(0.5)
    s.eventMode = 'none'
    s.scale.set(0.45 + Math.random() * 0.55)
    s.rotation = Math.random() * Math.PI * 2
    s.alpha = 0.6 + Math.random() * 0.35
    s.tint = 0xddddbb
    if ('blendMode' in s) (s as any).blendMode = 'add'
    return s
  }
  const g = new Graphics()
  g.eventMode = 'none'
  const len = 5 + Math.random() * 10
  g.moveTo(0, 0)
  g.lineTo(len, 0)
  g.stroke({ width: 1.2, color: 0xddddbb, alpha: 0.5 })
  if ('blendMode' in g) (g as any).blendMode = 'add'
  return g
}

function createSnowParticle(): WeatherDisplayObject {
  const tex = textures.value['weather_snowflake']
  if (tex) {
    const s = new Sprite(tex)
    s.anchor.set(0.5)
    s.eventMode = 'none'
    s.scale.set(0.4 + Math.random() * 0.5)
    s.rotation = Math.random() * Math.PI * 2
    s.alpha = 0.9 + Math.random() * 0.1
    s.tint = 0xeeffff
    if ('blendMode' in s) (s as any).blendMode = 'add'
    return s
  }
  const g = new Graphics()
  g.eventMode = 'none'
  g.circle(0, 0, 2)
  g.fill({ color: 0xffffff, alpha: 0.95 })
  g.moveTo(-2.5, 0)
  g.lineTo(2.5, 0)
  g.stroke({ width: 1, color: 0xffffff, alpha: 0.6 })
  g.moveTo(0, -2.5)
  g.lineTo(0, 2.5)
  g.stroke({ width: 1, color: 0xffffff, alpha: 0.6 })
  if ('blendMode' in g) (g as any).blendMode = 'add'
  return g
}

function ensureRainParticles(visibleRainZones: Array<{ x: number; y: number; width: number; height: number }>, maxCount: number) {
  const c = rainContainer.value
  if (!c) return
  const existing = rainPool.value
  let need = Math.min(maxCount, visibleRainZones.length * 35) - existing.length
  if (need <= 0 && visibleRainZones.length === 0) {
    existing.forEach((p) => {
      c.removeChild(p.g as any)
      p.g.destroy()
    })
    rainPool.value = []
    return
  }
  while (need > 0 && visibleRainZones.length > 0) {
    const zone = visibleRainZones[Math.floor(Math.random() * visibleRainZones.length)]
    const g = createRainParticle()
    g.x = zone.x + Math.random() * zone.width
    g.y = zone.y + Math.random() * zone.height
    const vx = (Math.random() - 0.5) * 0.8
    const vy = 4 + Math.random() * 6
    const p: RainParticle = { g, x: g.x, y: g.y, vx, vy, zoneX: zone.x, zoneY: zone.y, zoneW: zone.width, zoneH: zone.height }
    c.addChild(g as any)
    rainPool.value.push(p)
    need--
  }
  if (visibleRainZones.length === 0 && existing.length > 0) {
    existing.forEach((p) => {
      c.removeChild(p.g as any)
      p.g.destroy()
    })
    rainPool.value = []
  }
}

function ensureWindParticles(visibleWindZones: Array<{ x: number; y: number; width: number; height: number }>, maxCount: number) {
  const c = container.value
  if (!c) return
  const existing = windPool.value
  let need = Math.min(maxCount, visibleWindZones.length * 12) - existing.length
  if (need <= 0 && visibleWindZones.length === 0) {
    existing.forEach((p) => {
      c.removeChild(p.g as any)
      p.g.destroy()
    })
    windPool.value = []
    return
  }
  while (need > 0 && visibleWindZones.length > 0) {
    const zone = visibleWindZones[Math.floor(Math.random() * visibleWindZones.length)]
    const g = createWindParticle()
    g.x = zone.x + Math.random() * zone.width
    g.y = zone.y + Math.random() * zone.height
    const vx = 1.5 + Math.random() * 2
    const p: WindParticle = { g, x: g.x, y: g.y, vx, zoneX: zone.x, zoneW: zone.width }
    c.addChild(g as any)
    windPool.value.push(p)
    need--
  }
  if (visibleWindZones.length === 0 && existing.length > 0) {
    existing.forEach((p) => {
      c.removeChild(p.g as any)
      p.g.destroy()
    })
    windPool.value = []
  }
}

function ensureSnowParticles(visibleSnowZones: Array<{ x: number; y: number; width: number; height: number }>, maxCount: number) {
  const c = container.value
  if (!c) return
  const existing = snowPool.value
  let need = Math.min(maxCount, visibleSnowZones.length * 20) - existing.length
  if (need <= 0 && visibleSnowZones.length === 0) {
    existing.forEach((p) => {
      c.removeChild(p.g as any)
      p.g.destroy()
    })
    snowPool.value = []
    return
  }
  while (need > 0 && visibleSnowZones.length > 0) {
    const zone = visibleSnowZones[Math.floor(Math.random() * visibleSnowZones.length)]
    const g = createSnowParticle()
    g.x = zone.x + Math.random() * zone.width
    g.y = zone.y + Math.random() * zone.height
    const vy = 0.35 + Math.random() * 0.55
    const p: SnowParticle = { g, x: g.x, y: g.y, vy, phase: Math.random() * Math.PI * 2, zoneX: zone.x, zoneY: zone.y, zoneW: zone.width, zoneH: zone.height }
    c.addChild(g as any)
    snowPool.value.push(p)
    need--
  }
  if (visibleSnowZones.length === 0 && existing.length > 0) {
    existing.forEach((p) => {
      c.removeChild(p.g as any)
      p.g.destroy()
    })
    snowPool.value = []
  }
}

function ensureStormOverlay(hasStorm: boolean) {
  const c = container.value
  if (!c) return
  if (hasStorm) {
    if (!stormOverlay) {
      stormOverlay = new Graphics()
      stormOverlay.eventMode = 'none'
      stormOverlay.zIndex = 200
      stormOverlay.rect(-1000, -1000, props.width + 2000, props.height + 2000)
      stormOverlay.fill({ color: 0x0a0a1a, alpha: 0.14 })
      c.addChild(stormOverlay as any)
    }
    stormOverlay.visible = true
  } else if (stormOverlay) {
    stormOverlay.visible = false
  }
}

type StormZone = { x: number; y: number; width: number; height: number }

let stormAccum = 0
function tryLightning(dt: number, stormZones: StormZone[]) {
  if (stormZones.length === 0) return
  const level = getWeatherLevel()
  if (level.stormChance <= 0) return
  stormAccum += dt
  if (stormAccum < 0.5) return
  stormAccum = 0
  if (Math.random() > level.stormChance) return
  triggerLightning(stormZones)
}

function triggerLightning(stormZones: StormZone[]) {
  const c = container.value
  if (!c || stormZones.length === 0) return
  if (lightningGraphics) {
    c.removeChild(lightningGraphics as any)
    lightningGraphics.destroy()
  }
  lightningGraphics = new Graphics()
  lightningGraphics.eventMode = 'none'
  lightningGraphics.zIndex = 1000
  const margin = 30
  const count = Math.min(2, stormZones.length)
  const indices = new Set<number>()
  while (indices.size < count) indices.add(Math.floor(Math.random() * stormZones.length))
  indices.forEach((i) => {
    const z = stormZones[i]
    if (z) {
      lightningGraphics!.rect(z.x - margin, z.y - margin, z.width + margin * 2, z.height + margin * 2)
    }
  })
  lightningGraphics.fill({ color: 0xe8f4ff, alpha: 0.92 })
  c.addChild(lightningGraphics as any)
  lightningAlpha = 0.92
  lightningPhase = 'first'
  useAudio().play('thunder')
}

function updateLightning(dt: number) {
  if (!lightningGraphics) return
  const decay = 7
  if (lightningPhase === 'first') {
    lightningAlpha -= dt * decay
    if (lightningAlpha <= 0.25) {
      lightningAlpha = 0.25
      lightningPhase = 'dim'
    }
  } else if (lightningPhase === 'dim') {
    lightningAlpha -= dt * 2
    if (lightningAlpha <= 0.15) {
      lightningPhase = 'second'
      lightningAlpha = 0.65
    }
  } else if (lightningPhase === 'second') {
    lightningAlpha -= dt * decay
    if (lightningAlpha <= 0) lightningPhase = 'out'
  } else {
    lightningAlpha -= dt * decay
  }
  lightningGraphics.alpha = Math.max(0, lightningAlpha)
  if (lightningAlpha <= 0) {
    lightningGraphics.parent?.removeChild(lightningGraphics as any)
    lightningGraphics.destroy()
    lightningGraphics = null
    lightningPhase = 'out'
  }
}

function startTicker() {
  if (ticker) return

  ticker = new Ticker()
  ticker.add((t) => {
    setupContainers()
    const grid = weatherGrid.value
    const zoneRows = grid.length
    const zoneCols = grid[0]?.length ?? 0
    const dt = t.deltaTime
    const bounds = getViewportBounds()
    if (zoneRows === 0 || zoneCols === 0) return

    const level = getWeatherLevel()
    if (level.rain === 0 && level.wind === 0 && level.snow === 0) return

    const zones = getVisibleZones(bounds.x, bounds.y, bounds.w, bounds.h, zoneRows, zoneCols)
    const rainZones = zones.filter((z) => {
      const w = grid[z.zy]?.[z.zx]
      return w === 'rain' || w === 'storm'
    })
    const windZones = zones.filter((z) => grid[z.zy]?.[z.zx] === 'wind')
    const snowZones = zones.filter((z) => grid[z.zy]?.[z.zx] === 'snow')
    const stormZones = zones.filter((z) => grid[z.zy]?.[z.zx] === 'storm')
    const hasStorm = stormZones.length > 0

    ensureRainParticles(rainZones, level.rain)
    ensureWindParticles(windZones, level.wind)
    ensureSnowParticles(snowZones, level.snow)
    ensureStormOverlay(hasStorm)

    rainPool.value.forEach((p) => {
      p.x += p.vx * dt
      p.y += p.vy * dt
      if (p.y > p.zoneY + p.zoneH + 20) {
        p.y = p.zoneY - 10
        p.x = p.zoneX + Math.random() * p.zoneW
      }
      p.g.x = p.x
      p.g.y = p.y
    })

    windPool.value.forEach((p) => {
      p.x += p.vx * dt
      if (p.x > p.zoneX + p.zoneW + 20) {
        p.x = p.zoneX - 10
      }
      p.g.x = p.x
      p.g.y = p.y
    })

    snowPool.value.forEach((p) => {
      p.y += p.vy * dt
      p.phase += dt * 0.8
      const wobble = Math.sin(p.phase) * 1.2
      const wx = p.x + wobble
      if (p.y > p.zoneY + p.zoneH + 10) {
        p.y = p.zoneY - 5
        p.x = p.zoneX + Math.random() * p.zoneW
      }
      p.g.x = wx
      p.g.y = p.y
      if (p.g instanceof Sprite) p.g.rotation += dt * 0.15
    })

    tryLightning(dt, stormZones)
    updateLightning(dt)
  })
  ticker.start()
}

function stopTicker() {
  if (ticker) {
    ticker.stop()
    ticker.destroy()
    ticker = null
  }
  stormAccum = 0
  if (stormOverlay?.parent) {
    stormOverlay.visible = false
  }
  if (lightningGraphics?.parent) {
    lightningGraphics.parent.removeChild(lightningGraphics as any)
    lightningGraphics.destroy()
    lightningGraphics = null
  }
  rainPool.value.forEach((p) => {
    p.g.destroy()
  })
  rainPool.value = []
  windPool.value.forEach((p) => p.g.destroy())
  windPool.value = []
  snowPool.value.forEach((p) => p.g.destroy())
  snowPool.value = []
}

function setupContainers() {
  if (rainContainer.value) return
  const c = container.value
  if (!c) return
  rainContainer.value = new Container()
  rainContainer.value.eventMode = 'none'
  if ('blendMode' in rainContainer.value) (rainContainer.value as any).blendMode = 'add'
  c.addChild(rainContainer.value as any)
}

watch(
  () => getWeatherLevel(),
  (level) => {
    if (level.rain === 0 && level.wind === 0 && level.snow === 0) {
      stopTicker()
    } else if (weatherGrid.value.length > 0) {
      startTicker()
    }
  },
  { deep: true }
)

watch(
  [weatherGrid, () => worldStore.frontendConfig?.weather],
  () => {
    const level = getWeatherLevel()
    if (level.rain === 0 && level.wind === 0 && level.snow === 0) {
      stopTicker()
      return
    }
    if (weatherGrid.value.length > 0) {
      startTicker()
    }
  },
  { deep: true }
)

onMounted(() => {
  setupContainers()
  if (getWeatherLevel().rain !== 0 && weatherGrid.value.length > 0) {
    startTicker()
  }
})

onUnmounted(() => {
  stopTicker()
  rainContainer.value = null
  if (stormOverlay?.parent) {
    stormOverlay.parent.removeChild(stormOverlay as any)
    stormOverlay.destroy()
    stormOverlay = null
  }
})
</script>

<template>
  <container ref="container" :z-index="350" event-mode="none" />
</template>
