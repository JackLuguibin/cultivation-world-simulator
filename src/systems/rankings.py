"""
排行榜数据：修为榜、宗门榜、长寿榜、异宝榜
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.systems.cultivation import REALM_RANK, Realm

if TYPE_CHECKING:
    from src.classes.core.world import World


def get_realm_rank(world: "World", top_n: int = 15) -> list[dict[str, Any]]:
    """修为榜：按境界+等级排序，取前 top_n"""
    living = [
        a for a in world.avatar_manager.get_living_avatars()
    ]
    def key(a):
        cp = a.cultivation_progress
        realm_rank = REALM_RANK.get(cp.realm, 0)
        return (realm_rank, cp.level)
    living.sort(key=key, reverse=True)
    result = []
    for i, a in enumerate(living[:top_n], 1):
        result.append({
            "rank": i,
            "id": str(a.id),
            "name": a.name,
            "realm": a.cultivation_progress.realm.value,
            "level": a.cultivation_progress.level,
        })
    return result


def get_sect_rank(world: "World", top_n: int = 10) -> list[dict[str, Any]]:
    """宗门榜：按成员数排序"""
    sect_count: dict[str, list[str]] = {}
    for a in world.avatar_manager.get_living_avatars():
        name = a.sect.name if a.sect else "散修"
        if name not in sect_count:
            sect_count[name] = []
        sect_count[name].append(a.name)
    items = [
        {"name": name, "count": len(members), "members": members[:5]}
        for name, members in sect_count.items()
    ]
    items.sort(key=lambda x: x["count"], reverse=True)
    return [{"rank": i + 1, **x} for i, x in enumerate(items[:top_n])]


def get_age_rank(world: "World", top_n: int = 15) -> list[dict[str, Any]]:
    """长寿榜：按年龄降序"""
    living = list(world.avatar_manager.get_living_avatars())
    living.sort(key=lambda a: a.age.age, reverse=True)
    return [
        {"rank": i + 1, "id": str(a.id), "name": a.name, "age": a.age.age}
        for i, a in enumerate(living[:top_n])
    ]


def get_treasure_rank(world: "World", top_n: int = 20) -> list[dict[str, Any]]:
    """异宝榜：兵器与辅助装备，按境界排序，来源为角色装备 + 流通池"""
    entries: list[tuple[int, int, dict[str, Any]]] = []  # (realm_rank, mastery_or_0, payload)

    for a in world.avatar_manager.get_living_avatars():
        if a.weapon:
            r = REALM_RANK.get(a.weapon.realm, 0)
            m = getattr(a.weapon, "mastery", 0) or 0
            entries.append((r, m, {
                "item_id": a.weapon.id,
                "name": a.weapon.name,
                "grade": a.weapon.realm.value,
                "type": "weapon",
                "owner_id": str(a.id),
                "owner_name": a.name,
                "in_circulation": False,
            }))
        if a.auxiliary:
            r = REALM_RANK.get(a.auxiliary.realm, 0)
            m = getattr(a.auxiliary, "mastery", 0) or 0
            entries.append((r, m, {
                "item_id": a.auxiliary.id,
                "name": a.auxiliary.name,
                "grade": a.auxiliary.realm.value,
                "type": "auxiliary",
                "owner_id": str(a.id),
                "owner_name": a.name,
                "in_circulation": False,
            }))

    circ = world.circulation
    for w in circ.sold_weapons:
        r = REALM_RANK.get(w.realm, 0)
        entries.append((r, 0, {
            "item_id": w.id,
            "name": w.name,
            "grade": w.realm.value,
            "type": "weapon",
            "owner_id": None,
            "owner_name": None,
            "in_circulation": True,
        }))
    for aux in circ.sold_auxiliaries:
        r = REALM_RANK.get(aux.realm, 0)
        entries.append((r, 0, {
            "item_id": aux.id,
            "name": aux.name,
            "grade": aux.realm.value,
            "type": "auxiliary",
            "owner_id": None,
            "owner_name": None,
            "in_circulation": True,
        }))

    entries.sort(key=lambda x: (x[0], x[1]), reverse=True)
    return [{"rank": i + 1, **e[2]} for i, e in enumerate(entries[:top_n])]


def get_all_rankings(world: "World") -> dict[str, list[dict[str, Any]]]:
    return {
        "realm": get_realm_rank(world),
        "sect": get_sect_rank(world),
        "age": get_age_rank(world),
        "treasure": get_treasure_rank(world),
    }
