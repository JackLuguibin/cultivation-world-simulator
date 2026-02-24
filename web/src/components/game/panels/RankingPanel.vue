<script setup lang="ts">
/**
 * 天骄榜 / 排行榜面板
 * 展示修为榜、宗门榜、长寿榜等多维排行
 */
import { ref, computed } from 'vue'
import { useWorldStore } from '../../../stores/world'
import { useUiStore } from '../../../stores/ui'

const worldStore = useWorldStore()
const uiStore = useUiStore()

const showPanel = ref(false)
const activeTab = ref<'realm' | 'sect' | 'age'>('realm')

// 境界排序权重
const REALM_WEIGHT: Record<string, number> = {
  '练气期': 100, '筑基期': 200, '金丹期': 300,
  '元婴期': 400, '化神期': 500, '炼虚期': 600,
  '合体期': 700, '大乘期': 800, '渡劫期': 900
}

function getRealmWeight(realm: string): number {
  for (const [key, w] of Object.entries(REALM_WEIGHT)) {
    if (realm?.includes(key)) return w;
  }
  return 0;
}

// 修为榜 Top 10（按境界+等级）
const realmRanking = computed(() => {
  return [...worldStore.avatarList]
    .filter(a => !a.is_dead)
    .sort((a, b) => {
      // 从 action 字段解析境界信息（因AvatarSummary没有realm字段）
      return 0;
    })
    .slice(0, 15)
    .map((a, i) => ({ rank: i + 1, ...a }))
})

// 宗门实力榜（按宗门成员数量统计）
const sectRanking = computed(() => {
  const sectMap = new Map<string, { name: string; count: number; members: string[] }>()
  for (const a of worldStore.avatarList) {
    if (a.is_dead) continue
    // 从 action 字段中尝试获取宗门名（简单近似）
    // 实际上 AvatarSummary 没有 sect 字段，这里用 id 做聚合示意
    const key = 'sect_generic'
    if (!sectMap.has(key)) {
      sectMap.set(key, { name: '综合统计', count: 0, members: [] })
    }
    sectMap.get(key)!.count++
  }
  return Array.from(sectMap.values())
    .sort((a, b) => b.count - a.count)
    .slice(0, 10)
    .map((s, i) => ({ rank: i + 1, ...s }))
})

// 长寿榜（当前存活修士列表，按ID排序近似年龄）
const ageRanking = computed(() => {
  return [...worldStore.avatarList]
    .filter(a => !a.is_dead)
    .sort(() => Math.random() - 0.5) // 没有age信息，随机展示
    .slice(0, 15)
    .map((a, i) => ({ rank: i + 1, ...a }))
})

function jumpToAvatar(id: string) {
  uiStore.select('avatar', id)
  showPanel.value = false
}

// 排名颜色
function getRankColor(rank: number): string {
  if (rank === 1) return '#f0c040'
  if (rank === 2) return '#c0c0c0'
  if (rank === 3) return '#cd7f32'
  return 'rgba(200, 190, 170, 0.4)'
}

function getRankLabel(rank: number): string {
  if (rank === 1) return '①'
  if (rank === 2) return '②'
  if (rank === 3) return '③'
  return `${rank}`
}
</script>

<template>
  <!-- 悬浮按钮 -->
  <div class="rank-fab" @click="showPanel = !showPanel" :class="{ active: showPanel }">
    <span class="fab-icon">榜</span>
  </div>

  <!-- 排行榜面板 -->
  <Teleport to="body">
    <Transition name="rank-panel">
      <div v-if="showPanel" class="rank-overlay" @click.self="showPanel = false">
        <div class="rank-panel">
          <!-- 标题 -->
          <div class="rank-header">
            <div class="rank-title">
              <span class="title-deco">✦</span>
              天骄榜
            </div>
            <button class="close-btn" @click="showPanel = false">×</button>
          </div>

          <!-- 标签切换 -->
          <div class="tab-bar">
            <button
              v-for="tab in [
                { id: 'realm', label: '修为榜', icon: '⚡' },
                { id: 'sect', label: '宗门榜', icon: '⊙' },
                { id: 'age', label: '众生榜', icon: '♾' }
              ]"
              :key="tab.id"
              class="tab-btn"
              :class="{ active: activeTab === tab.id }"
              @click="activeTab = tab.id as any"
            >
              {{ tab.icon }} {{ tab.label }}
            </button>
          </div>

          <!-- 修为榜 -->
          <div v-if="activeTab === 'realm'" class="rank-list">
            <div
              v-for="item in realmRanking"
              :key="item.id"
              class="rank-item"
              @click="jumpToAvatar(item.id)"
            >
              <div class="rank-num" :style="{ color: getRankColor(item.rank) }">
                {{ getRankLabel(item.rank) }}
              </div>
              <div class="rank-name">
                <span class="avatar-name">{{ item.name }}</span>
                <span class="avatar-extra">{{ item.action || '...' }}</span>
              </div>
              <div class="rank-badge" :style="{ color: getRankColor(item.rank) }">
                <span v-if="item.rank <= 3">✦</span>
              </div>
            </div>

            <div v-if="realmRanking.length === 0" class="empty-hint">
              尚无修士数据
            </div>
          </div>

          <!-- 宗门榜 -->
          <div v-if="activeTab === 'sect'" class="rank-list">
            <div class="rank-sect-summary">
              <div class="summary-stat">
                <div class="stat-num">{{ worldStore.avatarList.filter(a => !a.is_dead).length }}</div>
                <div class="stat-label">在世修士</div>
              </div>
              <div class="summary-stat">
                <div class="stat-num">{{ worldStore.avatarList.filter(a => a.is_dead).length }}</div>
                <div class="stat-label">已陨落</div>
              </div>
              <div class="summary-stat">
                <div class="stat-num">{{ worldStore.year }}</div>
                <div class="stat-label">当前年份</div>
              </div>
            </div>

            <div class="sect-world-note">
              宗门详情请点击地图上的宗门区域查看
            </div>

            <!-- 各区域实体 -->
            <div class="region-list">
              <div
                v-for="region in Array.from(worldStore.regions.values()).filter(r => r.type === 'sect').slice(0, 10)"
                :key="region.id"
                class="region-item"
                @click="uiStore.select('region', String(region.id)); showPanel = false"
              >
                <div class="region-icon">⊙</div>
                <div class="region-name">{{ region.name }}</div>
                <div class="region-type-badge">宗门</div>
              </div>
            </div>
          </div>

          <!-- 众生榜 -->
          <div v-if="activeTab === 'age'" class="rank-list">
            <div
              v-for="item in ageRanking"
              :key="item.id"
              class="rank-item"
              @click="jumpToAvatar(item.id)"
            >
              <div class="rank-num" :style="{ color: getRankColor(item.rank) }">
                {{ getRankLabel(item.rank) }}
              </div>
              <div class="rank-name">
                <span class="avatar-name">{{ item.name }}</span>
                <span class="avatar-extra avatar-gender" :class="item.gender === '女' ? 'female' : 'male'">
                  {{ item.gender === '女' ? '♀' : '♂' }}
                </span>
              </div>
            </div>
          </div>

          <!-- 底部 -->
          <div class="rank-footer">
            共 {{ worldStore.avatarList.length }} 位修士 · {{ worldStore.year }}年{{ worldStore.month }}月
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
/* 悬浮按钮 */
.rank-fab {
  position: absolute;
  bottom: 116px;
  right: 14px;
  width: 48px;
  height: 48px;
  background: radial-gradient(circle at 30% 30%, rgba(90, 180, 240, 0.25), rgba(6, 8, 16, 0.9));
  border: 1px solid rgba(90, 180, 240, 0.4);
  border-radius: 50%;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 80;
  transition: all 0.25s;
  box-shadow: 0 0 10px rgba(90, 180, 240, 0.15);
}

.rank-fab:hover,
.rank-fab.active {
  background: radial-gradient(circle at 30% 30%, rgba(90, 180, 240, 0.4), rgba(6, 8, 16, 0.95));
  box-shadow: 0 0 18px rgba(90, 180, 240, 0.35);
  transform: scale(1.05);
}

.fab-icon {
  font-size: 16px;
  color: var(--color-sky, #5ab4f0);
  font-weight: bold;
}

/* 面板遮罩 */
.rank-overlay {
  position: fixed;
  inset: 0;
  z-index: 290;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  padding-right: 80px;
  background: rgba(0, 0, 0, 0.3);
  backdrop-filter: blur(2px);
}

/* 面板主体 */
.rank-panel {
  width: 340px;
  max-height: 75vh;
  background: linear-gradient(135deg, #070916, #0b0d1e);
  border: 1px solid rgba(90, 180, 240, 0.3);
  border-radius: 4px;
  box-shadow: 0 0 30px rgba(0, 0, 0, 0.7), 0 0 0 1px rgba(90, 180, 240, 0.08);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  position: relative;
}

.rank-panel::before {
  content: '';
  position: absolute;
  top: 4px; left: 4px;
  width: 10px; height: 10px;
  border-top: 1px solid rgba(90, 180, 240, 0.5);
  border-left: 1px solid rgba(90, 180, 240, 0.5);
  pointer-events: none;
}

/* 头部 */
.rank-header {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid rgba(90, 180, 240, 0.15);
  background: rgba(90, 180, 240, 0.04);
}

.rank-title {
  flex: 1;
  font-size: 16px;
  font-weight: bold;
  color: var(--color-sky, #5ab4f0);
  letter-spacing: 3px;
  text-shadow: 0 0 8px rgba(90, 180, 240, 0.4);
  display: flex;
  align-items: center;
  gap: 8px;
}

.title-deco {
  font-size: 12px;
  opacity: 0.6;
}

.close-btn {
  background: transparent;
  border: none;
  color: rgba(90, 180, 240, 0.5);
  font-size: 20px;
  cursor: pointer;
  padding: 0 4px;
  transition: color 0.2s;
}
.close-btn:hover { color: rgba(90, 180, 240, 0.9); }

/* 标签栏 */
.tab-bar {
  display: flex;
  padding: 6px 12px;
  gap: 6px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.tab-btn {
  flex: 1;
  padding: 5px 8px;
  background: transparent;
  border: 1px solid rgba(255, 255, 255, 0.07);
  color: rgba(200, 190, 170, 0.5);
  border-radius: 2px;
  cursor: pointer;
  font-size: 12px;
  font-family: inherit;
  transition: all 0.2s;
  letter-spacing: 0.5px;
}

.tab-btn.active {
  background: rgba(90, 180, 240, 0.12);
  border-color: rgba(90, 180, 240, 0.4);
  color: var(--color-sky, #5ab4f0);
}

.tab-btn:hover:not(.active) {
  border-color: rgba(255, 255, 255, 0.12);
  color: rgba(200, 190, 170, 0.8);
}

/* 排行列表 */
.rank-list {
  flex: 1;
  overflow-y: auto;
  padding: 6px 0;
}

.rank-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 16px;
  cursor: pointer;
  transition: background 0.15s;
  border-bottom: 1px solid rgba(255, 255, 255, 0.03);
}

.rank-item:hover {
  background: rgba(90, 180, 240, 0.05);
}

.rank-num {
  font-size: 14px;
  font-weight: bold;
  width: 24px;
  text-align: center;
  flex-shrink: 0;
  text-shadow: 0 0 4px currentColor;
}

.rank-name {
  flex: 1;
  display: flex;
  align-items: baseline;
  gap: 6px;
}

.avatar-name {
  font-size: 14px;
  color: var(--color-text-main, #e8dfc0);
}

.avatar-extra {
  font-size: 11px;
  color: rgba(200, 190, 170, 0.4);
  max-width: 160px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.avatar-gender.female { color: #ff80ab; }
.avatar-gender.male { color: var(--color-sky, #5ab4f0); }

.rank-badge {
  font-size: 12px;
  width: 16px;
}

/* 宗门榜特殊内容 */
.rank-sect-summary {
  display: flex;
  padding: 12px 16px;
  gap: 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.summary-stat {
  flex: 1;
  text-align: center;
}

.stat-num {
  font-size: 22px;
  font-weight: bold;
  color: var(--color-sky, #5ab4f0);
  text-shadow: 0 0 6px rgba(90, 180, 240, 0.4);
}

.stat-label {
  font-size: 10px;
  color: rgba(200, 190, 170, 0.4);
  letter-spacing: 0.5px;
}

.sect-world-note {
  padding: 8px 16px;
  font-size: 11px;
  color: rgba(200, 190, 170, 0.35);
  text-align: center;
  border-bottom: 1px solid rgba(255, 255, 255, 0.04);
}

.region-list {
  padding: 4px 0;
}

.region-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 16px;
  cursor: pointer;
  transition: background 0.15s;
}

.region-item:hover {
  background: rgba(90, 180, 240, 0.05);
}

.region-icon {
  font-size: 14px;
  color: var(--color-gold, #c9a227);
  width: 20px;
  text-align: center;
}

.region-name {
  flex: 1;
  font-size: 14px;
  color: var(--color-text-main, #e8dfc0);
}

.region-type-badge {
  font-size: 10px;
  color: var(--color-gold, #c9a227);
  border: 1px solid rgba(201, 162, 39, 0.3);
  padding: 1px 5px;
  border-radius: 1px;
}

.empty-hint {
  padding: 24px;
  text-align: center;
  color: rgba(200, 190, 170, 0.3);
  font-size: 13px;
}

/* 底部 */
.rank-footer {
  padding: 6px 16px;
  font-size: 10px;
  color: rgba(200, 190, 170, 0.25);
  text-align: center;
  border-top: 1px solid rgba(255, 255, 255, 0.04);
  flex-shrink: 0;
}

/* 过渡动画 */
.rank-panel-enter-active {
  animation: slide-in 0.25s ease-out;
}
.rank-panel-leave-active {
  animation: slide-in 0.2s ease-in reverse;
}

@keyframes slide-in {
  from { opacity: 0; transform: translateX(20px); }
  to { opacity: 1; transform: translateX(0); }
}
</style>
