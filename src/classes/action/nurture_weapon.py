from __future__ import annotations

from src.i18n import t
from src.classes.action import TimedAction
from src.classes.event import Event
import random


class NurtureWeapon(TimedAction):
    """
    温养兵器：花时间温养兵器，可以较多增加熟练度
    """
    
    # 多语言 ID
    ACTION_NAME_ID = "nurture_weapon_action_name"
    DESC_ID = "nurture_weapon_description"
    REQUIREMENTS_ID = "nurture_weapon_requirements"
    
    # 不需要翻译的常量
    EMOJI = "✨"
    PARAMS = {}

    duration_months = 3

    def _execute(self) -> None:
        from src.systems.cultivation import Realm
        from src.classes.items.weapon import get_random_weapon_by_realm
        
        # 温养兵器增加较多熟练度（5-10）
        proficiency_gain = random.uniform(5.0, 10.0)
        self.avatar.increase_weapon_proficiency(proficiency_gain)

        # 提升认主度，检测器灵觉醒
        if self.avatar.weapon:
            spirit_awakened = self.avatar.weapon.increase_mastery(random.randint(5, 15))
            if spirit_awakened:
                spirit_name = self.avatar.weapon.weapon_spirit
                content = t(
                    "【器灵觉醒】{avatar} 的兵器『{weapon}』器灵觉醒，化名{spirit}！器灵可在危急关头护主。",
                    avatar=self.avatar.name,
                    weapon=self.avatar.weapon.name,
                    spirit=spirit_name,
                )
                from src.classes.event import Event as EvClass
                ev = EvClass(
                    self.world.month_stamp,
                    content,
                    related_avatars=[self.avatar.id],
                    is_major=True,
                )
                ev.event_type = "spirit_awakening"
                self.avatar.add_event(ev)
                # 天赋指标追踪
                from src.systems.talent import increment_talent_metric
                increment_talent_metric(self.avatar, "weapon_use", 10)
        
        # 如果是练气兵器，有概率升级为筑基兵器
        if self.avatar.weapon and self.avatar.weapon.realm == Realm.Qi_Refinement:
            # 基础5%概率 + 来自effects的额外概率
            base_upgrade_chance = 0.05
            extra_chance_raw = self.avatar.effects.get("extra_weapon_upgrade_chance", 0.0)
            extra_chance = max(0.0, min(1.0, float(extra_chance_raw or 0.0)))
            total_chance = min(1.0, base_upgrade_chance + extra_chance)
            
            if random.random() < total_chance:
                treasure_weapon = get_random_weapon_by_realm(Realm.Foundation_Establishment, self.avatar.weapon.weapon_type)
                if treasure_weapon:
                    old_weapon_name = self.avatar.weapon.name
                    old_proficiency = self.avatar.weapon_proficiency
                    # 深拷贝宝物兵器并更换（会重新计算长期效果）
                    # get_random_weapon_by_realm 已经返回了副本，但再次copy也无妨
                    new_weapon = treasure_weapon.instantiate()
                    self.avatar.change_weapon(new_weapon)
                    # 恢复熟练度（change_weapon 会归零，需要手动恢复）
                    self.avatar.weapon_proficiency = old_proficiency
                    # 记录升华事件
                    from src.classes.event import Event
                    content = t("{avatar} nurturing {old_weapon}, the weapon's spirituality greatly increased, evolved into {new_weapon}!",
                               avatar=self.avatar.name, old_weapon=old_weapon_name, new_weapon=treasure_weapon.name)
                    self.avatar.add_event(Event(
                        self.world.month_stamp,
                        content,
                        related_avatars=[self.avatar.id]
                    ))

    def can_start(self) -> tuple[bool, str]:
        # 任何时候都可以温养兵器
        return (True, "")

    def start(self) -> Event:
        weapon_name = self.avatar.weapon.name if self.avatar.weapon else t("weapon")
        content = t("{avatar} begins nurturing {weapon}",
                   avatar=self.avatar.name, weapon=weapon_name)
        return Event(
            self.world.month_stamp,
            content,
            related_avatars=[self.avatar.id]
        )

    async def finish(self) -> list[Event]:
        weapon_name = self.avatar.weapon.name if self.avatar.weapon else t("weapon")
        proficiency = self.avatar.weapon_proficiency
        # 注意：升华事件已经在_execute中添加，这里只添加完成事件
        content = t("{avatar} finished nurturing {weapon}, proficiency increased to {proficiency}%",
                   avatar=self.avatar.name, weapon=weapon_name, proficiency=f"{proficiency:.1f}")
        return [
            Event(
                self.world.month_stamp,
                content,
                related_avatars=[self.avatar.id]
            )
        ]

