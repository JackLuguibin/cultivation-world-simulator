from __future__ import annotations
from typing import TYPE_CHECKING, Union
from src.classes.death_reason import DeathReason

if TYPE_CHECKING:
    from src.classes.core.world import World
    from src.classes.core.avatar import Avatar

def handle_death(world: World, avatar: Avatar, reason: Union[str, DeathReason]) -> None:
    """
    处理角色死亡的统一入口。
    负责将角色标记为死亡，清理行动队列，但保留角色数据。
    
    Args:
        world: 世界对象
        avatar: 死亡的角色
        reason: 死亡原因（DeathReason对象或字符串）
    """
    reason_str = str(reason)
    
    # 标记为死亡（软删除）
    avatar.set_dead(reason_str, world.month_stamp)
    
    # 从管理器中归档（硬移动），并记录变更
    world.avatar_manager.handle_death(avatar.id)

    # 转生/夺舍：异步触发（通过 world._pending_reincarnation_events 暂存）
    try:
        from src.systems.reincarnation import try_trigger_reincarnation
        events = try_trigger_reincarnation(world, avatar)
        if events:
            # 将事件暂存到 world，由 simulator 在下一阶段统一收集
            if not hasattr(world, "_pending_reincarnation_events"):
                world._pending_reincarnation_events = []
            world._pending_reincarnation_events.extend(events)
    except Exception:
        pass
