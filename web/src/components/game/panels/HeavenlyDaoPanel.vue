<script setup lang="ts">
/**
 * 天道干预面板
 * 玩家以"天道"身份干预世界，消耗天道积分施展各种权能
 */
import { ref, computed } from 'vue'
import { useWorldStore } from '../../../stores/world'
import { useUiStore } from '../../../stores/ui'
import { useHeavenlyDaoStore } from '../../../stores/heavenlyDao'

const worldStore = useWorldStore()
const uiStore = useUiStore()
const daoStore = useHeavenlyDaoStore()


const selectedPower = ref<string | null>(null)
const targetAvatarId = ref<string | null>(null)
const confirmPending = ref(false)
const lastActionMsg = ref('')
const showPanel = ref(false)

// 权能定义
interface Power {
  id: string
  name: string
  desc: string
  cost: number
  icon: string
  color: string
  needTarget: boolean
}

const POWERS: Power[] = [
  {
    id: 'fortune',
    name: '降下福缘',
    desc: '赐予指定修士一次奇遇机缘，天降宝物或传承',
    cost: 10,
    icon: '✦',
    color: '#f0c040',
    needTarget: true
  },
  {
    id: 'misfortune',
    name: '散功之祸',
    desc: '使指定修士修为大减，灵台受损',
    cost: 20,
    icon: '⚠',
    color: '#e05555',
    needTarget: true
  },
  {
    id: 'tribulation',
    name: '天雷惩戒',
    desc: '对指定修士降下天劫，考验其道心',
    cost: 30,
    icon: '⚡',
    color: '#a070ff',
    needTarget: true
  },
  {
    id: 'guide',
    name: '机缘引导',
    desc: '引导某修士踏上修炼圣地，获得机缘',
    cost: 15,
    icon: '◎',
    color: '#5ab4f0',
    needTarget: true
  },
  {
    id: 'reincarnate',
    name: '转世重生',
    desc: '重置指定修士的记忆与位置，给予其新的开始',
    cost: 50,
    icon: '∞',
    color: '#3ddbb0',
    needTarget: true
  },
  {
    id: 'awaken',
    name: '点化众生',
    desc: '批量觉醒世间凡人灵根，增加修士数量',
    cost: 40,
    icon: '☯',
    color: '#c9a227',
    needTarget: false
  },
  {
    id: 'prophecy',
    name: '窥视天机',
    desc: '以天道之眼预言某修士未来命运走向，预言有概率成真',
    cost: 25,
    icon: '卜',
    color: '#c9a850',
    needTarget: true
  }
]

// === 预言系统 ===
const prophecyText = ref('')
const showProphecy = ref(false)
const isGeneratingProphecy = ref(false)

// 预言模板集（本地生成，无需LLM）
const PROPHECY_TEMPLATES = [
  '此人命格{fate}，前路{path}，终将{end}。',
  '星象示警，{name}气数{luck}，{event}之日，其命运将现重大转折。',
  '天机不可泄露，然{name}一脉{root}，注定{destiny}。',
  '卦象显示，此人{sign}，宜{good}，忌{bad}，前程{future}。',
  '苍天有眼，{name}之命，系于{factor}，得之则飞升，失之则陨落。'
]

const FATE_OPTIONS = ['大吉', '吉中有凶', '凶中有吉', '大凶转大吉', '命途多舛']
const PATH_OPTIONS = ['顺遂', '坎坷', '迂回曲折', '充满机缘', '险象环生']
const END_OPTIONS = ['成就大道', '含憾而终', '留名青史', '隐居避世', '飞升上界']
const LUCK_OPTIONS = ['昌隆', '衰退', '起伏不定', '潜龙勿用', '一飞冲天']
const DESTINY_OPTIONS = ['立宗开派', '成为一代传奇', '在某场大战中陨落', '得一宝物改命', '与某人纠缠半生']

function pick<T>(arr: T[]): T {
  return arr[Math.floor(Math.random() * arr.length)]
}

function generateProphecy(avatarName: string) {
  isGeneratingProphecy.value = true
  showProphecy.value = false

  // 模拟生成延迟（体验感）
  setTimeout(() => {
    const template = pick(PROPHECY_TEMPLATES)
    const text = template
      .replace('{name}', avatarName || '此人')
      .replace('{fate}', pick(FATE_OPTIONS))
      .replace('{path}', pick(PATH_OPTIONS))
      .replace('{end}', pick(END_OPTIONS))
      .replace('{luck}', pick(LUCK_OPTIONS))
      .replace('{event}', `${worldStore.year + Math.floor(Math.random() * 5) + 1}年`)
      .replace('{destiny}', pick(DESTINY_OPTIONS))
      .replace('{root}', '根骨')
      .replace('{sign}', pick(['乾坤颠倒', '日月争辉', '阴阳失衡', '五行缺土']))
      .replace('{good}', pick(['顺势而为', '广结善缘', '闭关修炼']))
      .replace('{bad}', pick(['轻易出手', '贪图捷径', '与强敌争锋']))
      .replace('{future}', pick(['不可限量', '难逃劫数', '别有洞天']))
      .replace('{factor}', pick(['一枚宝丹', '一段情缘', '一场生死大战', '师门传承']))

    prophecyText.value = `「天机示言」\n\n${text}\n\n——天道于${worldStore.year}年${worldStore.month}月，以天道积分25点探得此卦`
    isGeneratingProphecy.value = false
    showProphecy.value = true
  }, 1200)
}

const canAfford = (cost: number) => daoStore.points >= cost

const selectedPowerDef = computed(() => POWERS.find(p => p.id === selectedPower.value))

const avatarOptions = computed(() =>
  worldStore.avatarList
    .filter(a => !a.is_dead)
    .map(a => ({ id: a.id, name: a.name || a.id }))
)

function selectPower(id: string) {
  selectedPower.value = id
  targetAvatarId.value = null
  confirmPending.value = false
  lastActionMsg.value = ''
}

function confirmAction() {
  const power = selectedPowerDef.value
  if (!power) return
  if (!canAfford(power.cost)) {
    lastActionMsg.value = '天道积分不足'
    return
  }
  if (power.needTarget && !targetAvatarId.value) {
    lastActionMsg.value = '请先选择目标修士'
    return
  }

  const savedTarget = targetAvatarId.value

  // 预言权能：特殊处理
  if (power.id === 'prophecy') {
    daoStore.usePower(power.id, savedTarget)
    const avatar = worldStore.avatarList.find(a => a.id === savedTarget)
    generateProphecy(avatar?.name || '此人')
    lastActionMsg.value = `正在窥视天机...`
    selectedPower.value = null
    targetAvatarId.value = null
    return
  }

  // 扣除积分，触发效果
  daoStore.usePower(power.id, savedTarget)
  lastActionMsg.value = `天道权能「${power.name}」已施展`
  confirmPending.value = false
  selectedPower.value = null
  targetAvatarId.value = null

  // 若选中了目标，跳转到角色
  if (savedTarget) {
    uiStore.select('avatar', savedTarget)
  }
}
</script>

<template>
  <!-- 悬浮按钮：天道面板入口 -->
  <div class="dao-fab" @click="showPanel = !showPanel" :class="{ active: showPanel }">
    <span class="fab-icon">天</span>
    <span class="fab-points">{{ daoStore.points }}</span>
  </div>

  <!-- 天道干预面板 -->
  <Teleport to="body">
    <Transition name="dao-panel">
      <div v-if="showPanel" class="dao-panel-overlay" @click.self="showPanel = false">
        <div class="dao-panel">
          <!-- 标题 -->
          <div class="dao-header">
            <div class="dao-title">
              <span class="title-emblem">⊙</span>
              天道干预
            </div>
            <div class="dao-points">
              <span class="points-label">天道积分</span>
              <span class="points-value">{{ daoStore.points }}</span>
            </div>
            <button class="dao-close" @click="showPanel = false">×</button>
          </div>

          <!-- 积分进度条 -->
          <div class="points-bar-wrap">
            <div class="points-bar">
              <div class="points-fill" :style="{ width: Math.min(daoStore.points / 2, 100) + '%' }"></div>
            </div>
            <span class="points-regen">+1积分/月</span>
          </div>

          <!-- 权能列表 -->
          <div class="powers-grid">
            <div
              v-for="power in POWERS"
              :key="power.id"
              class="power-card"
              :class="{
                'selected': selectedPower === power.id,
                'unaffordable': !canAfford(power.cost)
              }"
              @click="selectPower(power.id)"
              :style="{ '--power-color': power.color }"
            >
              <div class="power-icon" :style="{ color: power.color }">{{ power.icon }}</div>
              <div class="power-info">
                <div class="power-name" :style="{ color: power.color }">{{ power.name }}</div>
                <div class="power-desc">{{ power.desc }}</div>
              </div>
              <div class="power-cost" :class="{ 'can-afford': canAfford(power.cost) }">
                {{ power.cost }}
              </div>
            </div>
          </div>

          <!-- 施法区域 -->
          <div v-if="selectedPower && selectedPowerDef" class="cast-area">
            <div class="cast-title" :style="{ color: selectedPowerDef.color }">
              {{ selectedPowerDef.icon }} 施展：{{ selectedPowerDef.name }}
            </div>

            <!-- 目标选择 -->
            <div v-if="selectedPowerDef.needTarget" class="target-select">
              <label class="select-label">选择目标修士：</label>
              <select v-model="targetAvatarId" class="avatar-select">
                <option value="" disabled selected>— 请选择 —</option>
                <option v-for="a in avatarOptions" :key="a.id" :value="a.id">
                  {{ a.name }}
                </option>
              </select>
            </div>

            <div class="cast-actions">
              <button
                class="cast-btn"
                :style="{ '--btn-color': selectedPowerDef.color }"
                @click="confirmAction"
                :disabled="!canAfford(selectedPowerDef.cost)"
              >
                施展（消耗 {{ selectedPowerDef.cost }} 积分）
              </button>
              <button class="cancel-btn" @click="selectedPower = null">取消</button>
            </div>

            <div v-if="lastActionMsg" class="action-msg">{{ lastActionMsg }}</div>
          </div>

          <!-- 预言显示 -->
          <Transition name="prophecy">
            <div v-if="showProphecy" class="prophecy-box">
              <div class="prophecy-header">
                <span class="prophecy-icon">卜</span>
                天机示言
                <button class="prophecy-close" @click="showProphecy = false">×</button>
              </div>
              <div class="prophecy-content">{{ prophecyText }}</div>
            </div>
            <div v-else-if="isGeneratingProphecy" class="prophecy-box generating">
              <div class="prophecy-icon spinning">卜</div>
              <div class="prophecy-loading">天道正在演算命运...</div>
            </div>
          </Transition>

          <!-- 说明 -->
          <div class="dao-footer">
            以天道之名，干预苍生命运。积分随时间自动积累，重大世界事件额外奖励。
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
/* 悬浮按钮 */
.dao-fab {
  position: absolute;
  bottom: 60px;
  right: 14px;
  width: 48px;
  height: 48px;
  background: radial-gradient(circle at 30% 30%, rgba(201, 162, 39, 0.3), rgba(6, 8, 16, 0.9));
  border: 1px solid rgba(201, 162, 39, 0.5);
  border-radius: 50%;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  z-index: 80;
  transition: all 0.25s;
  box-shadow: 0 0 12px rgba(201, 162, 39, 0.2);
}

.dao-fab:hover,
.dao-fab.active {
  background: radial-gradient(circle at 30% 30%, rgba(201, 162, 39, 0.5), rgba(6, 8, 16, 0.95));
  box-shadow: 0 0 20px rgba(201, 162, 39, 0.4);
  transform: scale(1.05);
}

.fab-icon {
  font-size: 16px;
  color: var(--color-gold-bright, #f0c040);
  font-weight: bold;
  line-height: 1;
}

.fab-points {
  font-size: 9px;
  color: rgba(201, 162, 39, 0.7);
  line-height: 1;
}

/* 面板遮罩 */
.dao-panel-overlay {
  position: fixed;
  inset: 0;
  z-index: 300;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.4);
  backdrop-filter: blur(3px);
}

/* 天道面板主体 */
.dao-panel {
  width: 520px;
  max-height: 80vh;
  background: linear-gradient(135deg, #07091a, #0c0f20);
  border: 1px solid rgba(201, 162, 39, 0.4);
  border-radius: 4px;
  display: flex;
  flex-direction: column;
  box-shadow: 0 0 40px rgba(0, 0, 0, 0.8), 0 0 0 1px rgba(201, 162, 39, 0.1), inset 0 0 40px rgba(201, 162, 39, 0.03);
  overflow: hidden;
  position: relative;
}

/* 描金角装饰 */
.dao-panel::before {
  content: '';
  position: absolute;
  top: 4px; left: 4px;
  width: 12px; height: 12px;
  border-top: 1px solid rgba(201, 162, 39, 0.6);
  border-left: 1px solid rgba(201, 162, 39, 0.6);
  pointer-events: none;
}
.dao-panel::after {
  content: '';
  position: absolute;
  bottom: 4px; right: 4px;
  width: 12px; height: 12px;
  border-bottom: 1px solid rgba(201, 162, 39, 0.6);
  border-right: 1px solid rgba(201, 162, 39, 0.6);
  pointer-events: none;
}

/* 头部 */
.dao-header {
  display: flex;
  align-items: center;
  padding: 14px 20px;
  border-bottom: 1px solid rgba(201, 162, 39, 0.2);
  background: rgba(201, 162, 39, 0.04);
}

.dao-title {
  flex: 1;
  font-size: 18px;
  font-weight: bold;
  color: var(--color-gold-bright, #f0c040);
  letter-spacing: 3px;
  text-shadow: 0 0 10px rgba(240, 192, 64, 0.4);
  display: flex;
  align-items: center;
  gap: 8px;
}

.title-emblem {
  font-size: 14px;
  opacity: 0.7;
  animation: emblem-rotate 10s linear infinite;
}

@keyframes emblem-rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.dao-points {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  margin-right: 16px;
}

.points-label {
  font-size: 10px;
  color: rgba(201, 162, 39, 0.6);
  letter-spacing: 1px;
}

.points-value {
  font-size: 22px;
  font-weight: bold;
  color: var(--color-gold-bright, #f0c040);
  text-shadow: 0 0 8px rgba(240, 192, 64, 0.5);
  line-height: 1;
}

.dao-close {
  background: transparent;
  border: none;
  color: rgba(201, 162, 39, 0.5);
  font-size: 20px;
  cursor: pointer;
  padding: 0 4px;
  transition: color 0.2s;
}
.dao-close:hover { color: rgba(201, 162, 39, 0.9); }

/* 积分条 */
.points-bar-wrap {
  padding: 8px 20px;
  display: flex;
  align-items: center;
  gap: 10px;
}

.points-bar {
  flex: 1;
  height: 4px;
  background: rgba(255, 255, 255, 0.06);
  border-radius: 2px;
  overflow: hidden;
}

.points-fill {
  height: 100%;
  background: linear-gradient(to right, rgba(201, 162, 39, 0.6), #f0c040);
  border-radius: 2px;
  transition: width 0.5s ease;
  box-shadow: 0 0 6px rgba(240, 192, 64, 0.4);
}

.points-regen {
  font-size: 10px;
  color: rgba(201, 162, 39, 0.4);
  white-space: nowrap;
}

/* 权能网格 */
.powers-grid {
  padding: 10px 16px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  overflow-y: auto;
  flex: 1;
}

.power-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 3px;
  cursor: pointer;
  transition: all 0.2s;
  background: rgba(0, 0, 0, 0.2);
  position: relative;
  overflow: hidden;
}

.power-card::before {
  content: '';
  position: absolute;
  left: 0; top: 0; bottom: 0;
  width: 2px;
  background: var(--power-color, #c9a227);
  opacity: 0;
  transition: opacity 0.2s;
}

.power-card:hover,
.power-card.selected {
  border-color: rgba(255, 255, 255, 0.12);
  background: rgba(255, 255, 255, 0.04);
}

.power-card:hover::before,
.power-card.selected::before {
  opacity: 1;
}

.power-card.selected {
  border-color: var(--power-color, #c9a227);
  background: rgba(201, 162, 39, 0.06);
  box-shadow: 0 0 10px rgba(201, 162, 39, 0.1);
}

.power-card.unaffordable {
  opacity: 0.4;
  cursor: not-allowed;
}

.power-icon {
  font-size: 20px;
  width: 28px;
  text-align: center;
  flex-shrink: 0;
  text-shadow: 0 0 6px currentColor;
}

.power-info {
  flex: 1;
}

.power-name {
  font-size: 14px;
  font-weight: bold;
  letter-spacing: 0.5px;
  margin-bottom: 2px;
}

.power-desc {
  font-size: 11px;
  color: rgba(200, 190, 170, 0.6);
  line-height: 1.3;
}

.power-cost {
  font-size: 16px;
  font-weight: bold;
  color: rgba(200, 190, 170, 0.4);
  flex-shrink: 0;
  min-width: 28px;
  text-align: right;
}

.power-cost.can-afford {
  color: var(--color-gold-bright, #f0c040);
}

/* 施法区域 */
.cast-area {
  padding: 12px 20px 8px;
  border-top: 1px solid rgba(201, 162, 39, 0.15);
  background: rgba(201, 162, 39, 0.03);
  flex-shrink: 0;
}

.cast-title {
  font-size: 14px;
  font-weight: bold;
  margin-bottom: 10px;
  letter-spacing: 1px;
}

.target-select {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}

.select-label {
  font-size: 12px;
  color: rgba(200, 190, 170, 0.6);
  white-space: nowrap;
}

.avatar-select {
  flex: 1;
  background: rgba(0, 0, 0, 0.5);
  border: 1px solid rgba(201, 162, 39, 0.3);
  color: var(--color-text-main, #e8dfc0);
  padding: 4px 8px;
  border-radius: 2px;
  font-size: 13px;
  font-family: inherit;
}

.cast-actions {
  display: flex;
  gap: 8px;
}

.cast-btn {
  flex: 1;
  padding: 8px 16px;
  background: rgba(201, 162, 39, 0.15);
  border: 1px solid rgba(201, 162, 39, 0.5);
  color: var(--color-gold-bright, #f0c040);
  border-radius: 2px;
  cursor: pointer;
  font-size: 13px;
  font-family: inherit;
  letter-spacing: 0.5px;
  transition: all 0.2s;
  --btn-color: #c9a227;
}

.cast-btn:hover:not(:disabled) {
  background: rgba(201, 162, 39, 0.28);
  box-shadow: 0 0 12px rgba(201, 162, 39, 0.2);
}

.cast-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.cancel-btn {
  padding: 8px 16px;
  background: transparent;
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: rgba(200, 190, 170, 0.5);
  border-radius: 2px;
  cursor: pointer;
  font-size: 13px;
  font-family: inherit;
  transition: all 0.2s;
}

.cancel-btn:hover {
  border-color: rgba(255, 255, 255, 0.2);
  color: rgba(200, 190, 170, 0.8);
}

.action-msg {
  margin-top: 8px;
  font-size: 12px;
  color: var(--color-gold, #c9a227);
  text-align: center;
  letter-spacing: 0.5px;
}

/* 预言框 */
.prophecy-box {
  margin: 0 16px 8px;
  padding: 12px 14px;
  background: rgba(201, 168, 80, 0.06);
  border: 1px solid rgba(201, 168, 80, 0.35);
  border-radius: 3px;
  flex-shrink: 0;
  position: relative;
}

.prophecy-box.generating {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px;
}

.prophecy-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: rgba(201, 168, 80, 0.7);
  letter-spacing: 2px;
  margin-bottom: 8px;
}

.prophecy-close {
  margin-left: auto;
  background: transparent;
  border: none;
  color: rgba(201, 168, 80, 0.4);
  cursor: pointer;
  font-size: 14px;
  padding: 0 2px;
}

.prophecy-close:hover {
  color: rgba(201, 168, 80, 0.8);
}

.prophecy-icon {
  font-size: 14px;
  color: #c9a850;
}

.prophecy-icon.spinning {
  animation: spin 2s linear infinite;
  font-size: 20px;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.prophecy-loading {
  font-size: 13px;
  color: rgba(201, 168, 80, 0.6);
  letter-spacing: 1px;
}

.prophecy-content {
  font-size: 12px;
  color: #c9a850;
  line-height: 1.8;
  white-space: pre-line;
  letter-spacing: 0.5px;
}

/* 预言动画 */
.prophecy-enter-active {
  animation: prophecy-appear 0.5s ease-out;
}
.prophecy-leave-active {
  animation: prophecy-appear 0.3s ease-in reverse;
}

@keyframes prophecy-appear {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

/* 底部说明 */
.dao-footer {
  padding: 8px 20px 12px;
  font-size: 10px;
  color: rgba(200, 190, 170, 0.3);
  text-align: center;
  letter-spacing: 0.5px;
  border-top: 1px solid rgba(255, 255, 255, 0.04);
  flex-shrink: 0;
}

/* 面板过渡动画 */
.dao-panel-enter-active {
  animation: panel-appear 0.3s ease-out;
}
.dao-panel-leave-active {
  animation: panel-appear 0.2s ease-in reverse;
}

@keyframes panel-appear {
  from { opacity: 0; transform: scale(0.95) translateY(10px); }
  to { opacity: 1; transform: scale(1) translateY(0); }
}
</style>
