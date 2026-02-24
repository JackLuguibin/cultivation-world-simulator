"""
隐藏天赋系统

角色出生时随机赋予 0-3 个天赋（对外不可见），通过特定触发条件逐一显现。
"""
from __future__ import annotations

import csv
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional

if TYPE_CHECKING:
    from src.classes.core.avatar import Avatar

from src.classes.event import Event


@dataclass
class Talent:
    """天赋定义"""
    talent_id: str
    name: str
    desc: str
    category: str                    # battle / cultivation / alchemy / craft / fate
    trigger_condition: str           # 触发条件类型
    trigger_threshold: int           # 触发阈值
    effect_key: str                  # 触发后产生的effect key（用于effects系统）
    effect_value: float              # effect 数值
    fortune_bonus: float = 0.0       # 显现时气运变化
    karma_bonus: float = 0.0         # 显现时因果变化


# 全局天赋注册表
_talents_by_id: Dict[str, Talent] = {}


def _load_talents() -> None:
    from src.utils.config import CONFIG
    path = Path(CONFIG.paths.shared_game_configs) / "talent.csv"
    if not path.exists():
        return

    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            talent_id = row.get("talent_id", "").strip()
            if not talent_id:
                continue
            try:
                talent = Talent(
                    talent_id=talent_id,
                    name=row.get("name", "").strip(),
                    desc=row.get("desc", "").strip(),
                    category=row.get("category", "fate").strip(),
                    trigger_condition=row.get("trigger_condition", "age").strip(),
                    trigger_threshold=int(row.get("trigger_threshold", 10)),
                    effect_key=row.get("effect_key", "").strip(),
                    effect_value=float(row.get("effect_value", 0.0)),
                    fortune_bonus=float(row.get("fortune_bonus", 0.0)),
                    karma_bonus=float(row.get("karma_bonus", 0.0)),
                )
                _talents_by_id[talent_id] = talent
            except (ValueError, KeyError):
                continue


_load_talents()


def get_all_talent_ids() -> List[str]:
    return list(_talents_by_id.keys())


def get_talent(talent_id: str) -> Optional[Talent]:
    return _talents_by_id.get(talent_id)


def assign_birth_talents(avatar: "Avatar") -> None:
    """
    出生时随机赋予 0-3 个隐藏天赋。
    高气运角色（命星照耀/转世）有更大概率拥有更多天赋。
    """
    all_ids = get_all_talent_ids()
    if not all_ids:
        return

    # 天赋数量：0个(30%) / 1个(40%) / 2个(20%) / 3个(10%)
    count = random.choices([0, 1, 2, 3], weights=[30, 40, 20, 10], k=1)[0]

    if count == 0:
        return

    chosen = random.sample(all_ids, min(count, len(all_ids)))
    avatar.hidden_talents = chosen


def _get_trigger_metric(avatar: "Avatar", condition: str) -> int:
    """
    获取触发指标的当前值
    """
    metrics = getattr(avatar, "_talent_metrics", {})
    return metrics.get(condition, 0)


def increment_talent_metric(avatar: "Avatar", condition: str, amount: int = 1) -> None:
    """
    增加天赋触发指标计数（由各动作系统调用）
    """
    if not hasattr(avatar, "_talent_metrics"):
        avatar._talent_metrics = {}
    avatar._talent_metrics[condition] = avatar._talent_metrics.get(condition, 0) + amount


def _check_condition(avatar: "Avatar", talent: Talent) -> int:
    """
    根据触发条件类型返回当前进度值
    """
    condition = talent.trigger_condition
    metrics = getattr(avatar, "_talent_metrics", {})

    if condition == "age":
        return avatar.age.age
    elif condition == "breakthroughs":
        return metrics.get("breakthroughs", 0)
    elif condition == "battles_fought":
        return metrics.get("battles_fought", 0)
    elif condition == "kills":
        return metrics.get("kills", 0)
    elif condition == "meditate_count":
        return metrics.get("meditate_count", 0)
    elif condition == "weapon_use":
        return metrics.get("weapon_use", 0)
    elif condition == "harvest_count":
        return metrics.get("harvest_count", 0)
    elif condition == "hunt_count":
        return metrics.get("hunt_count", 0)
    elif condition == "buy_elixir":
        return metrics.get("buy_elixir", 0)
    elif condition == "elixir_count":
        return len(avatar.elixirs)
    elif condition == "near_death":
        return metrics.get("near_death", 0)
    elif condition == "assassinate_count":
        return metrics.get("assassinate_count", 0)
    else:
        return metrics.get(condition, 0)


def try_reveal_talent(avatar: "Avatar") -> List[Event]:
    """
    检测角色隐藏天赋是否满足显现条件，每月调用一次。
    返回若干显现事件。
    """
    if not avatar.hidden_talents:
        return []

    events: List[Event] = []
    to_reveal: List[str] = []

    for talent_id in list(avatar.hidden_talents):
        if talent_id in avatar.revealed_talents:
            continue
        talent = _talents_by_id.get(talent_id)
        if talent is None:
            continue

        # 检查触发条件
        current_val = _check_condition(avatar, talent)
        if current_val >= talent.trigger_threshold:
            to_reveal.append(talent_id)

    for talent_id in to_reveal:
        talent = _talents_by_id[talent_id]
        avatar.reveal_talent(talent_id)

        # 应用气运/因果奖励
        if talent.fortune_bonus != 0:
            avatar.modify_fortune(talent.fortune_bonus)
        if talent.karma_bonus != 0:
            avatar.modify_karma(talent.karma_bonus)

        # 立即应用天赋效果
        apply_revealed_talent_effects(avatar)

        # 生成显现事件
        from src.i18n import t
        event_text = t("{avatar} 天赋觉醒：【{talent_name}】——{talent_desc}",
                       avatar=avatar.name,
                       talent_name=talent.name,
                       talent_desc=talent.desc)
        event = Event(
            avatar.world.month_stamp,
            event_text,
            related_avatars=[avatar.id],
            is_major=True
        )
        # 标记为天赋显现事件（供前端识别）
        event.event_type = "talent_reveal"
        events.append(event)

    return events


def apply_revealed_talent_effects(avatar: "Avatar") -> None:
    """
    将已显现天赋的 effect 注入 avatar 的 temporary_effects（无限期）。
    由 recalc_effects 阶段自动调用，或在 reveal 后主动调用一次。
    """
    for talent_id in avatar.revealed_talents:
        talent = _talents_by_id.get(talent_id)
        if talent is None or not talent.effect_key:
            continue

        # 检查是否已经注入
        source_key = f"talent_{talent_id}"
        already = any(
            e.get("source") == source_key
            for e in avatar.temporary_effects
        )
        if not already:
            avatar.temporary_effects.append({
                "source": source_key,
                "effects": {talent.effect_key: talent.effect_value},
                "start_month": 0,
                "duration": 999999,  # 实质上永久
            })
            avatar.recalc_effects()


__all__ = [
    "Talent",
    "assign_birth_talents",
    "try_reveal_talent",
    "increment_talent_metric",
    "apply_revealed_talent_effects",
    "get_talent",
    "get_all_talent_ids",
]
