<script setup lang="ts">
/**
 * 世界年鉴面板
 * 按年份归档重要事件，展示世界历史
 */
import { ref, computed, watch } from 'vue'
import { useWorldStore } from '../../../stores/world'
import { useUiStore } from '../../../stores/ui'

const worldStore = useWorldStore()
const uiStore = useUiStore()

const showPanel = ref(false)
const selectedYear = ref<number | null>(null)
const viewMode = ref<'chronicle' | 'stats'>('chronicle')

// 按年份归档重要事件
const chronicleByYear = computed(() => {
  const yearMap = new Map<number, typeof worldStore.events>()
  const majorEvents = worldStore.events.filter(e => e.isMajor || e.isStory)

  for (const event of majorEvents) {
    if (!yearMap.has(event.year)) {
      yearMap.set(event.year, [])
    }
    yearMap.get(event.year)!.push(event)
  }

  // 按年份倒序
  return Array.from(yearMap.entries())
    .sort((a, b) => b[0] - a[0])
    .map(([year, events]) => ({ year, events, count: events.length }))
})

// 选中年份的事件详情
const selectedYearEvents = computed(() => {
  if (!selectedYear.value) return []
  const entry = chronicleByYear.value.find(e => e.year === selectedYear.value)
  return entry?.events || []
})

// 世界统计
const worldStats = computed(() => {
  const total = worldStore.avatarList.length
  const alive = worldStore.avatarList.filter(a => !a.is_dead).length
  const dead = total - alive
  const majorCount = worldStore.events.filter(e => e.isMajor).length
  const storyCount = worldStore.events.filter(e => e.isStory).length

  return { total, alive, dead, majorCount, storyCount }
})

// 初始选择最新年份
watch(showPanel, (show) => {
  if (show && chronicleByYear.value.length > 0 && !selectedYear.value) {
    selectedYear.value = chronicleByYear.value[0].year
  }
})

function formatTime(event: { year: number; month: number }) {
  return `第${event.year}年${event.month}月`
}

function getEventIcon(text: string): string {
  if (/突破|境界/.test(text)) return '⚡'
  if (/战|攻击|击败|刺杀/.test(text)) return '⚔'
  if (/天劫|心魔/.test(text)) return '☁'
  if (/奇遇|机缘/.test(text)) return '✦'
  if (/拍卖|交易/.test(text)) return '◈'
  if (/传授|对话/.test(text)) return '◎'
  return '·'
}
</script>

<template>
  <!-- 悬浮按钮 -->
  <div class="chronicle-fab" @click="showPanel = !showPanel" :class="{ active: showPanel }">
    <span class="fab-icon">史</span>
  </div>

  <!-- 年鉴面板 -->
  <Teleport to="body">
    <Transition name="chronicle-panel">
      <div v-if="showPanel" class="chronicle-overlay" @click.self="showPanel = false">
        <div class="chronicle-panel">
          <!-- 标题 -->
          <div class="chronicle-header">
            <div class="chronicle-title">
              <span class="title-deco">卷</span>
              世界年鉴
            </div>
            <div class="view-toggle">
              <button :class="{ active: viewMode === 'chronicle' }" @click="viewMode = 'chronicle'">史书</button>
              <button :class="{ active: viewMode === 'stats' }" @click="viewMode = 'stats'">统计</button>
            </div>
            <button class="close-btn" @click="showPanel = false">×</button>
          </div>

          <!-- 史书模式 -->
          <div v-if="viewMode === 'chronicle'" class="chronicle-body">
            <!-- 左侧年份列表 -->
            <div class="year-list">
              <div class="year-list-title">纪年</div>
              <div
                v-for="entry in chronicleByYear"
                :key="entry.year"
                class="year-item"
                :class="{ active: selectedYear === entry.year }"
                @click="selectedYear = entry.year"
              >
                <span class="year-num">{{ entry.year }}年</span>
                <span class="year-count">{{ entry.count }}事</span>
              </div>
              <div v-if="chronicleByYear.length === 0" class="year-empty">
                史册尚无大事记录
              </div>
            </div>

            <!-- 右侧事件详情 -->
            <div class="year-detail">
              <div v-if="selectedYear" class="detail-header">
                <div class="detail-year">第 {{ selectedYear }} 年</div>
                <div class="detail-count">共 {{ selectedYearEvents.length }} 件大事</div>
              </div>
              <div class="detail-events">
                <div
                  v-for="event in selectedYearEvents"
                  :key="event.id"
                  class="chronicle-event"
                >
                  <div class="event-time-icon">
                    <span class="event-icon">{{ getEventIcon(event.text) }}</span>
                    <span class="event-time">{{ formatTime(event) }}</span>
                  </div>
                  <div class="event-text">{{ event.text }}</div>
                  <div v-if="event.content && event.content !== event.text" class="event-detail">
                    {{ event.content }}
                  </div>
                </div>
                <div v-if="selectedYearEvents.length === 0 && selectedYear" class="detail-empty">
                  此年份无大事记录
                </div>
                <div v-if="!selectedYear" class="detail-empty">
                  ← 选择年份查看史料
                </div>
              </div>
            </div>
          </div>

          <!-- 统计模式 -->
          <div v-if="viewMode === 'stats'" class="stats-body">
            <div class="stats-section">
              <div class="section-title">世界概况</div>
              <div class="stats-grid">
                <div class="stat-card">
                  <div class="stat-icon">⚡</div>
                  <div class="stat-value">{{ worldStats.alive }}</div>
                  <div class="stat-label">在世修士</div>
                </div>
                <div class="stat-card">
                  <div class="stat-icon">✟</div>
                  <div class="stat-value">{{ worldStats.dead }}</div>
                  <div class="stat-label">已陨落</div>
                </div>
                <div class="stat-card">
                  <div class="stat-icon">✦</div>
                  <div class="stat-value">{{ worldStats.majorCount }}</div>
                  <div class="stat-label">重大事件</div>
                </div>
                <div class="stat-card">
                  <div class="stat-icon">卷</div>
                  <div class="stat-value">{{ worldStore.events.length }}</div>
                  <div class="stat-label">总事件数</div>
                </div>
              </div>
            </div>

            <div class="stats-section">
              <div class="section-title">时间轴</div>
              <div class="timeline">
                <div class="timeline-item current">
                  <div class="tl-dot"></div>
                  <div class="tl-content">
                    <div class="tl-year">当前：第{{ worldStore.year }}年{{ worldStore.month }}月</div>
                    <div class="tl-desc">世界仍在运转</div>
                  </div>
                </div>
                <div
                  v-for="entry in chronicleByYear.slice(0, 8)"
                  :key="entry.year"
                  class="timeline-item"
                  @click="viewMode = 'chronicle'; selectedYear = entry.year"
                >
                  <div class="tl-dot"></div>
                  <div class="tl-content">
                    <div class="tl-year">第{{ entry.year }}年</div>
                    <div class="tl-desc">{{ entry.count }}件大事</div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 底部 -->
          <div class="chronicle-footer">
            当前 {{ worldStore.year }}年{{ worldStore.month }}月 · 已记录 {{ worldStore.events.length }} 件事
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
/* 悬浮按钮 */
.chronicle-fab {
  position: absolute;
  bottom: 172px;
  right: 14px;
  width: 48px;
  height: 48px;
  background: radial-gradient(circle at 30% 30%, rgba(61, 219, 176, 0.2), rgba(6, 8, 16, 0.9));
  border: 1px solid rgba(61, 219, 176, 0.35);
  border-radius: 50%;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 80;
  transition: all 0.25s;
  box-shadow: 0 0 8px rgba(61, 219, 176, 0.12);
}

.chronicle-fab:hover,
.chronicle-fab.active {
  background: radial-gradient(circle at 30% 30%, rgba(61, 219, 176, 0.35), rgba(6, 8, 16, 0.95));
  box-shadow: 0 0 16px rgba(61, 219, 176, 0.3);
  transform: scale(1.05);
}

.fab-icon {
  font-size: 16px;
  color: var(--color-jade, #3ddbb0);
  font-weight: bold;
}

/* 遮罩 */
.chronicle-overlay {
  position: fixed;
  inset: 0;
  z-index: 280;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.4);
  backdrop-filter: blur(2px);
}

/* 面板 */
.chronicle-panel {
  width: 640px;
  max-height: 78vh;
  background: linear-gradient(135deg, #060a12, #090d1c);
  border: 1px solid rgba(61, 219, 176, 0.25);
  border-radius: 4px;
  box-shadow: 0 0 40px rgba(0, 0, 0, 0.8), 0 0 0 1px rgba(61, 219, 176, 0.08);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  position: relative;
}

.chronicle-panel::before {
  content: '';
  position: absolute;
  top: 4px; left: 4px;
  width: 12px; height: 12px;
  border-top: 1px solid rgba(61, 219, 176, 0.5);
  border-left: 1px solid rgba(61, 219, 176, 0.5);
  pointer-events: none;
}

/* 头部 */
.chronicle-header {
  display: flex;
  align-items: center;
  padding: 12px 20px;
  border-bottom: 1px solid rgba(61, 219, 176, 0.15);
  background: rgba(61, 219, 176, 0.03);
  gap: 12px;
}

.chronicle-title {
  flex: 1;
  font-size: 16px;
  font-weight: bold;
  color: var(--color-jade, #3ddbb0);
  letter-spacing: 3px;
  text-shadow: 0 0 8px rgba(61, 219, 176, 0.4);
  display: flex;
  align-items: center;
  gap: 8px;
}

.title-deco {
  font-size: 18px;
  opacity: 0.7;
}

.view-toggle {
  display: flex;
  gap: 4px;
}

.view-toggle button {
  background: transparent;
  border: 1px solid rgba(61, 219, 176, 0.2);
  color: rgba(200, 190, 170, 0.4);
  padding: 3px 10px;
  font-size: 12px;
  border-radius: 1px;
  cursor: pointer;
  font-family: inherit;
  transition: all 0.2s;
}

.view-toggle button.active {
  background: rgba(61, 219, 176, 0.12);
  border-color: rgba(61, 219, 176, 0.4);
  color: var(--color-jade, #3ddbb0);
}

.close-btn {
  background: transparent;
  border: none;
  color: rgba(61, 219, 176, 0.4);
  font-size: 20px;
  cursor: pointer;
  padding: 0 4px;
  transition: color 0.2s;
}
.close-btn:hover { color: rgba(61, 219, 176, 0.9); }

/* 史书主体 */
.chronicle-body {
  flex: 1;
  display: flex;
  overflow: hidden;
}

/* 年份列表 */
.year-list {
  width: 110px;
  flex-shrink: 0;
  border-right: 1px solid rgba(255, 255, 255, 0.05);
  overflow-y: auto;
  background: rgba(0, 0, 0, 0.15);
}

.year-list-title {
  padding: 8px 12px 4px;
  font-size: 10px;
  color: rgba(61, 219, 176, 0.4);
  letter-spacing: 2px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.04);
}

.year-item {
  display: flex;
  flex-direction: column;
  padding: 8px 12px;
  cursor: pointer;
  transition: background 0.15s;
  border-bottom: 1px solid rgba(255, 255, 255, 0.03);
}

.year-item:hover {
  background: rgba(61, 219, 176, 0.05);
}

.year-item.active {
  background: rgba(61, 219, 176, 0.1);
  border-right: 2px solid rgba(61, 219, 176, 0.5);
}

.year-num {
  font-size: 13px;
  color: var(--color-text-main, #e8dfc0);
}

.year-item.active .year-num {
  color: var(--color-jade, #3ddbb0);
}

.year-count {
  font-size: 10px;
  color: rgba(200, 190, 170, 0.35);
}

.year-empty {
  padding: 16px 12px;
  font-size: 11px;
  color: rgba(200, 190, 170, 0.25);
  text-align: center;
}

/* 事件详情 */
.year-detail {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}

.detail-header {
  padding: 10px 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  display: flex;
  align-items: baseline;
  gap: 10px;
  flex-shrink: 0;
}

.detail-year {
  font-size: 15px;
  font-weight: bold;
  color: var(--color-jade, #3ddbb0);
}

.detail-count {
  font-size: 11px;
  color: rgba(200, 190, 170, 0.4);
}

.detail-events {
  padding: 8px 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.chronicle-event {
  padding: 10px 12px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 2px;
  border-left: 2px solid rgba(61, 219, 176, 0.3);
}

.event-time-icon {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 5px;
}

.event-icon {
  font-size: 12px;
  color: var(--color-jade, #3ddbb0);
  opacity: 0.7;
}

.event-time {
  font-size: 10px;
  color: rgba(200, 190, 170, 0.4);
}

.event-text {
  font-size: 13px;
  color: var(--color-text-main, #e8dfc0);
  line-height: 1.6;
}

.event-detail {
  margin-top: 6px;
  font-size: 11px;
  color: rgba(200, 190, 170, 0.5);
  line-height: 1.5;
  padding-top: 5px;
  border-top: 1px dashed rgba(255, 255, 255, 0.06);
}

.detail-empty {
  padding: 20px;
  text-align: center;
  color: rgba(200, 190, 170, 0.25);
  font-size: 12px;
}

/* 统计模式 */
.stats-body {
  flex: 1;
  overflow-y: auto;
  padding: 16px 20px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.stats-section {}

.section-title {
  font-size: 12px;
  color: rgba(61, 219, 176, 0.5);
  letter-spacing: 2px;
  margin-bottom: 10px;
  border-bottom: 1px solid rgba(61, 219, 176, 0.1);
  padding-bottom: 4px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
}

.stat-card {
  background: rgba(0, 0, 0, 0.25);
  border: 1px solid rgba(61, 219, 176, 0.1);
  border-radius: 3px;
  padding: 12px 8px;
  text-align: center;
}

.stat-icon {
  font-size: 16px;
  margin-bottom: 6px;
  color: var(--color-jade, #3ddbb0);
  opacity: 0.7;
}

.stat-value {
  font-size: 22px;
  font-weight: bold;
  color: var(--color-jade, #3ddbb0);
  text-shadow: 0 0 6px rgba(61, 219, 176, 0.3);
}

.stat-label {
  font-size: 10px;
  color: rgba(200, 190, 170, 0.4);
  margin-top: 4px;
  letter-spacing: 0.5px;
}

/* 时间轴 */
.timeline {
  display: flex;
  flex-direction: column;
  gap: 0;
  position: relative;
  padding-left: 24px;
}

.timeline::before {
  content: '';
  position: absolute;
  left: 6px;
  top: 8px;
  bottom: 8px;
  width: 1px;
  background: linear-gradient(to bottom, rgba(61, 219, 176, 0.4), rgba(61, 219, 176, 0.1), transparent);
}

.timeline-item {
  display: flex;
  gap: 10px;
  padding: 6px 0;
  cursor: pointer;
  position: relative;
}

.tl-dot {
  position: absolute;
  left: -21px;
  top: 10px;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: rgba(61, 219, 176, 0.3);
  border: 1px solid rgba(61, 219, 176, 0.5);
}

.timeline-item.current .tl-dot {
  background: var(--color-jade, #3ddbb0);
  box-shadow: 0 0 6px rgba(61, 219, 176, 0.6);
}

.timeline-item:hover .tl-dot {
  background: rgba(61, 219, 176, 0.6);
}

.tl-year {
  font-size: 13px;
  color: var(--color-text-main, #e8dfc0);
}

.tl-desc {
  font-size: 11px;
  color: rgba(200, 190, 170, 0.4);
}

/* 底部 */
.chronicle-footer {
  padding: 6px 20px;
  font-size: 10px;
  color: rgba(200, 190, 170, 0.25);
  text-align: center;
  border-top: 1px solid rgba(255, 255, 255, 0.04);
  flex-shrink: 0;
}

/* 过渡动画 */
.chronicle-panel-enter-active {
  animation: chronicle-in 0.3s ease-out;
}
.chronicle-panel-leave-active {
  animation: chronicle-in 0.2s ease-in reverse;
}

@keyframes chronicle-in {
  from { opacity: 0; transform: scale(0.97) translateY(-8px); }
  to { opacity: 1; transform: scale(1) translateY(0); }
}
</style>
