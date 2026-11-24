"""Deterministic synthetic history, never presented as real bakery results."""
import math
import pandas as pd


def make_demo_data(days: int = 84, end_date="2026-10-31") -> pd.DataFrame:
    rows = []
    for i, date in enumerate(pd.date_range(end=end_date, periods=days, freq="D")):
        for j, (product, base) in enumerate((("Barra", 110), ("Integral", 55), ("Croissant", 75))):
            weekend = 1.3 if date.weekday() >= 5 else 1.0
            units = max(0, round(base * weekend + 7 * math.sin(i * 0.8 + j)))
            rows.append({"fecha": date.strftime("%Y-%m-%d"), "articulo": product, "unidades": units})
    return pd.DataFrame(rows)
