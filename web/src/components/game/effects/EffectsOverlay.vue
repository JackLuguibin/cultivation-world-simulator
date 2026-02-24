<script setup lang="ts">
/**
 * 特效覆盖层 - 负责境界突破、天劫等全屏特效动画
 * 通过监听事件流，检测到突破/天劫/奇遇等关键词时触发动画
 */
import { ref, watch } from 'vue'
import { useWorldStore } from '../../../stores/world'

interface SpecialEffect {
  id: string
  type: 'breakthrough' | 'tribulation' | 'fortune' | 'battle'
  name: string
  x: number
  y: number
}

const worldStore = useWorldStore()
const activeEffects = ref<SpecialEffect[]>([])

let effectCounter = 0

// 监听新事件，检测特殊事件并触发特效
watch(() => worldStore.events, (newEvents, oldEvents) => {
  if (!newEvents || !oldEvents) return
  if (newEvents.length <= oldEvents.length) return

  // 只处理最新的事件（末尾新增的）
  const latestEvent = newEvents[newEvents.length - 1]
  if (!latestEvent) return

  const text = latestEvent.content || latestEvent.text || ''
  
  let effectType: SpecialEffect['type'] | null = null
  if (/突破成功|境界晋升|突破了|渡过天劫/.test(text)) {
    effectType = 'breakthrough'
  } else if (/天劫降临|渡劫|劫雷|天劫/.test(text)) {
    effectType = 'tribulation'
  } else if (/奇遇|机缘|获得宝物|传承/.test(text)) {
    effectType = 'fortune'
  } else if (latestEvent.isMajor && /大战|激战|击杀|覆灭/.test(text)) {
    effectType = 'battle'
  }

  if (effectType) {
    const effect: SpecialEffect = {
      id: `effect_${effectCounter++}`,
      type: effectType,
      name: latestEvent.text.slice(0, 30),
      x: Math.random() * 60 + 20, // 随机位置 20-80%
      y: Math.random() * 40 + 20
    }
    activeEffects.value = [...activeEffects.value, effect]

    // 自动移除特效
    const duration = effectType === 'tribulation' ? 3000 : 2000
    setTimeout(() => {
      activeEffects.value = activeEffects.value.filter(e => e.id !== effect.id)
    }, duration)
  }
}, { deep: false })
</script>

<template>
  <div class="effects-overlay" aria-hidden="true">
    <transition-group name="effect" tag="div">
      <div
        v-for="effect in activeEffects"
        :key="effect.id"
        class="effect-container"
        :class="`effect-${effect.type}`"
        :style="{ left: effect.x + '%', top: effect.y + '%' }"
      >
        <!-- 突破：金色光柱 -->
        <template v-if="effect.type === 'breakthrough'">
          <div class="pillar-beam"></div>
          <div class="pillar-glow"></div>
          <div class="pillar-rings">
            <div class="ring ring-1"></div>
            <div class="ring ring-2"></div>
            <div class="ring ring-3"></div>
          </div>
          <div class="effect-label gold">境界突破</div>
        </template>

        <!-- 天劫：紫色雷电 -->
        <template v-else-if="effect.type === 'tribulation'">
          <div class="lightning-bolt"></div>
          <div class="lightning-bolt bolt-2"></div>
          <div class="tribulation-cloud"></div>
          <div class="effect-label purple">天劫降临</div>
        </template>

        <!-- 奇遇：绿色光粒 -->
        <template v-else-if="effect.type === 'fortune'">
          <div class="fortune-burst">
            <div v-for="i in 8" :key="i" class="fortune-particle" :style="{ '--i': i }"></div>
          </div>
          <div class="effect-label jade">奇遇降临</div>
        </template>

        <!-- 大战：红色冲击 -->
        <template v-else-if="effect.type === 'battle'">
          <div class="battle-shockwave"></div>
          <div class="battle-shockwave wave-2"></div>
          <div class="effect-label red">大战爆发</div>
        </template>
      </div>
    </transition-group>
  </div>
</template>

<style scoped>
.effects-overlay {
  position: absolute;
  inset: 0;
  pointer-events: none;
  z-index: 50;
  overflow: hidden;
}

.effect-container {
  position: absolute;
  transform: translate(-50%, -50%);
  width: 120px;
  height: 200px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-end;
}

/* === 突破特效 - 金色光柱 === */
.pillar-beam {
  position: absolute;
  bottom: 0;
  width: 16px;
  height: 160px;
  background: linear-gradient(to top, transparent, rgba(240, 192, 64, 0.9), rgba(240, 192, 64, 0.4), transparent);
  border-radius: 8px;
  animation: pillar-rise 2s ease-out forwards;
  filter: blur(2px);
}

.pillar-glow {
  position: absolute;
  bottom: 0;
  width: 40px;
  height: 100px;
  background: radial-gradient(ellipse at bottom, rgba(240, 192, 64, 0.5), transparent);
  animation: pillar-glow-anim 2s ease-out forwards;
}

.pillar-rings {
  position: absolute;
  bottom: 20px;
}

.ring {
  position: absolute;
  border-radius: 50%;
  border: 2px solid rgba(240, 192, 64, 0.7);
  transform: translate(-50%, -50%);
  left: 50%;
  top: 50%;
}

.ring-1 { width: 40px; height: 20px; animation: ring-expand 1.5s ease-out 0.1s forwards; }
.ring-2 { width: 70px; height: 35px; animation: ring-expand 1.5s ease-out 0.3s forwards; border-color: rgba(240, 192, 64, 0.5); }
.ring-3 { width: 100px; height: 50px; animation: ring-expand 1.5s ease-out 0.5s forwards; border-color: rgba(240, 192, 64, 0.3); }

@keyframes pillar-rise {
  0% { transform: scaleY(0); opacity: 0; transform-origin: bottom; }
  20% { opacity: 1; transform: scaleY(1); }
  80% { opacity: 0.8; }
  100% { opacity: 0; }
}

@keyframes pillar-glow-anim {
  0% { opacity: 0; }
  30% { opacity: 1; }
  100% { opacity: 0; }
}

@keyframes ring-expand {
  0% { transform: translate(-50%, -50%) scale(0.1); opacity: 1; }
  100% { transform: translate(-50%, -50%) scale(3); opacity: 0; }
}

/* === 天劫特效 - 紫色雷电 === */
.lightning-bolt {
  position: absolute;
  top: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 4px;
  height: 140px;
  background: linear-gradient(to bottom, rgba(170, 100, 255, 0.9), rgba(120, 50, 255, 0.8), rgba(80, 20, 200, 0));
  clip-path: polygon(30% 0, 100% 40%, 55% 40%, 80% 100%, 0 50%, 45% 50%);
  width: 30px;
  animation: lightning-flash 0.15s steps(1) infinite;
  filter: drop-shadow(0 0 8px rgba(170, 100, 255, 0.8));
}

.bolt-2 {
  left: 60%;
  height: 100px;
  opacity: 0.7;
  animation-delay: 0.07s;
  transform: translateX(-50%) scaleX(-1);
}

.tribulation-cloud {
  position: absolute;
  top: -20px;
  width: 120px;
  height: 40px;
  background: radial-gradient(ellipse, rgba(80, 20, 160, 0.7), rgba(50, 10, 100, 0.5), transparent);
  border-radius: 50%;
  animation: cloud-pulse 0.5s ease-in-out infinite alternate;
  filter: blur(4px);
}

@keyframes lightning-flash {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.2; }
}

@keyframes cloud-pulse {
  from { transform: scale(1); opacity: 0.7; }
  to { transform: scale(1.1); opacity: 1; }
}

/* === 奇遇特效 - 翠玉粒子 === */
.fortune-burst {
  position: absolute;
  bottom: 20px;
}

.fortune-particle {
  position: absolute;
  width: 6px;
  height: 6px;
  background: var(--color-jade, #3ddbb0);
  border-radius: 50%;
  box-shadow: 0 0 6px var(--color-jade, #3ddbb0);
  animation: particle-fly 1.8s ease-out forwards;
  --angle: calc(var(--i) * 45deg);
  animation-delay: calc(var(--i) * 0.05s);
}

@keyframes particle-fly {
  0% { transform: translate(0, 0) scale(1); opacity: 1; }
  100% {
    transform: 
      translate(calc(cos(var(--angle)) * 60px), calc(sin(var(--angle)) * -60px))
      scale(0);
    opacity: 0;
  }
}

/* === 大战特效 - 红色冲击波 === */
.battle-shockwave {
  position: absolute;
  bottom: 20px;
  width: 10px;
  height: 10px;
  border: 3px solid rgba(224, 85, 85, 0.8);
  border-radius: 50%;
  animation: shockwave-expand 1s ease-out forwards;
}

.wave-2 {
  animation-delay: 0.3s;
  border-color: rgba(224, 85, 85, 0.5);
}

@keyframes shockwave-expand {
  0% { transform: scale(1); opacity: 1; }
  100% { transform: scale(15); opacity: 0; }
}

/* === 标签 === */
.effect-label {
  position: absolute;
  bottom: -24px;
  font-size: 11px;
  letter-spacing: 2px;
  white-space: nowrap;
  font-weight: bold;
  text-shadow: 0 0 8px currentColor;
  animation: label-fade 2s ease-out forwards;
}

.effect-label.gold { color: #f0c040; }
.effect-label.purple { color: #a070ff; }
.effect-label.jade { color: #3ddbb0; }
.effect-label.red { color: #e05555; }

@keyframes label-fade {
  0% { opacity: 0; transform: translateY(5px); }
  20% { opacity: 1; transform: translateY(0); }
  80% { opacity: 1; }
  100% { opacity: 0; transform: translateY(-10px); }
}

/* === 过渡动画 === */
.effect-enter-active { animation: effect-in 0.3s ease-out; }
.effect-leave-active { animation: effect-in 0.3s ease-in reverse; }

@keyframes effect-in {
  from { opacity: 0; transform: translate(-50%, -50%) scale(0.5); }
  to { opacity: 1; transform: translate(-50%, -50%) scale(1); }
}
</style>
