"""
NPC 间交易：同区域两修士达成以物易灵石，由 LLM 生成古风叙事。
"""
from __future__ import annotations

import random
from typing import TYPE_CHECKING, List, Optional

from src.classes.event import Event
from src.classes.prices import prices
from src.utils.config import CONFIG

if TYPE_CHECKING:
    from src.classes.core.world import World
    from src.classes.core.avatar import Avatar
    from src.classes.material import Material


def _find_trade_candidates(world: "World") -> List[tuple["Avatar", "Avatar", "Material"]]:
    """找出可交易的 (卖家, 买家, 材料) 列表：同区域、卖家有材料、买家灵石足够。"""
    from src.classes.material import Material

    candidates: List[tuple["Avatar", "Avatar", "Material"]] = []
    living = world.avatar_manager.get_living_avatars()

    for seller in living:
        if not getattr(seller, "can_trigger_world_event", True) or seller.tile is None or seller.tile.region is None:
            continue
        if not seller.materials:
            continue
        others = world.avatar_manager.get_avatars_in_same_region(seller)
        for buyer in others:
            if buyer is seller or not getattr(buyer, "can_trigger_world_event", True):
                continue
            # 卖家拥有的材料中，买家能付得起价的都加入候选
            for mat, qty in seller.materials.items():
                if qty <= 0:
                    continue
                if not isinstance(mat, Material):
                    continue
                base_price = prices.get_selling_price(mat, seller)
                min_price = max(1, int(base_price * 0.8))
                if buyer.magic_stone.value >= min_price:
                    candidates.append((seller, buyer, mat))
    return candidates


async def try_trigger_npc_trade(world: "World") -> List[Event]:
    """
    月度结算时尝试触发一次 NPC 间交易。
    条件：同区域两人，一方有材料可售、另一方灵石足够；价格在系统价 ±20% 内随机。
    成功后转移物品与灵石，并生成事件（优先 LLM 古风描述）。
    """
    events: List[Event] = []
    prob = float(getattr(CONFIG.game, "npc_trade_probability", 0.02))
    if prob <= 0 or random.random() >= prob:
        return events

    candidates = _find_trade_candidates(world)
    if not candidates:
        return events

    seller, buyer, material = random.choice(candidates)
    base_price = prices.get_selling_price(material, seller)
    price = max(1, int(base_price * random.uniform(0.8, 1.2)))
    if buyer.magic_stone.value < price:
        return events

    # 执行交易
    seller.remove_material(material, 1)
    buyer.add_material(material, 1)
    seller.magic_stone = seller.magic_stone + price
    buyer.magic_stone = buyer.magic_stone - price

    # 生成事件描述
    content = await _generate_trade_story(seller, buyer, material.name, price)
    if not content:
        from src.i18n import t
        content = t(
            "npc_trade_fallback",
            seller=seller.name,
            buyer=buyer.name,
            item=material.name,
            amount=price,
        )

    events.append(Event(
        world.month_stamp,
        content,
        related_avatars=[seller.id, buyer.id],
        is_major=False,
        event_type="npc_trade",
    ))
    return events


async def _generate_trade_story(
    seller: "Avatar",
    buyer: "Avatar",
    item_name: str,
    price: int,
) -> Optional[str]:
    """调用 LLM 生成一两句古风交易描述；失败则返回 None。"""
    from pathlib import Path
    from src.utils.llm.client import call_llm_with_template
    from src.utils.llm.exceptions import LLMError

    # 价格文言化
    price_phrase = _price_to_phrase(price)
    template_path = Path(CONFIG.paths.templates) / "npc_trade.txt"
    if not template_path.exists():
        return None

    infos = {
        "seller_name": seller.name,
        "buyer_name": buyer.name,
        "item_name": item_name,
        "price_phrase": price_phrase,
    }

    try:
        result = await call_llm_with_template(
            template_path=template_path,
            infos=infos,
        )
        if isinstance(result, dict) and result.get("story"):
            return str(result["story"]).strip()
    except (LLMError, Exception):
        pass
    return None


def _price_to_phrase(price: int) -> str:
    """将灵石数量转为简短文言表述。"""
    if price >= 10000:
        return f"{price // 10000}万灵石"
    if price >= 1000:
        return f"{price // 1000}千灵石"
    if price >= 100:
        return f"{price // 100}百灵石"
    return f"{price}灵石"
