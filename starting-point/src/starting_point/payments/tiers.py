from starting_point.models import TIER_DEFINITIONS


def get_tiers() -> list[dict]:
    return [
        {**v, "key": k}
        for k, v in TIER_DEFINITIONS.items()
        if v["price_fen"] > 0
    ]
