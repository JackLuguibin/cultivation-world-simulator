<script setup lang="ts">
import { onMounted, onUnmounted, watch, ref } from 'vue'
import { NConfigProvider, darkTheme, NMessageProvider } from 'naive-ui'
import { systemApi } from './api/modules/system'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

// Components
import SplashLayer from './components/SplashLayer.vue'
import GameCanvas from './components/game/GameCanvas.vue'
import InfoPanelContainer from './components/game/panels/info/InfoPanelContainer.vue'
import StatusBar from './components/layout/StatusBar.vue'
import EventPanel from './components/game/panels/EventPanel.vue'
import SystemMenu from './components/SystemMenu.vue'
import LoadingOverlay from './components/LoadingOverlay.vue'
import EffectsOverlay from './components/game/effects/EffectsOverlay.vue'
import HeavenlyDaoPanel from './components/game/panels/HeavenlyDaoPanel.vue'
import RankingPanel from './components/game/panels/RankingPanel.vue'
import ChroniclePanel from './components/game/panels/ChroniclePanel.vue'
import TournamentPanel from './components/game/panels/TournamentPanel.vue'
import WorldCrisisAlert from './components/game/WorldCrisisAlert.vue'

// Composables
import { useGameInit } from './composables/useGameInit'
import { useGameControl } from './composables/useGameControl'
import { useAudio } from './composables/useAudio'
import { useBgm } from './composables/useBgm'
import { useSidebarResize } from './composables/useSidebarResize'

// Stores
import { useUiStore } from './stores/ui'
import { useSettingStore } from './stores/setting'
import { useHeavenlyDaoStore } from './stores/heavenlyDao'
import { useWorldStore } from './stores/world'

const uiStore = useUiStore()
const settingStore = useSettingStore()
const daoStore = useHeavenlyDaoStore()
const worldStore = useWorldStore()

// 天道积分：每月自动积累
watch(() => [worldStore.year, worldStore.month], ([y, m]) => {
  if (gameInitialized.value) {
    daoStore.tickMonth(y as number, m as number)
  }
})

const showSplash = ref(true)

// Sidebar resizer 状态
const { sidebarWidth, isResizing, onResizerMouseDown } = useSidebarResize()

const openedFromSplash = ref(false)

// 1. 游戏初始化逻辑
const { 
  initStatus, 
  gameInitialized, 
  showLoading,
} = useGameInit()

// 2. 游戏控制逻辑
// 依赖 gameInitialized 状态来决定是否允许暂停等
const {
  showMenu,
  isManualPaused,
  menuDefaultTab,
  canCloseMenu,
  handleKeydown: controlHandleKeydown,
  performStartupCheck,
  handleLLMReady,
  handleMenuClose,
  toggleManualPause
} = useGameControl(gameInitialized)

// 3. 胶水逻辑：连接 Init 和 Control

// 当检测到 idle 状态时，执行启动检查
watch(initStatus, (newVal, oldVal) => {
  // Idle check
  if (newVal?.status === 'idle' && oldVal?.status !== 'idle') {
    if (!showMenu.value) {
      performStartupCheck()
    }
  }

  // Ready check (原逻辑: stopPolling 由 useGameInit 处理, 这里只负责 UI)
  if (oldVal?.status !== 'ready' && newVal?.status === 'ready') {
    showMenu.value = false
  }
})

// 自动取消暂停：当游戏初始化完成后，自动开始运行
watch(gameInitialized, (val) => {
  if (val) {
    // 切换到游戏背景音乐
    useBgm().play('map')

    // 如果游戏已初始化完成（可能是刷新页面后恢复），确保关闭 Splash
    if (showSplash.value) {
      showSplash.value = false
    }

    // 设置前端状态并恢复后端
    isManualPaused.value = false
    systemApi.resumeGame().catch(console.error)
    openedFromSplash.value = false // 游戏开始，清除 Splash 来源标记
  }
})

// 事件处理
function onKeydown(e: KeyboardEvent) {
  if (showLoading.value) return
  if (showSplash.value) return
  controlHandleKeydown(e)
}

function handleSelection(target: { type: 'avatar' | 'region'; id: string; name?: string }) {
  uiStore.select(target.type, target.id)
}

async function handleSplashAction(key: string) {
  if (key === 'exit') {
    try {
      await systemApi.shutdown()
      window.close()
      document.body.innerHTML = `<div style="color:white; display:flex; justify-content:center; align-items:center; height:100vh; background:black; font-size:24px;">${t('game.controls.closed_msg')}</div>`
    } catch (e) {
      console.error('Shutdown failed', e)
    }
    return
  }

  openedFromSplash.value = true // 标记来源
  // 关闭 Splash
  showSplash.value = false

  // 根据按键跳转到对应 Tab
  if (key === 'start') {
    performStartupCheck()
  } else if (key === 'load') {
    menuDefaultTab.value = 'load'
    showMenu.value = true
  } else if (key === 'settings') {
    menuDefaultTab.value = 'settings'
    showMenu.value = true
  } else if (key === 'about') {
    menuDefaultTab.value = 'about'
    showMenu.value = true
  }
}

function handleMenuCloseWrapper() {
  // 如果是从 Splash 打开的，关闭菜单时应回到 Splash
  if (openedFromSplash.value) {
    showMenu.value = false
    showSplash.value = true
    // 保持 openedFromSplash 为 true 或 false?
    // 如果回到 Splash，下次点击 Start 又是重新流程。
    // 这里不需要重置，因为下次点击 handleSplashAction 会再次设置。
  } else {
    // 正常游戏内关闭
    handleMenuClose()
  }
}

async function handleReturnToMain() {
  try {
    await systemApi.resetGame()
    // 关闭菜单
    showMenu.value = false
    // 显示 Splash
    showSplash.value = true
    // 重置来源标记（虽然显示Splash后，点击按钮会重新设置，但这里为了逻辑清晰先重置）
    openedFromSplash.value = false 
  } catch (e) {
    console.error('Reset game failed', e)
  }
}

onMounted(() => {
  window.addEventListener('keydown', onKeydown)
  // Ensure backend language setting matches frontend preference
  settingStore.syncBackend()
  
    // Initialize audio system
    useAudio().init()
    useBgm().init() // 确保 BGM 系统在 App 层级初始化，避免 Watcher 被子组件卸载
  })

onUnmounted(() => {
  window.removeEventListener('keydown', onKeydown)
})
</script>

<template>
  <n-config-provider :theme="darkTheme">
    <n-message-provider>
      <SplashLayer 
        v-if="showSplash" 
        @action="handleSplashAction"
      />
      
      <!-- Loading Overlay - 盖在游戏上面 -->
      <LoadingOverlay 
        v-if="!showSplash && showLoading"
        :status="initStatus"
      />

      <!-- Game UI - 始终渲染 -->
      <div v-if="!showSplash" class="app-layout">
        <StatusBar />
        
        <div class="main-content">
          <div class="map-container">
            <!-- 顶部控制栏 -->
            <div class="top-controls">
              <!-- 暂停/播放按钮 -->
              <button class="control-btn pause-toggle" @click="toggleManualPause" :title="isManualPaused ? t('game.controls.resume') : t('game.controls.pause')">
                <!-- 播放图标 (当暂停时显示) -->
                <svg v-if="isManualPaused" viewBox="0 0 24 24" width="24" height="24">
                  <path fill="currentColor" d="M8 5v14l11-7z"/>
                </svg>
                <!-- 暂停图标 (当播放时显示) -->
                <svg v-else viewBox="0 0 24 24" width="24" height="24">
                  <path fill="currentColor" d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/>
                </svg>
              </button>

              <!-- 菜单按钮 -->
              <button class="control-btn menu-toggle" @click="showMenu = true">
                <svg viewBox="0 0 24 24" width="24" height="24">
                  <path fill="currentColor" d="M3 18h18v-2H3v2zm0-5h18v-2H3v2zm0-7v2h18V6H3z"/>
                </svg>
              </button>
            </div>

            <!-- 暂停状态提示 -->
            <div v-if="isManualPaused" class="pause-indicator">
              <div class="pause-text">{{ t('game.controls.paused') }}</div>
            </div>

            <GameCanvas
              :sidebar-width="sidebarWidth"
              @avatarSelected="handleSelection"
              @regionSelected="handleSelection"
            />
            <!-- 特效覆盖层：境界突破、天劫、奇遇等特效 -->
            <EffectsOverlay v-if="gameInitialized" />
            <InfoPanelContainer />
            <!-- 天道干预面板 -->
            <HeavenlyDaoPanel v-if="gameInitialized" />
            <!-- 天骄榜 -->
            <RankingPanel v-if="gameInitialized" />
            <!-- 世界年鉴 -->
            <ChroniclePanel v-if="gameInitialized" />
            <!-- 比武大会 -->
            <TournamentPanel v-if="gameInitialized" />
            <!-- 世界危机预警 -->
            <WorldCrisisAlert v-if="gameInitialized" />
          </div>
          <div
            class="sidebar-resizer"
            :class="{ 'is-resizing': isResizing }"
            @mousedown="onResizerMouseDown"
          ></div>
          <aside class="sidebar" :style="{ width: sidebarWidth + 'px' }">
            <EventPanel />
          </aside>
        </div>

        <SystemMenu 
          :visible="showMenu"
          :default-tab="menuDefaultTab"
          :game-initialized="gameInitialized"
          :closable="canCloseMenu"
          @close="handleMenuCloseWrapper"
          @llm-ready="handleLLMReady"
          @return-to-main="handleReturnToMain"
          @exit-game="() => handleSplashAction('exit')"
        />
      </div>
    </n-message-provider>
  </n-config-provider>
</template>

<style scoped>
.app-layout {
  display: flex;
  flex-direction: column;
  width: 100vw;
  height: 100vh;
  background: var(--color-bg-dark);
  color: var(--color-text-main);
  overflow: hidden;
  position: relative;
}

.main-content {
  flex: 1;
  display: flex;
  position: relative;
  overflow: hidden;
}

.map-container {
  flex: 1;
  position: relative;
  background: #06080f;
  overflow: hidden;
}

.top-controls {
  position: absolute;
  top: 10px;
  right: 10px;
  z-index: 100;
  display: flex;
  gap: 8px;
}

.control-btn {
  background: rgba(6, 8, 16, 0.8);
  border: 1px solid rgba(201, 162, 39, 0.35);
  color: rgba(201, 162, 39, 0.8);
  width: 38px;
  height: 38px;
  border-radius: 3px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  backdrop-filter: blur(8px);
  position: relative;
}

.control-btn::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: 3px;
  opacity: 0;
  background: radial-gradient(circle at center, rgba(201, 162, 39, 0.15), transparent);
  transition: opacity 0.2s;
}

.control-btn:hover {
  background: rgba(201, 162, 39, 0.12);
  border-color: rgba(201, 162, 39, 0.7);
  color: var(--color-gold-bright);
  box-shadow: 0 0 10px rgba(201, 162, 39, 0.2);
}

.control-btn:hover::before {
  opacity: 1;
}

.pause-indicator {
  position: absolute;
  top: 20px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 90;
  pointer-events: none;
}

.pause-text {
  background: rgba(6, 8, 16, 0.85);
  color: var(--color-gold-bright);
  padding: 6px 20px;
  border-radius: 2px;
  font-size: 14px;
  letter-spacing: 4px;
  border: 1px solid rgba(201, 162, 39, 0.4);
  backdrop-filter: blur(8px);
  box-shadow: 0 0 16px rgba(201, 162, 39, 0.15), inset 0 0 8px rgba(201, 162, 39, 0.05);
}

.sidebar-resizer {
  width: 3px;
  background: transparent;
  cursor: col-resize;
  transition: background 0.15s;
  flex-shrink: 0;
}

.sidebar-resizer:hover,
.sidebar-resizer.is-resizing {
  background: linear-gradient(to bottom, transparent, rgba(201, 162, 39, 0.4), transparent);
}

.sidebar {
  background: var(--color-bg-panel);
  border-left: 1px solid var(--color-border);
  display: flex;
  flex-direction: column;
  z-index: 20;
  flex-shrink: 0;
}
</style>
