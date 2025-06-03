# app/core/leveling.py

def xp_to_level(xp: int) -> int:
    """
    Sample leveling curve:
     - Level 1: 0 ≤ xp < 100
     - Level 2: 100 ≤ xp < 250
     - Level 3: 250 ≤ xp < 500
     - Level 4: 500 ≤ xp < 900
     - and so on…
    """
    if xp < 100:
        return 1
    elif xp < 250:
        return 2
    elif xp < 500:
        return 3
    elif xp < 900:
        return 4
    else:
        return (xp // 500) + 1
