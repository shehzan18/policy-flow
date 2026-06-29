def discount(price, pct):
    if pct < 0 or pct > 100:
        raise ValueError("bad pct")
    return price * (1 - pct / 100)
