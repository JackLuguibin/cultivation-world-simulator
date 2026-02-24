<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, computed } from 'vue'
import { useWorldStore } from '../../stores/world'

const worldStore = useWorldStore()

// -------------------------------------------------------
// 地形颜色表（与 TileType 对应）
// -------------------------------------------------------
const TERRAIN_COLORS: Record<string, [number, number, number]> = {
  PLAIN:        [122, 158,  95],
  WATER:        [ 74, 127, 193],
  SEA:          [ 43,  90, 158],
  MOUNTAIN:     [139, 115,  85],
  FOREST:       [ 45, 107,  45],
  CITY:         [200, 160,  64],
  DESERT:       [212, 168,  84],
  RAINFOREST:   [ 26, 122,  42],
  GLACIER:      [176, 216, 240],
  SNOW_MOUNTAIN:[232, 232, 248],
  VOLCANO:      [192,  64,  32],
  GRASSLAND:    [144, 192,  96],
  SWAMP:        [ 74, 106,  58],
  CAVE:         [106,  80,  64],
  RUIN:         [138, 112,  96],
  FARM:         [184, 192,  80],
  SECT:         [192, 160,  80],
  ISLAND:       [144, 200, 144],
  BAMBOO:       [ 74, 138,  80],
  GOBI:         [200, 168, 112],
  TUNDRA:       [144, 168, 176],
  MARSH:        [ 90, 122,  80],
}
const DEFAULT_COLOR: [number, number, number] = [80, 80, 80]

// -------------------------------------------------------
// 小地图尺寸
// -------------------------------------------------------
const MINI_MAX_W = 180   // 小地图最大宽度（像素）
const MINI_MAX_H = 120   // 小地图最大高度（像素）

const canvasRef = ref<HTMLCanvasElement | null>(null)
const collapsed = ref(false)

const mapData = computed(() => worldStore.mapData)
const mapHeight = computed(() => mapData.value.length)
const mapWidth  = computed(() => mapData.value[0]?.length ?? 0)

// 小地图实际像素尺寸（保持宽高比，不超过最大值）
const miniW = computed(() => {
  if (!mapWidth.value || !mapHeight.value) return MINI_MAX_W
  const scaleW = MINI_MAX_W / mapWidth.value
  const scaleH = MINI_MAX_H / mapHeight.value
  return Math.round(Math.min(scaleW, scaleH) * mapWidth.value)
})
const miniH = computed(() => {
  if (!mapWidth.value || !mapHeight.value) return MINI_MAX_H
  const scaleW = MINI_MAX_W / mapWidth.value
  const scaleH = MINI_MAX_H / mapHeight.value
  return Math.round(Math.min(scaleW, scaleH) * mapHeight.value)
})

// 每格对应的像素数（可能 < 1）
const tilePixW = computed(() => mapWidth.value  ? miniW.value / mapWidth.value  : 1)
const tilePixH = computed(() => mapHeight.value ? miniH.value / mapHeight.value : 1)

// -------------------------------------------------------
// 绘制地形底图（ImageData 批量写像素，性能优）
// -------------------------------------------------------
function drawTerrain() {
  const canvas = canvasRef.value
  if (!canvas || !mapData.value.length) return
  const w = miniW.value
  const h = miniH.value
  canvas.width  = w
  canvas.height = h
  const ctx = canvas.getContext('2d')
  if (!ctx) return

  const imgData = ctx.createImageData(w, h)
  const d = imgData.data

  const tw = tilePixW.value
  const th = tilePixH.value

  for (let ty = 0; ty < mapHeight.value; ty++) {
    for (let tx = 0; tx < mapWidth.value; tx++) {
      const type = mapData.value[ty]?.[tx] ?? ''
      const [r, g, b] = TERRAIN_COLORS[type] ?? DEFAULT_COLOR

      const px0 = Math.floor(tx * tw)
      const px1 = Math.min(w, Math.ceil((tx + 1) * tw))
      const py0 = Math.floor(ty * th)
      const py1 = Math.min(h, Math.ceil((ty + 1) * th))

      for (let py = py0; py < py1; py++) {
        for (let px = px0; px < px1; px++) {
          const idx = (py * w + px) * 4
          d[idx]     = r
          d[idx + 1] = g
          d[idx + 2] = b
          d[idx + 3] = 255
        }
      }
    }
  }
  ctx.putImageData(imgData, 0, 0)
}

// -------------------------------------------------------
// 绘制视口指示框（每帧轮询 window.__viewport）
// -------------------------------------------------------
let rafId: number | null = null
let terrainCanvas: HTMLCanvasElement | null = null  // 离屏底图缓存

function drawViewportIndicator() {
  const canvas = canvasRef.value
  if (!canvas) return
  const ctx = canvas.getContext('2d')
  if (!ctx) return

  const vp: any = (window as any).__viewport
  if (!vp) return

  // 恢复底图
  if (terrainCanvas) {
    ctx.clearRect(0, 0, canvas.width, canvas.height)
    ctx.drawImage(terrainCanvas, 0, 0)
  }

  // 计算视口在世界坐标中的范围
  const worldTileW = mapWidth.value  * 64  // TILE_SIZE = 64
  const worldTileH = mapHeight.value * 64

  if (!worldTileW || !worldTileH) return

  const corner = vp.corner           // {x, y} 左上角世界坐标
  const scale  = vp.scaled           // 当前缩放比例
  const visW   = vp.screenWidth  / scale   // 可见区域世界宽度
  const visH   = vp.screenHeight / scale   // 可见区域世界高度

  // 映射到小地图像素
  const rx = (corner.x / worldTileW) * miniW.value
  const ry = (corner.y / worldTileH) * miniH.value
  const rw = (visW     / worldTileW) * miniW.value
  const rh = (visH     / worldTileH) * miniH.value

  // 画视口框
  ctx.strokeStyle = 'rgba(255, 220, 80, 0.9)'
  ctx.lineWidth   = 1.5
  ctx.strokeRect(rx, ry, rw, rh)

  // 半透明填充
  ctx.fillStyle = 'rgba(255, 220, 80, 0.08)'
  ctx.fillRect(rx, ry, rw, rh)
}

function startLoop() {
  function loop() {
    if (!collapsed.value) drawViewportIndicator()
    rafId = requestAnimationFrame(loop)
  }
  loop()
}

function stopLoop() {
  if (rafId !== null) {
    cancelAnimationFrame(rafId)
    rafId = null
  }
}

// -------------------------------------------------------
// 重新构建底图并缓存为离屏 Canvas
// -------------------------------------------------------
function rebuildTerrain() {
  if (!mapData.value.length) return

  // 先画到真实 canvas
  drawTerrain()

  // 拷贝为离屏缓存
  const canvas = canvasRef.value
  if (canvas) {
    terrainCanvas = document.createElement('canvas')
    terrainCanvas.width  = canvas.width
    terrainCanvas.height = canvas.height
    terrainCanvas.getContext('2d')!.drawImage(canvas, 0, 0)
  }
}

watch(mapData, () => { rebuildTerrain() }, { deep: false })

onMounted(() => {
  rebuildTerrain()
  startLoop()
})

onUnmounted(() => {
  stopLoop()
})

// -------------------------------------------------------
// 交互：点击/拖拽 → 移动主视口
// -------------------------------------------------------
let isDragging = false

function canvasToWorld(offsetX: number, offsetY: number): { x: number; y: number } {
  const canvas = canvasRef.value!
  // 把点击坐标映射到地图格子，再乘以 TILE_SIZE = 64
  const fracX = offsetX / canvas.width
  const fracY = offsetY / canvas.height
  const worldX = fracX * mapWidth.value  * 64
  const worldY = fracY * mapHeight.value * 64
  return { x: worldX, y: worldY }
}

function moveViewportTo(wx: number, wy: number) {
  const vp: any = (window as any).__viewport
  if (vp) vp.moveCenter(wx, wy)
}

function onPointerDown(e: PointerEvent) {
  if (collapsed.value) return
  isDragging = true
  ;(e.currentTarget as HTMLElement).setPointerCapture(e.pointerId)
  const { x, y } = canvasToWorld(e.offsetX, e.offsetY)
  moveViewportTo(x, y)
}

function onPointerMove(e: PointerEvent) {
  if (!isDragging) return
  const { x, y } = canvasToWorld(e.offsetX, e.offsetY)
  moveViewportTo(x, y)
}

function onPointerUp(e: PointerEvent) {
  if (isDragging) {
    ;(e.currentTarget as HTMLElement).releasePointerCapture(e.pointerId)
    isDragging = false
  }
}

function toggleCollapse() {
  collapsed.value = !collapsed.value
}
</script>

<template>
  <div class="minimap-wrapper" :class="{ collapsed }">
    <!-- 标题栏 -->
    <div class="minimap-header" @click="toggleCollapse" title="折叠/展开小地图">
      <span class="minimap-title">地图</span>
      <span class="minimap-toggle">{{ collapsed ? '▲' : '▼' }}</span>
    </div>

    <!-- 画布 -->
    <canvas
      v-show="!collapsed"
      ref="canvasRef"
      class="minimap-canvas"
      :width="miniW"
      :height="miniH"
      @pointerdown="onPointerDown"
      @pointermove="onPointerMove"
      @pointerup="onPointerUp"
      @pointerleave="onPointerUp"
    />
  </div>
</template>

<style scoped>
.minimap-wrapper {
  position: absolute;
  bottom: 16px;
  left: 16px;
  z-index: 80;
  background: rgba(6, 8, 16, 0.82);
  border: 1px solid rgba(201, 162, 39, 0.4);
  border-radius: 4px;
  backdrop-filter: blur(6px);
  box-shadow: 0 2px 16px rgba(0, 0, 0, 0.6), 0 0 8px rgba(201, 162, 39, 0.08);
  overflow: hidden;
  user-select: none;
  transition: box-shadow 0.2s;
}

.minimap-wrapper:hover {
  box-shadow: 0 2px 20px rgba(0, 0, 0, 0.7), 0 0 12px rgba(201, 162, 39, 0.18);
  border-color: rgba(201, 162, 39, 0.65);
}

.minimap-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 4px 8px;
  cursor: pointer;
  border-bottom: 1px solid rgba(201, 162, 39, 0.2);
  background: rgba(201, 162, 39, 0.06);
}

.minimap-title {
  font-size: 11px;
  color: rgba(201, 162, 39, 0.85);
  letter-spacing: 2px;
  font-family: var(--font-family-title, serif);
}

.minimap-toggle {
  font-size: 9px;
  color: rgba(201, 162, 39, 0.5);
}

.collapsed .minimap-header {
  border-bottom: none;
}

.minimap-canvas {
  display: block;
  cursor: crosshair;
  image-rendering: pixelated;
}
</style>
