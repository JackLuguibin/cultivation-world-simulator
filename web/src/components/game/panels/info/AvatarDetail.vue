<script setup lang="ts">
import { ref, computed, watch } from 'vue';
import type { AvatarDetail, EffectEntity } from '@/types/core';
import { RelationType } from '@/constants/relations';
import { formatHp } from '@/utils/formatters/number';
import StatItem from './components/StatItem.vue';
import EntityRow from './components/EntityRow.vue';
import RelationRow from './components/RelationRow.vue';
import TagList from './components/TagList.vue';
import SecondaryPopup from './components/SecondaryPopup.vue';
import { avatarApi } from '@/api';
import { useUiStore } from '@/stores/ui';
import { useI18n } from 'vue-i18n';

const { t } = useI18n();
const props = defineProps<{
  data: AvatarDetail;
}>();

const uiStore = useUiStore();
const secondaryItem = ref<EffectEntity | null>(null);
const showObjectiveModal = ref(false);
const objectiveContent = ref('');

// --- 境界进度条 ---
// 境界顺序
const REALM_ORDER = ['练气期', '筑基期', '金丹期', '元婴期', '化神期', '炼虚期', '合体期', '大乘期', '渡劫期'];
const STAGE_ORDER = ['前期', '中期', '后期'];
const MAX_LEVEL_PER_STAGE = 10;

const realmProgress = computed(() => {
  const realm = props.data.realm || '';
  const level = props.data.level ?? 0;
  // 每境界30级（前中后各10）
  const progressInRealm = Math.min((level % 30) / 30, 1);
  return Math.round(progressInRealm * 100);
});

const realmColor = computed(() => {
  const realm = props.data.realm || '';
  if (realm.includes('练气')) return '#b0b8c8';
  if (realm.includes('筑基')) return '#4de94d';
  if (realm.includes('金丹')) return '#f0c040';
  if (realm.includes('元婴')) return '#a070ff';
  if (realm.includes('化神')) return '#ff7a30';
  if (realm.includes('炼虚')) return '#ff4488';
  if (realm.includes('合体') || realm.includes('大乘') || realm.includes('渡劫')) return '#ffffff';
  return '#c9a227';
});

// HP百分比
const hpPercent = computed(() => {
  const { cur, max } = props.data.hp;
  if (!max) return 100;
  return Math.round((cur / max) * 100);
});

const hpColor = computed(() => {
  const p = hpPercent.value;
  if (p > 70) return '#3ddbb0';
  if (p > 30) return '#f0c040';
  return '#e05555';
});

// 灵根对应五行颜色
const rootColor = computed(() => {
  const root = props.data.root || '';
  if (root.includes('金')) return '#f0c040';
  if (root.includes('木')) return '#4de94d';
  if (root.includes('水')) return '#5ab4f0';
  if (root.includes('火')) return '#ff6b35';
  if (root.includes('土')) return '#c9a227';
  if (root.includes('雷') || root.includes('风')) return '#a070ff';
  if (root.includes('冰') || root.includes('寒')) return '#a0e8ff';
  if (root.includes('暗') || root.includes('血')) return '#e05555';
  return '#c0b090';
});

// --- Computeds ---

const groupedRelations = computed(() => {
  const rels = props.data.relations || [];
  
  // 1. 父母 (Parents) - 对应 RelationType.TO_ME_IS_PARENT (对方是我的父母)
  const existingParents = rels.filter(r => r.relation_type === RelationType.TO_ME_IS_PARENT);
  const displayParents = [...existingParents];
  
  // 补全凡人父母占位符
  // Check genders of existing parents
  const hasFather = existingParents.some(p => p.target_gender === 'male');
  const hasMother = existingParents.some(p => p.target_gender === 'female');
  
  // 如果现有的不足2个，尝试补全
  if (existingParents.length < 2) {
    if (!hasFather) {
      displayParents.unshift({ // Father usually first
        target_id: `mortal_father_placeholder`,
        name: '', 
        relation: '', 
        relation_type: RelationType.TO_ME_IS_PARENT,
        realm: '',
        sect: '',
        is_mortal: true, 
        label_key: 'father_short'
      } as any);
    }
    
    if (!hasMother) {
      displayParents.push({
        target_id: `mortal_mother_placeholder`,
        name: '', 
        relation: '', 
        relation_type: RelationType.TO_ME_IS_PARENT,
        realm: '',
        sect: '',
        is_mortal: true, 
        label_key: 'mother_short'
      } as any);
    }
  }
  
  // 2. 子女 (Children) - 对应 RelationType.TO_ME_IS_CHILD (对方是我的子女)
  const children = rels.filter(r => r.relation_type === RelationType.TO_ME_IS_CHILD);
  
  // 3. 其他 (Others)
  const others = rels.filter(r => 
    r.relation_type !== RelationType.TO_ME_IS_PARENT && 
    r.relation_type !== RelationType.TO_ME_IS_CHILD
  );

  return {
    parents: displayParents,
    children: children,
    others: others
  };
});

// --- Actions ---

function showDetail(item: EffectEntity | undefined) {
  if (item) {
    secondaryItem.value = item;
  }
}

function jumpToAvatar(id: string) {
  uiStore.select('avatar', id);
}

function jumpToSect(id: string) {
  uiStore.select('sect', id);
}

async function handleSetObjective() {
  if (!objectiveContent.value.trim()) return;
  try {
    await avatarApi.setLongTermObjective(props.data.id, objectiveContent.value);
    showObjectiveModal.value = false;
    objectiveContent.value = '';
    uiStore.refreshDetail();
  } catch (e) {
    console.error(e);
    alert(t('game.info_panel.avatar.modals.set_failed'));
  }
}

async function handleClearObjective() {
  if (!confirm(t('game.info_panel.avatar.modals.clear_confirm'))) return;
  try {
    await avatarApi.clearLongTermObjective(props.data.id);
    uiStore.refreshDetail();
  } catch (e) {
    console.error(e);
  }
}
</script>

<template>
  <div class="avatar-detail">
    <SecondaryPopup 
      :item="secondaryItem" 
      @close="secondaryItem = null" 
    />

    <!-- 角色头部信息区 -->
    <div class="avatar-header" :class="{ 'is-dead': data.is_dead }">
      <!-- 灵根光环 + 角色名 -->
      <div class="avatar-identity">
        <div class="avatar-aura" :style="{ '--aura-color': rootColor, '--realm-color': realmColor }">
          <div class="aura-ring outer"></div>
          <div class="aura-ring inner"></div>
          <div class="avatar-portrait">
            <span class="portrait-icon">{{ data.gender === '女' ? '♀' : '♂' }}</span>
          </div>
        </div>
        <div class="avatar-name-block">
          <div class="avatar-name">
            {{ data.name }}
            <span v-if="data.nickname" class="avatar-nickname">「{{ data.nickname }}」</span>
            <span v-if="data.is_dead" class="dead-mark">✟</span>
          </div>
          <div class="avatar-realm-tag" :style="{ color: realmColor }">
            {{ data.realm }} · 第{{ data.level }}层
          </div>
          <div class="avatar-action-tag" v-if="!data.is_dead && data.action_state">
            {{ data.action_state }}
          </div>
        </div>
      </div>

      <!-- 境界进度条 -->
      <div class="realm-progress-wrap" v-if="!data.is_dead">
        <div class="progress-label">
          <span>修为进度</span>
          <span :style="{ color: realmColor }">{{ realmProgress }}%</span>
        </div>
        <div class="realm-progress-bar">
          <div
            class="realm-progress-fill"
            :style="{ width: realmProgress + '%', background: `linear-gradient(to right, ${realmColor}88, ${realmColor})` }"
          ></div>
          <div class="realm-progress-glow" :style="{ width: realmProgress + '%', '--glow-color': realmColor }"></div>
        </div>
      </div>

      <!-- HP进度条 -->
      <div class="hp-bar-wrap" v-if="!data.is_dead">
        <div class="progress-label">
          <span>生命</span>
          <span :style="{ color: hpColor }">{{ formatHp(data.hp.cur, data.hp.max) }}</span>
        </div>
        <div class="hp-bar">
          <div
            class="hp-fill"
            :style="{ width: hpPercent + '%', background: `linear-gradient(to right, ${hpColor}88, ${hpColor})` }"
          ></div>
        </div>
      </div>

      <!-- 死亡横幅 -->
      <div class="dead-banner" v-if="data.is_dead">
        {{ t('game.info_panel.avatar.dead_with_reason', { reason: data.death_info?.reason || t('game.info_panel.avatar.unknown_reason') }) }}
      </div>
    </div>

    <!-- Actions Bar -->
    <div class="actions-bar" v-if="!data.is_dead">
      <button class="btn primary" @click="showObjectiveModal = true">{{ t('game.info_panel.avatar.set_objective') }}</button>
      <button class="btn" @click="handleClearObjective">{{ t('game.info_panel.avatar.clear_objective') }}</button>
    </div>

    <div class="content-scroll">
      <!-- Objectives -->
      <div v-if="!data.is_dead" class="objectives-banner">
        <div class="objective-item">
          <span class="label">{{ t('game.info_panel.avatar.long_term_objective') }}</span>
          <span class="value">{{ data.long_term_objective || t('common.none') }}</span>
        </div>
        <div class="objective-item">
          <span class="label">{{ t('game.info_panel.avatar.short_term_objective') }}</span>
          <span class="value">{{ data.short_term_objective || t('common.none') }}</span>
        </div>
      </div>

      <!-- Stats Grid -->
      <div class="stats-grid">
        <StatItem :label="t('game.info_panel.avatar.stats.realm')" :value="data.realm" :sub-value="data.level" />
        <StatItem :label="t('game.info_panel.avatar.stats.age')" :value="`${data.age} / ${data.lifespan}`" />
        <StatItem :label="t('game.info_panel.avatar.stats.origin')" :value="data.origin" />
        <StatItem :label="t('game.info_panel.avatar.stats.gender')" :value="data.gender" />
        
        <StatItem 
          :label="t('game.info_panel.avatar.stats.alignment')" 
          :value="data.alignment" 
          :on-click="() => showDetail(data.alignment_detail)"
        />
        <StatItem 
          :label="t('game.info_panel.avatar.stats.sect')" 
          :value="data.sect?.name || t('game.info_panel.avatar.stats.rogue')" 
          :sub-value="data.sect?.rank"
          :on-click="data.sect ? () => jumpToSect(data.sect!.id) : (data.orthodoxy ? () => showDetail(data.orthodoxy) : undefined)"
        />
        
        <StatItem 
          :label="t('game.info_panel.avatar.stats.root')" 
          :value="data.root" 
          :on-click="() => showDetail(data.root_detail)"
        />
        <StatItem :label="t('game.info_panel.avatar.stats.magic_stone')" :value="data.magic_stone" />
        <StatItem :label="t('game.info_panel.avatar.stats.appearance')" :value="data.appearance" />
        <StatItem :label="t('game.info_panel.avatar.stats.battle_strength')" :value="data.base_battle_strength" />
        <StatItem 
          :label="t('game.info_panel.avatar.stats.emotion')" 
          :value="data.emotion.emoji" 
          :sub-value="data.emotion.name"
        />
      </div>

      <!-- 气运/因果 -->
      <div class="section fate-section" v-if="data.fortune !== undefined || data.karma !== undefined">
        <div class="section-title">命运与因果</div>
        <div class="fate-bars">
          <!-- 气运条 -->
          <div class="fate-row" v-if="data.fortune !== undefined">
            <span class="fate-label">气运</span>
            <div class="fate-bar-wrap">
              <div class="fate-bar fortune-bar">
                <div
                  class="fate-fill fortune-fill"
                  :style="{ width: Math.abs(data.fortune) + '%', marginLeft: data.fortune >= 0 ? '50%' : (50 - Math.abs(data.fortune)) + '%' }"
                  :class="{ positive: data.fortune >= 0, negative: data.fortune < 0 }"
                ></div>
                <div class="fate-center-line"></div>
              </div>
            </div>
            <span class="fate-value" :class="{ positive: data.fortune > 20, negative: data.fortune < -20 }">
              {{ data.fortune > 40 ? '命运亨通' : data.fortune > 10 ? '气运尚可' : data.fortune < -40 ? '气运衰颓' : data.fortune < -10 ? '运势不佳' : '平稳' }}
            </span>
          </div>
          <!-- 因果条 -->
          <div class="fate-row" v-if="data.karma !== undefined">
            <span class="fate-label">因果</span>
            <div class="fate-bar-wrap">
              <div class="fate-bar karma-bar">
                <div
                  class="fate-fill karma-fill"
                  :style="{ width: Math.abs(data.karma) + '%', marginLeft: data.karma >= 0 ? '50%' : (50 - Math.abs(data.karma)) + '%' }"
                  :class="{ sinful: data.karma > 0, virtuous: data.karma < 0 }"
                ></div>
                <div class="fate-center-line"></div>
              </div>
            </div>
            <span class="fate-value" :class="{ sinful: data.karma > 30, virtuous: data.karma < -30 }">
              {{ data.karma > 50 ? '杀孽深重' : data.karma > 20 ? '有所杀孽' : data.karma < -50 ? '功德无量' : data.karma < -20 ? '积有功德' : '因果平衡' }}
            </span>
          </div>
        </div>
      </div>

      <!-- 天赋系统 -->
      <div class="section talents-section" v-if="(data.revealed_talents?.length || data.hidden_talent_count)">
        <div class="section-title">天赋</div>
        <div class="talents-grid">
          <!-- 已显现天赋 -->
          <div
            v-for="talent in data.revealed_talents"
            :key="talent.id"
            class="talent-chip revealed"
            :title="talent.desc"
          >
            <span class="talent-icon">★</span>
            {{ talent.name }}
          </div>
          <!-- 未显现天赋槽位 -->
          <div
            v-for="i in (data.hidden_talent_count || 0)"
            :key="'hidden-' + i"
            class="talent-chip hidden"
            title="隐藏天赋——尚未触发显现"
          >
            <span class="talent-icon">?</span>
            未知
          </div>
        </div>
        <div v-if="data.past_life_name" class="past-life-note">
          ♻ 前世：{{ data.past_life_name }}
        </div>
      </div>

      <!-- 武器认主度/器灵 -->
      <div class="section weapon-spirit-section" v-if="data.weapon && (data.weapon.mastery !== undefined || data.weapon.weapon_spirit)">
        <div class="section-title">兵器灵性</div>
        <div v-if="data.weapon.mastery !== undefined" class="mastery-bar-wrap">
          <span class="fate-label">认主度</span>
          <div class="mastery-bar">
            <div class="mastery-fill" :style="{ width: data.weapon.mastery + '%' }"></div>
          </div>
          <span class="mastery-value">{{ data.weapon.mastery }}%</span>
        </div>
        <div v-if="data.weapon.weapon_spirit" class="spirit-badge">
          <span class="spirit-icon">◈</span>
          器灵「{{ data.weapon.weapon_spirit }}」已觉醒
        </div>
      </div>

      <!-- Thinking -->
      <div class="section" v-if="data.thinking">
        <div class="section-title">{{ t('game.info_panel.avatar.sections.thinking') }}</div>
        <div class="text-content">{{ data.thinking }}</div>
      </div>

      <!-- Personas -->
      <div class="section" v-if="data.personas?.length">
        <div class="section-title">{{ t('game.info_panel.avatar.sections.traits') }}</div>
        <TagList :tags="data.personas" @click="showDetail" />
      </div>

      <!-- Equipment & Sect -->
      <div class="section">
        <div class="section-title">{{ t('game.info_panel.avatar.sections.techniques_equipment') }}</div>
        <EntityRow 
          v-if="data.technique" 
          :item="data.technique" 
          @click="showDetail(data.technique)" 
        />
        <EntityRow 
          v-if="data.weapon" 
          :item="data.weapon" 
          :meta="t('game.info_panel.avatar.weapon_meta', { value: data.weapon.proficiency })"
          @click="showDetail(data.weapon)" 
        />
        <EntityRow 
          v-if="data.auxiliary" 
          :item="data.auxiliary" 
          @click="showDetail(data.auxiliary)" 
        />
         <EntityRow 
          v-if="data.spirit_animal" 
          :item="data.spirit_animal" 
          @click="showDetail(data.spirit_animal)" 
        />
      </div>

      <!-- Materials -->
      <div class="section" v-if="data.materials?.length">
        <div class="section-title">{{ t('game.info_panel.avatar.sections.materials') }}</div>
        <div class="list-container">
          <EntityRow 
            v-for="item in data.materials"
            :key="item.name"
            :item="item"
            :meta="`x${item.count}`"
            compact
            @click="showDetail(item)"
          />
        </div>
      </div>

      <!-- Relations (Refactored) -->
      <div class="section" v-if="data.relations?.length || groupedRelations.parents.length">
        <div class="section-title">{{ t('game.info_panel.avatar.sections.relations') }}</div>
        
        <div class="list-container">
          <!-- Parents Group -->
          <template v-if="groupedRelations.parents.length">
            <!-- Title Removed as requested -->
            <template v-for="rel in groupedRelations.parents" :key="rel.target_id">
              <!-- Mortal Parent / Placeholder -->
              <div v-if="rel.is_mortal" class="mortal-row">
                <span class="label">{{ t(`game.info_panel.avatar.${rel.label_key}`) }}</span>
                <span class="value">{{ t('game.info_panel.avatar.mortal_realm') }}</span>
              </div>
              <!-- Cultivator Parent -->
              <RelationRow 
                v-else
                :relation="rel" 
                :name="rel.name"
                :meta="t('game.info_panel.avatar.relation_meta', { owner: data.name, relation: rel.relation })"
                :sub="`${rel.sect} · ${rel.realm}`"
                :type="rel.relation_type"
                @click="jumpToAvatar(rel.target_id)"
              />
            </template>
          </template>

          <!-- Children Group -->
          <template v-if="groupedRelations.children.length">
            <template v-for="rel in groupedRelations.children" :key="rel.target_id">
              <!-- Mortal Child -->
              <div v-if="rel.is_mortal" class="mortal-row">
                <span class="label">{{ rel.name }} ({{ rel.relation }})</span>
                <span class="value">{{ t('game.info_panel.avatar.mortal_realm') }}</span>
              </div>
              <!-- Cultivator Child -->
              <RelationRow 
                v-else
                :relation="rel"
                :name="rel.name"
                :meta="t('game.info_panel.avatar.relation_meta', { owner: data.name, relation: rel.relation })"
                :sub="`${rel.sect} · ${rel.realm}`"
                :type="rel.relation_type" 
                @click="jumpToAvatar(rel.target_id)"
              />
            </template>
          </template>

          <!-- Others Group -->
          <template v-if="groupedRelations.others.length">
            <RelationRow 
              v-for="rel in groupedRelations.others"
              :key="rel.target_id"
              :relation="rel"
              :name="rel.name"
              :meta="t('game.info_panel.avatar.relation_meta', { owner: data.name, relation: rel.relation })"
              :sub="`${rel.sect} · ${rel.realm}`"
              :type="rel.relation_type"
              @click="jumpToAvatar(rel.target_id)"
            />
          </template>
        </div>
      </div>

      <!-- Effects -->
      <div class="section" v-if="data['当前效果'] && data['当前效果'] !== '无'">
        <div class="section-title">{{ t('game.info_panel.avatar.sections.current_effects') }}</div>
        <div class="effects-grid">
          <template v-for="(line, idx) in data['当前效果'].split('\n')" :key="idx">
            <div class="effect-source">{{ line.match(/^\[(.*?)\]/)?.[1] || t('ui.other') }}</div>
            <div class="effect-content">
              <div v-for="(segment, sIdx) in line.replace(/^\[.*?\]\s*/, '').split(/[;；]/)" :key="sIdx">
                {{ segment.trim() }}
              </div>
            </div>
          </template>
        </div>
      </div>
    </div>

    <!-- Modal -->
    <div v-if="showObjectiveModal" class="modal-overlay">
      <div class="modal">
        <h3>{{ t('game.info_panel.avatar.modals.set_long_term') }}</h3>
        <textarea v-model="objectiveContent" :placeholder="t('game.info_panel.avatar.modals.placeholder')"></textarea>
        <div class="modal-footer">
          <button class="btn primary" @click="handleSetObjective">{{ t('common.confirm') }}</button>
          <button class="btn" @click="showObjectiveModal = false">{{ t('common.cancel') }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.avatar-detail {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  position: relative;
}

/* 角色头部区域 */
.avatar-header {
  padding: 12px 12px 8px;
  border-bottom: 1px solid var(--color-border);
  background: linear-gradient(to bottom, rgba(201, 162, 39, 0.05), transparent);
  flex-shrink: 0;
}

.avatar-header.is-dead {
  background: linear-gradient(to bottom, rgba(224, 85, 85, 0.05), transparent);
}

.avatar-identity {
  display: flex;
  gap: 10px;
  margin-bottom: 10px;
}

/* 灵气光环 */
.avatar-aura {
  position: relative;
  width: 44px;
  height: 44px;
  flex-shrink: 0;
}

.aura-ring {
  position: absolute;
  border-radius: 50%;
  border: 1px solid var(--aura-color, #c9a227);
  animation: rotate-ring 8s linear infinite;
}

.aura-ring.outer {
  inset: 0;
  opacity: 0.4;
}

.aura-ring.inner {
  inset: 4px;
  opacity: 0.6;
  animation-direction: reverse;
  animation-duration: 5s;
  border-color: var(--realm-color, #c9a227);
}

@keyframes rotate-ring {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.avatar-portrait {
  position: absolute;
  inset: 8px;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.5);
  border: 1px solid var(--realm-color, #c9a227);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 0 8px var(--realm-color, #c9a22740);
}

.portrait-icon {
  font-size: 14px;
  color: var(--realm-color, #c9a227);
}

.avatar-name-block {
  flex: 1;
  min-width: 0;
}

.avatar-name {
  font-size: 16px;
  font-weight: bold;
  color: var(--color-text-main);
  letter-spacing: 1px;
  line-height: 1.3;
  display: flex;
  align-items: baseline;
  gap: 4px;
  flex-wrap: wrap;
}

.avatar-nickname {
  font-size: 12px;
  color: var(--color-gold);
  font-weight: normal;
}

.dead-mark {
  font-size: 12px;
  color: var(--color-danger);
  font-weight: normal;
}

.avatar-realm-tag {
  font-size: 12px;
  margin-top: 2px;
  font-weight: 500;
  letter-spacing: 0.5px;
}

.avatar-action-tag {
  font-size: 11px;
  color: var(--color-sky);
  margin-top: 2px;
  opacity: 0.85;
}

/* 进度条 */
.realm-progress-wrap,
.hp-bar-wrap {
  margin-top: 6px;
}

.progress-label {
  display: flex;
  justify-content: space-between;
  font-size: 10px;
  color: var(--color-text-muted);
  margin-bottom: 3px;
}

.realm-progress-bar,
.hp-bar {
  height: 4px;
  background: rgba(255, 255, 255, 0.06);
  border-radius: 2px;
  overflow: hidden;
  position: relative;
}

.realm-progress-fill,
.hp-fill {
  height: 100%;
  border-radius: 2px;
  transition: width 0.5s ease;
  position: relative;
}

.realm-progress-glow {
  position: absolute;
  top: 0;
  left: 0;
  height: 100%;
  border-radius: 2px;
  box-shadow: 0 0 6px var(--glow-color, #c9a227);
  pointer-events: none;
  opacity: 0.6;
}

.actions-bar {
  display: flex;
  gap: 8px;
  padding: 8px 12px;
  border-bottom: 1px solid var(--color-border-dim);
  flex-shrink: 0;
}

.dead-banner {
  background: rgba(74, 26, 26, 0.7);
  color: #ffaaaa;
  padding: 6px 10px;
  border-radius: 3px;
  text-align: center;
  font-size: 12px;
  margin-top: 8px;
  border: 1px solid rgba(122, 42, 42, 0.6);
}

.objectives-banner {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 8px;
  background: rgba(201, 162, 39, 0.04);
  border-radius: 3px;
  margin-bottom: 8px;
  border: 1px solid rgba(201, 162, 39, 0.1);
}

.objective-item {
  display: flex;
  gap: 8px;
  font-size: 12px;
  line-height: 1.4;
}

.objective-item .label {
  color: var(--color-gold-dim);
  white-space: nowrap;
  font-weight: bold;
  flex-shrink: 0;
}

.objective-item .value {
  color: var(--color-text-main);
}

.content-scroll {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 10px 12px;
}

.stats-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
  background: rgba(201, 162, 39, 0.03);
  padding: 8px;
  border-radius: 3px;
  border: 1px solid var(--color-border-dim);
}

.section {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.section-title {
  font-size: 11px;
  font-weight: bold;
  color: var(--color-gold-dim);
  border-bottom: 1px solid var(--color-border-dim);
  padding-bottom: 4px;
  margin-bottom: 2px;
  letter-spacing: 1px;
  text-transform: uppercase;
}

.text-content {
  font-size: 12px;
  line-height: 1.6;
  color: var(--color-text-main);
  padding: 6px 8px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 2px;
  border-left: 2px solid rgba(201, 162, 39, 0.2);
}

.list-container {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

/* Relation specific styles */
.relation-group-label {
  font-size: 11px;
  color: #555;
  margin-top: 4px;
  margin-bottom: 2px;
  padding-left: 4px;
}

.mortal-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 8px;
  background: rgba(255, 255, 255, 0.02);
  border-radius: 4px;
  font-size: 12px;
  opacity: 0.6;
  cursor: default;
}

.mortal-row .label {
  color: #aaa;
}

.mortal-row .value {
  color: #666;
  font-size: 11px;
}

/* Buttons */
.btn {
  flex: 1;
  padding: 5px 10px;
  border: 1px solid var(--color-border);
  background: rgba(201, 162, 39, 0.06);
  color: var(--color-gold);
  border-radius: 2px;
  cursor: pointer;
  font-size: 12px;
  transition: all 0.2s;
  letter-spacing: 0.5px;
}

.btn:hover {
  background: rgba(201, 162, 39, 0.14);
  border-color: var(--color-gold);
}

.btn.primary {
  background: rgba(201, 162, 39, 0.18);
  color: var(--color-gold-bright);
  border-color: rgba(201, 162, 39, 0.5);
}

.btn.primary:hover {
  background: rgba(201, 162, 39, 0.28);
  box-shadow: 0 0 8px rgba(201, 162, 39, 0.2);
}

/* Modal */
.modal-overlay {
  position: absolute;
  top: 0;
  left: -16px;
  right: -16px;
  bottom: -16px;
  background: rgba(0, 0, 0, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
  backdrop-filter: blur(4px);
}

.modal {
  width: 280px;
  background: var(--color-bg-card);
  border: 1px solid var(--color-border-bright);
  border-radius: 3px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  box-shadow: 0 0 30px rgba(0, 0, 0, 0.8), 0 0 0 1px rgba(201, 162, 39, 0.1);
}

.modal h3 {
  margin: 0;
  font-size: 14px;
  color: var(--color-gold);
  letter-spacing: 1px;
}

.modal textarea {
  height: 100px;
  background: rgba(0, 0, 0, 0.4);
  border: 1px solid var(--color-border);
  color: var(--color-text-main);
  padding: 8px;
  resize: none;
  border-radius: 2px;
  font-family: inherit;
}

.modal-footer {
  display: flex;
  gap: 10px;
}

.effects-grid {
  display: grid;
  grid-template-columns: max-content 1fr;
  gap: 4px 12px;
  font-size: 12px;
  align-items: baseline;
}

.effect-source {
  color: var(--color-gold-dim);
  text-align: right;
  white-space: nowrap;
  font-size: 11px;
}

.effect-content {
  color: var(--color-sky);
  line-height: 1.5;
}

/* 关系行间距 */
.list-container {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.mortal-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 5px 8px;
  background: rgba(255, 255, 255, 0.02);
  border-radius: 2px;
  font-size: 12px;
  opacity: 0.5;
  cursor: default;
}

.mortal-row .label {
  color: var(--color-text-secondary);
}

.mortal-row .value {
  color: var(--color-text-muted);
  font-size: 11px;
}

/* ===== 气运/因果系统 ===== */
.fate-section .fate-bars {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.fate-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
}

.fate-label {
  width: 32px;
  color: var(--color-text-secondary);
  flex-shrink: 0;
}

.fate-bar-wrap {
  flex: 1;
}

.fate-bar {
  position: relative;
  height: 6px;
  background: rgba(255,255,255,0.08);
  border-radius: 3px;
  overflow: hidden;
}

.fate-center-line {
  position: absolute;
  left: 50%;
  top: 0;
  bottom: 0;
  width: 1px;
  background: rgba(255,255,255,0.3);
}

.fate-fill {
  position: absolute;
  top: 0;
  bottom: 0;
  border-radius: 3px;
  transition: all 0.3s;
}

.fortune-fill.positive { background: linear-gradient(to right, #c9a227aa, #ffd700); }
.fortune-fill.negative { background: linear-gradient(to right, #444, #666); }
.karma-fill.sinful { background: linear-gradient(to right, #cc2244aa, #ff3366); }
.karma-fill.virtuous { background: linear-gradient(to right, #2266ccaa, #3399ff); }

.fate-value {
  width: 64px;
  text-align: right;
  font-size: 11px;
  color: var(--color-text-secondary);
}
.fate-value.positive { color: #ffd700; }
.fate-value.negative { color: #888; }
.fate-value.sinful { color: #ff3366; }
.fate-value.virtuous { color: #3399ff; }

/* ===== 天赋系统 ===== */
.talents-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 4px;
}

.talent-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 8px;
  border-radius: 12px;
  font-size: 11px;
  cursor: help;
}

.talent-chip.revealed {
  background: rgba(201, 162, 39, 0.15);
  border: 1px solid rgba(201, 162, 39, 0.4);
  color: #ffd700;
}

.talent-chip.hidden {
  background: rgba(100, 100, 100, 0.15);
  border: 1px dashed rgba(120, 120, 120, 0.4);
  color: var(--color-text-muted);
}

.talent-icon {
  font-size: 10px;
}

.past-life-note {
  margin-top: 6px;
  font-size: 11px;
  color: #a070ff;
  opacity: 0.8;
}

/* ===== 兵器灵性 ===== */
.mastery-bar-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
}

.mastery-bar {
  flex: 1;
  height: 5px;
  background: rgba(255,255,255,0.1);
  border-radius: 3px;
  overflow: hidden;
}

.mastery-fill {
  height: 100%;
  background: linear-gradient(to right, #5ab4f088, #5ab4f0);
  border-radius: 3px;
  transition: width 0.3s;
}

.mastery-value {
  width: 36px;
  text-align: right;
  color: #5ab4f0;
  font-size: 11px;
}

.spirit-badge {
  margin-top: 6px;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 3px 10px;
  background: rgba(0, 200, 200, 0.1);
  border: 1px solid rgba(0, 200, 200, 0.3);
  border-radius: 12px;
  font-size: 11px;
  color: #3ddbb0;
}

.spirit-icon {
  font-size: 12px;
}
</style>