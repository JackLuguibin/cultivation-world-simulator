/**
 * 天道积分系统 Store
 * 玩家积累"天道积分"，用于施展各种干预世界的权能
 */
import { defineStore } from 'pinia';
import { ref } from 'vue';

export const useHeavenlyDaoStore = defineStore('heavenlyDao', () => {
  const points = ref(50); // 初始积分
  const totalEarned = ref(50);
  const lastMonth = ref(0);

  // 历史施法记录
  const history = ref<Array<{ time: string; power: string; target: string | null; cost: number }>>([]);

  // 积分自动积累（每月+1）
  function tickMonth(year: number, month: number) {
    const stamp = year * 12 + month;
    if (stamp > lastMonth.value) {
      lastMonth.value = stamp;
      const gain = 1;
      points.value += gain;
      totalEarned.value += gain;
    }
  }

  // 大事件奖励（外部调用）
  function rewardMajorEvent(amount: number = 3) {
    points.value += amount;
    totalEarned.value += amount;
  }

  // 消耗积分施展权能
  function usePower(powerId: string, targetId: string | null) {
    const COSTS: Record<string, number> = {
      fortune: 10,
      misfortune: 20,
      tribulation: 30,
      guide: 15,
      reincarnate: 50,
      awaken: 40
    };

    const cost = COSTS[powerId] || 10;
    if (points.value < cost) return false;

    points.value -= cost;

    history.value.unshift({
      time: new Date().toLocaleTimeString(),
      power: powerId,
      target: targetId,
      cost
    });

    // 保留最近20条记录
    if (history.value.length > 20) {
      history.value = history.value.slice(0, 20);
    }

    return true;
  }

  return {
    points,
    totalEarned,
    history,
    tickMonth,
    rewardMajorEvent,
    usePower
  };
});
