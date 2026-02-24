<script setup lang="ts">
/**
 * 比武大会面板
 * 展示当前世界的比武信息、战报历史
 * 后端触发后通过事件流推送战果
 */
import { ref, computed } from 'vue'
import { useWorldStore } from '../../../stores/world'
import { useUiStore } from '../../../stores/ui'

const worldStore = useWorldStore()
const uiStore = useUiStore()

const showPanel = ref(false)
const activeTab = ref<'bracket' | 'records'>('records')

// 从事件流过滤出比武相关事件
const tournamentEvents = computed(() => {
  return worldStore.events
    .filter(e => {
      const text = e.content || e.text || ''
      return /比武|切磋|胜出|擂台|武道|大比|冠军|决战/.test(text)
    })
    .slice(-30)
    .reverse()
})

// 模拟比武榜单（实际应由后端推送）
const bracketData = computed(() => {
  const avatars = worldStore.avatarList.filter(a => !a.is_dead).slice(0, 8)
  if (avatars.length < 2) return []

  // 模拟淘汰赛对阵
  const rounds = []
  let pool = [...avatars]

  while (pool.length > 1) {
    const round = []
    for (let i = 0; i < pool.length - 1; i += 2) {
      round.push({
        a: pool[i],
        b: pool[i + 1],
        winner: Math.random() > 0.5 ? pool[i] : pool[i + 1]
      })
    }
    rounds.push(round)
    pool = round.map(m => m.winner)
  }

  return { rounds, champion: pool[0] }
})

function getEventIcon(text: string) {
  if (/胜|赢|冠军/.test(text)) return '🏆'
  if (/败|输/.test(text)) return '⚔'
  return '◎'
}

function jumpToAvatar(id: string) {
  uiStore.select('avatar', id)
}

function formatTime(e: { year: number; month: number }) {
  return `${e.year}年${e.month}月`
}
</script>

<template>
  <!-- 悬浮按钮 -->
  <div class="tournament-fab" @click="showPanel = !showPanel" :class="{ active: showPanel }">
    <span class="fab-icon">武</span>
  </div>

  <!-- 比武面板 -->
  <Teleport to="body">
    <Transition name="tournament-panel">
      <div v-if="showPanel" class="tournament-overlay" @click.self="showPanel = false">
        <div class="tournament-panel">
          <!-- 标题 -->
          <div class="tournament-header">
            <div class="tournament-title">
              <span class="title-deco">⚔</span>
              武道大会
            </div>
            <div class="tab-bar">
              <button :class="{ active: activeTab === 'records' }" @click="activeTab = 'records'">战报</button>
              <button :class="{ active: activeTab === 'bracket' }" @click="activeTab = 'bracket'">对阵</button>
            </div>
            <button class="close-btn" @click="showPanel = false">×</button>
          </div>

          <!-- 战报 -->
          <div v-if="activeTab === 'records'" class="records-body">
            <div v-if="tournamentEvents.length === 0" class="empty-state">
              <div class="empty-icon">⚔</div>
              <div class="empty-text">尚无比武记录</div>
              <div class="empty-hint">世间修士切磋对决时，战报将在此处自动汇聚</div>
            </div>

            <div
              v-for="event in tournamentEvents"
              :key="event.id"
              class="battle-record"
              :class="{ 'is-major': event.isMajor }"
            >
              <div class="record-meta">
                <span class="record-time">{{ formatTime(event) }}</span>
                <span class="record-icon">{{ getEventIcon(event.text) }}</span>
                <span v-if="event.isMajor" class="record-badge">精彩</span>
              </div>
              <div class="record-text">{{ event.text }}</div>
              <div v-if="event.content && event.isStory" class="record-detail">
                {{ event.content }}
              </div>
            </div>
          </div>

          <!-- 对阵图 -->
          <div v-if="activeTab === 'bracket'" class="bracket-body">
            <div v-if="!bracketData || (bracketData as any).rounds?.length === 0" class="empty-state">
              <div class="empty-icon">🏆</div>
              <div class="empty-text">等待比武大会</div>
              <div class="empty-hint">大会开启后将展示对阵淘汰图</div>
            </div>

            <div v-else class="bracket-view">
              <!-- 冠军 -->
              <div class="champion-block" v-if="(bracketData as any).champion">
                <div class="champion-label">✦ 冠军 ✦</div>
                <div
                  class="champion-name"
                  @click="jumpToAvatar((bracketData as any).champion.id)"
                >
                  {{ (bracketData as any).champion.name }}
                </div>
              </div>

              <!-- 对阵轮次 -->
              <div class="rounds">
                <div
                  v-for="(round, rIdx) in (bracketData as any).rounds"
                  :key="rIdx"
                  class="round"
                >
                  <div class="round-title">第{{ rIdx + 1 }}轮</div>
                  <div
                    v-for="(match, mIdx) in round"
                    :key="mIdx"
                    class="match-card"
                  >
                    <div
                      class="fighter"
                      :class="{ winner: match.winner.id === match.a.id }"
                      @click="jumpToAvatar(match.a.id)"
                    >
                      {{ match.a.name }}
                    </div>
                    <div class="vs">VS</div>
                    <div
                      class="fighter"
                      :class="{ winner: match.winner.id === match.b.id }"
                      @click="jumpToAvatar(match.b.id)"
                    >
                      {{ match.b.name }}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 底部 -->
          <div class="tournament-footer">
            武道乃修士根本，以战证道，方得真意
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
/* 悬浮按钮 */
.tournament-fab {
  position: absolute;
  bottom: 228px;
  right: 14px;
  width: 48px;
  height: 48px;
  background: radial-gradient(circle at 30% 30%, rgba(224, 85, 85, 0.2), rgba(6, 8, 16, 0.9));
  border: 1px solid rgba(224, 85, 85, 0.35);
  border-radius: 50%;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 80;
  transition: all 0.25s;
  box-shadow: 0 0 8px rgba(224, 85, 85, 0.12);
}

.tournament-fab:hover,
.tournament-fab.active {
  background: radial-gradient(circle at 30% 30%, rgba(224, 85, 85, 0.35), rgba(6, 8, 16, 0.95));
  box-shadow: 0 0 16px rgba(224, 85, 85, 0.3);
  transform: scale(1.05);
}

.fab-icon {
  font-size: 16px;
  color: var(--color-danger, #e05555);
  font-weight: bold;
}

/* 遮罩 */
.tournament-overlay {
  position: fixed;
  inset: 0;
  z-index: 270;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.35);
  backdrop-filter: blur(2px);
}

/* 面板 */
.tournament-panel {
  width: 500px;
  max-height: 78vh;
  background: linear-gradient(135deg, #0a0608, #12080e);
  border: 1px solid rgba(224, 85, 85, 0.25);
  border-radius: 4px;
  box-shadow: 0 0 40px rgba(0, 0, 0, 0.8), 0 0 0 1px rgba(224, 85, 85, 0.08);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  position: relative;
}

.tournament-panel::before {
  content: '';
  position: absolute;
  top: 4px; left: 4px;
  width: 12px; height: 12px;
  border-top: 1px solid rgba(224, 85, 85, 0.5);
  border-left: 1px solid rgba(224, 85, 85, 0.5);
  pointer-events: none;
}

/* 头部 */
.tournament-header {
  display: flex;
  align-items: center;
  padding: 12px 20px;
  border-bottom: 1px solid rgba(224, 85, 85, 0.15);
  background: rgba(224, 85, 85, 0.04);
  gap: 12px;
}

.tournament-title {
  flex: 1;
  font-size: 16px;
  font-weight: bold;
  color: var(--color-danger, #e05555);
  letter-spacing: 3px;
  text-shadow: 0 0 8px rgba(224, 85, 85, 0.4);
  display: flex;
  align-items: center;
  gap: 8px;
}

.title-deco {
  font-size: 14px;
  opacity: 0.7;
}

.tab-bar {
  display: flex;
  gap: 4px;
}

.tab-bar button {
  background: transparent;
  border: 1px solid rgba(224, 85, 85, 0.2);
  color: rgba(200, 190, 170, 0.4);
  padding: 3px 10px;
  font-size: 12px;
  border-radius: 1px;
  cursor: pointer;
  font-family: inherit;
  transition: all 0.2s;
}

.tab-bar button.active {
  background: rgba(224, 85, 85, 0.12);
  border-color: rgba(224, 85, 85, 0.4);
  color: var(--color-danger, #e05555);
}

.close-btn {
  background: transparent;
  border: none;
  color: rgba(224, 85, 85, 0.4);
  font-size: 20px;
  cursor: pointer;
  padding: 0 4px;
  transition: color 0.2s;
}
.close-btn:hover { color: rgba(224, 85, 85, 0.9); }

/* 战报列表 */
.records-body {
  flex: 1;
  overflow-y: auto;
  padding: 8px 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.empty-state {
  padding: 32px 20px;
  text-align: center;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.empty-icon {
  font-size: 32px;
  opacity: 0.3;
}

.empty-text {
  font-size: 14px;
  color: rgba(200, 190, 170, 0.4);
}

.empty-hint {
  font-size: 11px;
  color: rgba(200, 190, 170, 0.25);
  line-height: 1.5;
}

.battle-record {
  padding: 10px 12px;
  background: rgba(0, 0, 0, 0.25);
  border: 1px solid rgba(224, 85, 85, 0.1);
  border-left: 2px solid rgba(224, 85, 85, 0.4);
  border-radius: 2px;
  transition: border-color 0.2s;
}

.battle-record.is-major {
  border-left-color: #f0c040;
  background: rgba(201, 162, 39, 0.05);
}

.battle-record:hover {
  border-color: rgba(224, 85, 85, 0.25);
}

.record-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 5px;
}

.record-time {
  font-size: 10px;
  color: rgba(200, 190, 170, 0.35);
}

.record-icon {
  font-size: 11px;
}

.record-badge {
  font-size: 9px;
  color: #f0c040;
  border: 1px solid rgba(240, 192, 64, 0.3);
  padding: 0 4px;
  border-radius: 1px;
}

.record-text {
  font-size: 13px;
  color: var(--color-text-main, #e8dfc0);
  line-height: 1.6;
}

.record-detail {
  margin-top: 6px;
  font-size: 11px;
  color: rgba(200, 190, 170, 0.45);
  line-height: 1.5;
  padding-top: 5px;
  border-top: 1px dashed rgba(255, 255, 255, 0.05);
}

/* 对阵图 */
.bracket-body {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.bracket-view {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.champion-block {
  text-align: center;
  padding: 12px;
  background: rgba(201, 162, 39, 0.1);
  border: 1px solid rgba(201, 162, 39, 0.3);
  border-radius: 3px;
}

.champion-label {
  font-size: 11px;
  color: rgba(201, 162, 39, 0.6);
  letter-spacing: 2px;
  margin-bottom: 4px;
}

.champion-name {
  font-size: 18px;
  font-weight: bold;
  color: #f0c040;
  text-shadow: 0 0 10px rgba(240, 192, 64, 0.5);
  cursor: pointer;
}

.champion-name:hover {
  text-decoration: underline;
}

.rounds {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.round {}

.round-title {
  font-size: 11px;
  color: rgba(224, 85, 85, 0.5);
  letter-spacing: 1px;
  margin-bottom: 6px;
}

.match-card {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 2px;
  margin-bottom: 4px;
}

.fighter {
  flex: 1;
  text-align: center;
  font-size: 13px;
  color: rgba(200, 190, 170, 0.5);
  cursor: pointer;
  padding: 4px;
  border-radius: 1px;
  transition: all 0.15s;
}

.fighter:hover {
  color: rgba(200, 190, 170, 0.9);
  background: rgba(255, 255, 255, 0.04);
}

.fighter.winner {
  color: var(--color-gold-bright, #f0c040);
  font-weight: bold;
  text-shadow: 0 0 6px rgba(240, 192, 64, 0.3);
}

.vs {
  font-size: 10px;
  color: rgba(224, 85, 85, 0.5);
  letter-spacing: 1px;
  flex-shrink: 0;
}

/* 底部 */
.tournament-footer {
  padding: 6px 20px;
  font-size: 10px;
  color: rgba(200, 190, 170, 0.2);
  text-align: center;
  border-top: 1px solid rgba(255, 255, 255, 0.04);
  flex-shrink: 0;
  letter-spacing: 0.5px;
}

/* 过渡动画 */
.tournament-panel-enter-active {
  animation: tournament-in 0.25s ease-out;
}
.tournament-panel-leave-active {
  animation: tournament-in 0.2s ease-in reverse;
}

@keyframes tournament-in {
  from { opacity: 0; transform: scale(0.96); }
  to { opacity: 1; transform: scale(1); }
}
</style>
