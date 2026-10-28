import time, pandas as pd
from pawacast.targets.public import named_sites
from pawacast.features import build_features
pd.set_option("display.width", 220); pd.set_option("display.max_columns", 30)
s = named_sites().dropna(subset=["lat"])
t = time.time()
f = build_features(s, name="blodgett", refresh=True)
print(f"{time.time()-t:.0f}s")
print(s[["site", "kwh_cust_month", "survey_kwh_cust_month", "months_since_connection"]].round(2).to_string(index=False))
print(f.drop(columns=["lat", "lon"]).round(2).to_string(index=False))
