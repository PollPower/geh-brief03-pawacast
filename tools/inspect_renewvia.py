"""Inspect Renewvia metadata tables: schemas and project list. No consumption values are read."""
import pathlib, pandas as pd
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40); pd.set_option("display.max_colwidth", 40)
R = pathlib.Path("data/raw/renewvia")
for name in ["minigridprojects", "meteringbasestations", "tariffs", "meteringplatformtariffs", "customers", "sparkmetercustomers"]:
    p = R / f"{name}.parquet"
    if not p.exists():
        print(name, "missing"); continue
    d = pd.read_parquet(p)
    print(f"\n== {name}: {d.shape}")
    print(d.dtypes.to_string())
    if name == "minigridprojects":
        print(d.to_string(max_rows=40))
    elif name == "customers":
        for c in d.columns:
            if d[c].nunique() < 15:
                print(c, d[c].value_counts(dropna=False).to_dict())
