<script setup lang="ts">
/**
 * 世界危机预警组件
 * 监控事件流，检测兽潮/魔道入侵/天地异变等危机事件，显示全屏预警
 */
import { ref, watch, computed } from 'vue'
import { useWorldStore } from '../../stores/world'

const worldStore = useWorldStore()

interface Crisis {
  id: string
  type: 'beast_tide' | 'demon_invasion' | 'world_upheaval' | 'war'
  title: string
  desc: string
  level: 'warning' | 'danger' | 'critical'
  time: string
}

const activeCrises = ref<Crisis[]>([])
const dismissedIds = ref<Set<string>>(new Set())

// 危机关键词检测
const CRISIS_PATTERNS = [
  {
    type: 'beast_tide' as const,
    patterns: /兽潮|魔兽潮|妖兽暴动|兽群来袭/,
    title: '兽潮来袭',
    level: 'danger' as const,
    color: '#e05555'
  },
  {
    type: 'demon_invasion' as const,
    patterns: /魔道入侵|魔族|正魔大战|魔道崛起|天魔降临/,
    title: '魔道入侵',
    level: 'critical' as const,
    color: '#a070ff'
  },
  {
    type: 'world_upheaval' as const,
    patterns: /天地异变|灵气暴走|天地崩塌|虚空破碎|世界法则/,
    title: '天地异变',
    level: 'warning' as const,
    color: '#f0c040'
  },
  {
    type: 'war' as const,
    patterns: /宗门大战|覆灭|灭门|宗门覆灭|宗主陨落/,
    title: '大战爆发',
    level: 'danger' as const,
    color: '#ff7a30'
  }
]

// 监听事件流，检测危机
watch(() => worldStore.events.length, () => {
  if (!worldStore.events.length) return

  // 只检查最新的一批事件（最近10条）
  const recent = worldStore.events.slice(-5)

  for (const event of recent) {
    const text = event.content || event.text || ''
    if (!event.isMajor) continue

    for (const pattern of CRISIS_PATTERNS) {
      if (pattern.patterns.test(text)) {
        const crisisId = `${event.id}_${pattern.type}`
        if (!dismissedIds.value.has(crisisId) && !activeCrises.value.find(c => c.id === crisisId)) {
          activeCrises.value.push({
            id: crisisId,
            type: pattern.type,
            title: pattern.title,
            desc: text.slice(0, 80),
            level: pattern.level,
            time: `${event.year}年${event.month}月`
          })

          // 20秒后自动消失
          setTimeout(() => {
            dismissCrisis(crisisId)
          }, 20000)
        }
      }
    }
  }
})

function dismissCrisis(id: string) {
  dismissedIds.value.add(id)
  activeCrises.value = activeCrises.value.filter(c => c.id !== id)
}

function getCrisisColor(level: string) {
  if (level === 'critical') return '#a070ff'
  if (level === 'danger') return '#e05555'
  return '#f0c040'
}
</script>

<template>
  <div class="crisis-container" aria-live="assertive">
    <TransitionGroup name="crisis-alert" tag="div" class="crisis-list">
      <div
        v-for="crisis in activeCrises"
        :key="crisis.id"
        class="crisis-alert"
        :class="`level-${crisis.level}`"
        :style="{ '--crisis-color': getCrisisColor(crisis.level) }"
      >
        <!-- 闪烁边框 -->
        <div class="crisis-border-anim"></div>

        <!-- 内容 -->
        <div class="crisis-icon">
          <span v-if="crisis.type === 'beast_tide'">⚡</span>
          <span v-else-if="crisis.type === 'demon_invasion'">☁</span>
          <span v-else-if="crisis.type === 'world_upheaval'">◈</span>
          <span v-else>⚔</span>
        </div>
        <div class="crisis-body">
          <div class="crisis-level-tag">{{ crisis.level === 'critical' ? '极危' : crisis.level === 'danger' ? '危急' : '警告' }}</div>
          <div class="crisis-title">{{ crisis.title }}</div>
          <div class="crisis-desc">{{ crisis.desc }}</div>
          <div class="crisis-time">{{ crisis.time }}</div>
        </div>
        <button class="crisis-dismiss" @click="dismissCrisis(crisis.id)">×</button>
      </div>
    </TransitionGroup>
  </div>
</template>

<style scoped>
.crisis-container {
  position: absolute;
  top: 50px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 95;
  pointer-events: none;
  width: 360px;
}

.crisis-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.crisis-alert {
  position: relative;
  background: rgba(6, 8, 16, 0.95);
  border: 1px solid var(--crisis-color);
  border-radius: 3px;
  padding: 12px 40px 12px 16px;
  display: flex;
  align-items: flex-start;
  gap: 12px;
  pointer-events: auto;
  box-shadow: 0 0 20px rgba(0, 0, 0, 0.6), 0 0 8px color-mix(in srgb, var(--crisis-color) 30%, transparent);
  overflow: hidden;
}

/* 闪烁边框动画 */
.crisis-border-anim {
  position: absolute;
  inset: 0;
  border: 1px solid var(--crisis-color);
  border-radius: 3px;
  animation: border-flash 1s ease-in-out infinite;
  pointer-events: none;
  opacity: 0;
}

@keyframes border-flash {
  0%, 100% { opacity: 0; }
  50% { opacity: 0.6; }
}

.crisis-alert.level-critical .crisis-border-anim {
  animation-duration: 0.5s;
}

/* 侧边色条 */
.crisis-alert::before {
  content: '';
  position: absolute;
  left: 0; top: 0; bottom: 0;
  width: 3px;
  background: var(--crisis-color);
  box-shadow: 0 0 8px var(--crisis-color);
}

.crisis-icon {
  font-size: 20px;
  color: var(--crisis-color);
  flex-shrink: 0;
  text-shadow: 0 0 8px currentColor;
  animation: icon-pulse 1.5s ease-in-out infinite;
}

@keyframes icon-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.crisis-body {
  flex: 1;
  min-width: 0;
}

.crisis-level-tag {
  font-size: 9px;
  color: var(--crisis-color);
  letter-spacing: 2px;
  margin-bottom: 2px;
  opacity: 0.8;
}

.crisis-title {
  font-size: 15px;
  font-weight: bold;
  color: var(--crisis-color);
  text-shadow: 0 0 6px currentColor;
  letter-spacing: 1px;
  margin-bottom: 4px;
}

.crisis-desc {
  font-size: 11px;
  color: rgba(200, 190, 170, 0.6);
  line-height: 1.4;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.crisis-time {
  font-size: 10px;
  color: rgba(200, 190, 170, 0.3);
  margin-top: 4px;
}

.crisis-dismiss {
  position: absolute;
  top: 8px;
  right: 8px;
  background: transparent;
  border: none;
  color: rgba(200, 190, 170, 0.3);
  font-size: 16px;
  cursor: pointer;
  padding: 0 4px;
  line-height: 1;
  transition: color 0.2s;
}

.crisis-dismiss:hover {
  color: rgba(200, 190, 170, 0.8);
}

/* 过渡动画 */
.crisis-alert-enter-active {
  animation: crisis-enter 0.4s ease-out;
}
.crisis-alert-leave-active {
  animation: crisis-enter 0.3s ease-in reverse;
  pointer-events: none;
}

@keyframes crisis-enter {
  from { opacity: 0; transform: translateY(-16px) scale(0.96); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}
</style>
