"""
转生 & 夺舍系统

死亡不再是终点，为持续运行的修仙世界提供 NPC 轮回的戏剧性。

转生流程：
  角色死亡 → 元神完整度检测（金丹+ 有概率保留阴神）
           → 阴神游荡 N 个月
           → 投胎至新生婴儿（继承部分隐藏天赋）
           → 以新 NPC 身份重生，带"宿慧"隐藏天赋

夺舍流程（仅高境界邪修）：
  元神强横的邪修陨落
           → 有概率发动夺舍（目标：弱小散修，低境界）
           → 成功：继承目标肉身 + 部分修为，阵营变邪，触发大事件
           → 失败：阴神消散
"""
from __future__ import annotations

import random
from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from src.classes.core.world import World
    from src.classes.core.avatar import Avatar

from src.classes.event import Event
from src.systems.cultivation import Realm, REALM_RANK


# 各境界的转生概率（该境界死亡后阴神保留概率）
_REINCARNATION_PROB = {
    Realm.Qi_Refinement: 0.0,
    Realm.Foundation_Establishment: 0.05,
    Realm.Core_Formation: 0.15,
    Realm.Nascent_Soul: 0.30,
    Realm.Soul_Formation: 0.45,
    Realm.Void_Refinement: 0.60,
    Realm.Body_Integration: 0.75,
    Realm.Mahayana: 0.90,
}

# 夺舍概率（邪修专属，额外乘以上面的概率）
_POSSESSION_EXTRA_PROB = 0.30


def try_trigger_reincarnation(world: "World", dead_avatar: "Avatar") -> List[Event]:
    """
    角色死亡后调用：检测是否触发转生或夺舍。
    返回生成的事件列表。
    """
    events: List[Event] = []

    realm = dead_avatar.cultivation_progress.realm
    base_prob = _REINCARNATION_PROB.get(realm, 0.0)

    if base_prob <= 0.0:
        return events

    if random.random() >= base_prob:
        return events

    from src.classes.alignment import Alignment

    # 邪修：优先尝试夺舍
    if dead_avatar.alignment == Alignment.EVIL:
        possession_events = _try_possession(world, dead_avatar)
        if possession_events:
            return possession_events
        # 夺舍失败：阴神消散，无法转生
        return events

    # 普通转生：阴神游荡，稍后投胎
    dead_avatar.soul_state = "wandering"
    events.append(_make_reincarnation_pending_event(world, dead_avatar))
    return events


def _make_reincarnation_pending_event(world: "World", avatar: "Avatar") -> Event:
    """生成阴神游荡事件"""
    from src.i18n import t
    text = t(
        "【轮回感应】{avatar} 魂魄未散，阴神游荡于天地间，或将寻机转世。",
        avatar=avatar.name,
    )
    ev = Event(world.month_stamp, text, related_avatars=[avatar.id], is_major=True)
    ev.event_type = "reincarnation_pending"
    return ev


def process_wandering_souls(world: "World") -> List[Event]:
    """
    每月调用：处理处于"游荡"状态的阴神，尝试投胎为新角色。
    """
    events: List[Event] = []

    dead_avatars = list(world.avatar_manager.dead_avatars.values())
    for avatar in dead_avatars:
        if getattr(avatar, "soul_state", "alive") != "wandering":
            continue

        # 每月 10% 概率触发投胎
        if random.random() < 0.10:
            birth_events = _do_reincarnation(world, avatar)
            events.extend(birth_events)

    return events


def _do_reincarnation(world: "World", past_avatar: "Avatar") -> List[Event]:
    """
    执行转生：以前世角色为模板生成新 NPC。
    """
    events: List[Event] = []

    try:
        from src.classes.core.avatar import Avatar
        from src.systems.cultivation import CultivationProgress
        from src.classes.age import Age
        from src.classes.root import Root
        from src.classes.items.magic_stone import MagicStone
        from src.utils.id_generator import get_avatar_id
        from src.systems.time import MonthStamp
        from src.utils.name_generator import get_random_name_for_sect

        # 新生婴儿：1级，随机位置（靠近前世出生地）
        pos_x = past_avatar.pos_x + random.randint(-10, 10)
        pos_y = past_avatar.pos_y + random.randint(-10, 10)
        pos_x = max(0, min(world.map.width - 1, pos_x))
        pos_y = max(0, min(world.map.height - 1, pos_y))

        new_name = get_random_name_for_sect(past_avatar.gender, None)
        age = Age(1, Realm.Qi_Refinement)
        birth_month_stamp = int(world.month_stamp) - 12

        new_avatar = Avatar(
            world=world,
            name=new_name,
            id=get_avatar_id(),
            birth_month_stamp=MonthStamp(birth_month_stamp),
            age=age,
            gender=past_avatar.gender,
            cultivation_progress=CultivationProgress(1),
            pos_x=pos_x,
            pos_y=pos_y,
        )
        new_avatar.magic_stone = MagicStone(50)
        new_avatar.tile = world.map.get_tile(pos_x, pos_y)

        # 标记为转世角色
        new_avatar.soul_state = "reincarnated"
        new_avatar.past_life_id = past_avatar.id

        # 继承前世隐藏天赋（保留1-2个）
        past_hidden = past_avatar.hidden_talents
        if past_hidden:
            inherited = random.sample(past_hidden, min(2, len(past_hidden)))
            for talent_id in inherited:
                if talent_id not in new_avatar.hidden_talents:
                    new_avatar.hidden_talents.append(talent_id)

        # 添加"宿慧"天赋（转世标志性天赋）
        if "INNATE_WISDOM" not in new_avatar.hidden_talents:
            new_avatar.hidden_talents.append("INNATE_WISDOM")

        # 轻微气运加成（前世有功德则气运更好）
        if past_avatar.karma < 0:
            new_avatar.modify_fortune(10.0)

        # 标记前世阴神已消散
        past_avatar.soul_state = "reincarnated"

        # 注册新角色到世界
        world.avatar_manager.register_avatar(new_avatar)

        from src.i18n import t
        text = t(
            "【轮回转世】{past_name} 的阴神历经游荡，终于投胎转世，以新生命{new_name}降临世间，携带前世记忆碎片。",
            past_name=past_avatar.name,
            new_name=new_avatar.name,
        )
        ev = Event(
            world.month_stamp,
            text,
            related_avatars=[past_avatar.id, new_avatar.id],
            is_major=True,
        )
        ev.event_type = "reincarnation"
        events.append(ev)

    except Exception:
        # 转生失败静默处理，避免影响主循环
        pass

    return events


def _try_possession(world: "World", evil_avatar: "Avatar") -> List[Event]:
    """
    夺舍：邪修元神尝试占据弱小散修肉身。
    """
    events: List[Event] = []

    # 寻找目标：境界比邪修低至少2级，且为散修（无宗门）
    own_rank = REALM_RANK.get(evil_avatar.cultivation_progress.realm, 0)
    candidates = [
        a for a in world.avatar_manager.avatars.values()
        if not a.is_dead
        and a.sect is None
        and REALM_RANK.get(a.cultivation_progress.realm, 0) <= max(0, own_rank - 2)
    ]

    if not candidates:
        return events

    target = random.choice(candidates)

    # 夺舍成功率：30% 基础，境界差越大成功率越高
    target_rank = REALM_RANK.get(target.cultivation_progress.realm, 0)
    rank_diff = own_rank - target_rank
    success_rate = min(0.8, 0.30 + rank_diff * 0.10)

    from src.i18n import t

    if random.random() < success_rate:
        # 夺舍成功
        old_name = evil_avatar.name
        old_realm = str(evil_avatar.cultivation_progress.realm)

        # 修改目标的属性
        from src.classes.alignment import Alignment
        target.alignment = Alignment.EVIL
        target.past_life_id = evil_avatar.id

        # 继承邪修的部分隐藏天赋
        for t_id in evil_avatar.hidden_talents[:2]:
            if t_id not in target.hidden_talents:
                target.hidden_talents.append(t_id)

        # 邪修阴神消散
        evil_avatar.soul_state = "reincarnated"

        # 修改目标气运/因果
        target.modify_karma(evil_avatar.karma * 0.5)
        target.modify_fortune(evil_avatar.fortune * 0.3)

        text = t(
            "【夺舍成功】{evil_name}（{realm}）元神强行夺舍{target_name}！{target_name}从此阵营大变，举止诡异，令周围修士心生警惕。",
            evil_name=old_name,
            realm=old_realm,
            target_name=target.name,
        )
        ev = Event(
            world.month_stamp,
            text,
            related_avatars=[evil_avatar.id, target.id],
            is_major=True,
        )
        ev.event_type = "possession"
        events.append(ev)
    else:
        # 夺舍失败，阴神消散
        evil_avatar.soul_state = "reincarnated"
        text = t(
            "【夺舍失败】{evil_name} 的阴神尝试夺舍失败，元神消散于天地间。",
            evil_name=evil_avatar.name,
        )
        ev = Event(
            world.month_stamp,
            text,
            related_avatars=[evil_avatar.id],
            is_major=True,
        )
        ev.event_type = "possession_failed"
        events.append(ev)

    return events


__all__ = [
    "try_trigger_reincarnation",
    "process_wandering_souls",
]
