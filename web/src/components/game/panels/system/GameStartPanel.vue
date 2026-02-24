<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { NForm, NFormItem, NInputNumber, NSelect, NButton, NInput, NSwitch, NInputGroup, NDivider, useMessage } from 'naive-ui'
import { useI18n } from 'vue-i18n'
import { systemApi } from '../../../../api'

const { t } = useI18n()

const props = defineProps<{
  readonly: boolean
}>()

const message = useMessage()

// 配置表单数据
const config = ref({
  init_npc_num: 12,
  sect_num: 3,
  npc_awakening_rate_per_month: 0.01,
  world_history: '',
  use_random_map: false,
  map_seed: '',
  map_width: 160,
  map_height: 100,
})

const loading = ref(false)

// 预设地图尺寸
const mapSizePresets = [
  { label: t('game_start.map_size.small'),  value: 'small'  },
  { label: t('game_start.map_size.medium'), value: 'medium' },
  { label: t('game_start.map_size.large'),  value: 'large'  },
  { label: t('game_start.map_size.custom'), value: 'custom' },
]
const selectedPreset = ref<string>('medium')

function applyPreset(preset: string) {
  selectedPreset.value = preset
  if (preset === 'small')  { config.value.map_width = 100; config.value.map_height = 65 }
  if (preset === 'medium') { config.value.map_width = 160; config.value.map_height = 100 }
  if (preset === 'large')  { config.value.map_width = 240; config.value.map_height = 150 }
}

async function fetchConfig() {
  try {
    loading.value = true
    const res = await systemApi.fetchCurrentConfig()
    config.value = {
      init_npc_num: res.game.init_npc_num,
      sect_num: res.game.sect_num,
      npc_awakening_rate_per_month: res.game.npc_awakening_rate_per_month,
      world_history: res.game.world_history || '',
      use_random_map: res.game.use_random_map ?? false,
      map_seed: res.game.map_seed || '',
      map_width: res.game.map_width ?? 160,
      map_height: res.game.map_height ?? 100,
    }
  } catch (e) {
    message.error(t('game_start.messages.load_failed'))
    console.error(e)
  } finally {
    loading.value = false
  }
}

async function startGame() {
  try {
    loading.value = true
    await systemApi.startGame(config.value)
    message.success(t('game_start.messages.start_success'))
  } catch (e) {
    message.error(t('game_start.messages.start_failed'))
    console.error(e)
    loading.value = false
  }
}

onMounted(() => {
  fetchConfig()
})
</script>

<template>
  <div class="game-start-panel">
    <div class="panel-header">
      <h3>{{ t('game_start.title') }}</h3>
      <p class="description">{{ t('game_start.description') }}</p>
    </div>

    <n-form
      label-placement="left"
      label-width="160"
      require-mark-placement="right-hanging"
      :disabled="readonly"
    >
      <!-- 修士与宗门 -->
      <n-form-item :label="t('game_start.labels.init_npc_num')" path="init_npc_num">
        <n-input-number v-model:value="config.init_npc_num" :min="0" :max="100" />
      </n-form-item>

      <n-form-item :label="t('game_start.labels.sect_num')" path="sect_num">
        <n-input-number v-model:value="config.sect_num" :min="0" :max="14" />
      </n-form-item>
      <div class="tip-text" style="margin-top: -12px;">
        {{ t('game_start.tips.sect_num') }}
      </div>

      <n-form-item :label="t('game_start.labels.new_npc_rate')" path="npc_awakening_rate_per_month">
        <n-input-number 
            v-model:value="config.npc_awakening_rate_per_month" 
            :min="0" 
            :max="1" 
            :step="0.001"
            :format="(val: number) => `${(val * 100).toFixed(1)}%`"
            :parse="(val: string) => parseFloat(val) / 100"
        />
      </n-form-item>

      <!-- 随机地图设置 -->
      <n-divider style="margin: 16px 0; color: #d4a843; font-size: 0.85em;">{{ t('game_start.map_section') }}</n-divider>

      <n-form-item :label="t('game_start.labels.use_random_map')" path="use_random_map">
        <n-switch v-model:value="config.use_random_map" />
      </n-form-item>

      <template v-if="config.use_random_map">
        <n-form-item :label="t('game_start.labels.map_size')" path="map_size_preset">
          <div class="preset-buttons">
            <n-button
              v-for="p in mapSizePresets"
              :key="p.value"
              :type="selectedPreset === p.value ? 'primary' : 'default'"
              size="small"
              @click="applyPreset(p.value)"
              style="margin-right: 8px; margin-bottom: 8px;"
            >{{ p.label }}</n-button>
          </div>
        </n-form-item>

        <template v-if="selectedPreset === 'custom'">
          <n-form-item :label="t('game_start.labels.map_width')" path="map_width">
            <n-input-number v-model:value="config.map_width" :min="60" :max="512" :step="10" />
          </n-form-item>
          <n-form-item :label="t('game_start.labels.map_height')" path="map_height">
            <n-input-number v-model:value="config.map_height" :min="40" :max="320" :step="10" />
          </n-form-item>
        </template>
        <div v-else class="tip-text" style="margin-top: -8px; margin-bottom: 16px;">
          {{ t('game_start.tips.map_size_current', { w: config.map_width, h: config.map_height }) }}
        </div>

        <n-form-item :label="t('game_start.labels.map_seed')" path="map_seed">
          <n-input
            v-model:value="config.map_seed"
            :placeholder="t('game_start.placeholders.map_seed')"
            clearable
          />
        </n-form-item>
        <div class="tip-text" style="margin-top: -12px;">
          {{ t('game_start.tips.map_seed') }}
        </div>
      </template>

      <!-- 世界历史 -->
      <n-divider style="margin: 16px 0; color: #d4a843; font-size: 0.85em;">{{ t('game_start.history_section') }}</n-divider>

      <n-form-item :label="t('game_start.labels.world_history')" path="world_history">
        <n-input
          v-model:value="config.world_history"
          type="textarea"
          :placeholder="t('game_start.placeholders.world_history')"
          :autosize="{ minRows: 3, maxRows: 6 }"
          maxlength="800"
          show-count
        />
      </n-form-item>
      <div class="tip-text" style="margin-top: -12px;">
        {{ t('game_start.tips.world_history') }}
      </div>

      <div class="actions" v-if="!readonly">
        <n-button type="primary" size="large" @click="startGame" :loading="loading">
          {{ t('game_start.actions.start') }}
        </n-button>
      </div>
    </n-form>
  </div>
</template>

<style scoped>
.game-start-panel {
  color: #eee;
  max-width: 600px;
  margin: 0 auto;
}

.panel-header {
  margin-bottom: 2em;
  text-align: center;
}

.description {
  color: #888;
  font-size: 0.9em;
}

.tip-text {
  margin-left: 160px; /* offset label width */
  margin-bottom: 24px;
  color: #aaa;
  font-size: 0.85em;
  line-height: 1.5;
}

.actions {
  display: flex;
  justify-content: center;
  margin-top: 2em;
}

.preset-buttons {
  display: flex;
  flex-wrap: wrap;
}
</style>