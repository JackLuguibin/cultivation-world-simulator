"""
灵石与天地灵气经济
- 灵脉产出：有主洞府/遗迹每年按天地灵气结算灵石给占据者
"""
from __future__ import annotations

from typing import TYPE_CHECKING, List

from src.classes.event import Event
from src.systems.time import Month
from src.utils.config import CONFIG

if TYPE_CHECKING:
    from src.classes.core.world import World


def process_spirit_vein_output(world: "World") -> List[Event]:
    """
    灵脉产出：每年一月，有主洞府/遗迹的占据者获得灵石。
    产出量 = spirit_vein_output_base * world_spirit_qi * (区域灵气密度/10)
    """
    events: List[Event] = []
    if world.month_stamp.get_month() != Month.JANUARY:
        return events

    base = int(getattr(CONFIG.game, "spirit_vein_output_base", 50))
    qi = getattr(world, "world_spirit_qi", 0.6)
    qi = max(0.0, min(1.0, float(qi)))

    from src.classes.environment.region import CultivateRegion

    for region in world.map.regions.values():
        if not isinstance(region, CultivateRegion) or not region.host_avatar:
            continue
        if region.host_avatar.is_dead:
            continue
        # 密度系数 0.1～1.0
        density_factor = 0.1 + 0.9 * (region.essence_density / 10.0)
        amount = max(1, int(base * qi * density_factor))
        region.host_avatar.magic_stone = region.host_avatar.magic_stone + amount
        from src.i18n import t
        content = t("{avatar} gained {amount} spirit stones from the spirit vein at {region}.",
                   avatar=region.host_avatar.name, region=region.name, amount=amount)
        events.append(Event(
            world.month_stamp,
            content,
            related_avatars=[region.host_avatar.id],
            is_major=False,
        ))
    return events
