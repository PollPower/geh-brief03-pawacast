"""Inspect minigridprojects capex columns. No consumption."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

p = Path("data/raw/renewvia/minigridprojects.parquet")
df = pd.read_parquet(p)
print("columns:", list(df.columns))
keep = [c for c in df.columns if c.lower() in
        {"projectname", "country", "currency", "sizepv", "sizebattery", "typebattery",
         "capex", "powerondate", "peakloadcapacity", "solarpanelscount"}]
# print a compact view
cols = [c for c in ["projectName", "country", "currency", "sizePv", "sizeBattery",
                    "typeBattery", "capex", "powerOnDate"] if c in df.columns]
pd.set_option("display.width", 220)
pd.set_option("display.max_rows", 30)
print(df[cols].to_string(index=False))
print("n", len(df))
print(df[cols].describe(include="all"))
