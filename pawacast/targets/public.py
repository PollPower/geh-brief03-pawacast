"""Public ground truth for mini-grid demand. No open site-level metered dataset exists for
East/West Africa (checked 28 Oct 2026), so we use:

1. NAMED_SITES: measured per-customer consumption at named sites from published papers.
   Used ONLY for held-out validation, never for fitting.
2. AMDA: country / regional benchmarks (kWh per customer per month) from AMDA's
   Benchmarking Africa's Minigrids reports. Used to set priors.
3. GROWTH: published post-connection growth observations.

Coordinates are geocoded from village names (OSM Nominatim); `geo_conf` says how sure we are.
"""
import pandas as pd

DAYS_PER_MONTH = 30.44

# Blodgett et al. (2017), Energy for Sustainable Development, Table 1 + Table 4.
# Measured 30 Nov 2015 - 29 Nov 2016; "actual" = site-subset total Wh/day for n customers.
_BLODGETT = [
    # site,        commissioned, customers, n_subset, actual_Wh_day, survey_Wh_day, lat,     lon,     geo_conf
    ("Barsaloi",    "2014-10", 58, 29, 1680, 12418,  1.33836, 36.8599, "high"),
    ("Enkoireroi",  "2014-09", 27, 15, 1246,  7746,  None,    None,    "none"),
    ("Entesopia",   "2014-12", 63, 31, 7132, 19703, -1.7840,  36.0533, "medium"),
    ("Marti",       "2015-04", 29, 24, 2326, 11361,  1.47513, 36.7228, "medium"),
    ("Merile",      "2014-10", 27, 18, 1794, 14676,  1.41568, 37.7224, "medium"),
    ("Namba Koloo", "2014-09", 19,  7,  301,  1392, -1.0229,  34.3051, "low"),
    # Olenarau: only a stream of that name is mapped (GeoNames 182313, Kajiado); village position is approximate
    ("Olenarau",    "2014-10", 29, 11, 1352,  2526, -1.94790, 37.03542, "low"),
    ("Opiroi",      "2014-10", 26, 19, 1565,  2537,  1.15865, 36.8095, "high"),
]

def named_sites() -> pd.DataFrame:
    df = pd.DataFrame(_BLODGETT, columns=["site", "commissioned", "customers", "n_subset",
                                          "actual_wh_day", "survey_wh_day", "lat", "lon", "geo_conf"])
    df["country"] = "KE"
    df["source"] = "Blodgett et al. 2017, ESD 41:88-105"
    df["kwh_cust_month"] = df.actual_wh_day / df.n_subset * DAYS_PER_MONTH / 1000
    df["survey_kwh_cust_month"] = df.survey_wh_day / df.n_subset * DAYS_PER_MONTH / 1000
    # months since commissioning at the middle of the measurement year (31 May 2016)
    mid = pd.Timestamp("2016-05-31")
    df["months_since_connection"] = ((mid - pd.to_datetime(df.commissioned)).dt.days / DAYS_PER_MONTH).round(1)
    df["site_id"] = "blodgett_" + df.site.str.lower().str.replace(" ", "_")
    # Set A = scored by pre-sprint model v0 (results seen). Set B = never scored before the sprint.
    df["eval_set"] = df.site.map(lambda s: "B" if s == "Olenarau" else ("unlocated" if s == "Enkoireroi" else "A"))
    df["segment_note"] = ""
    return pd.concat([df, _ethiopia()], ignore_index=True)

# Wassie & Ahlgren 2024, Energy Policy 185:113969, Table 1 and section 3.1.3.
# Site mean kWh/day over May 2021 - Dec 2022 (610 days); customers = Dec 2021 snapshot.
# Coordinates: paper (Tum) and OSM town centre (Omorate; the paper's printed latitude is malformed).
def _ethiopia() -> pd.DataFrame:
    rows = [
        # site,     commissioned, customers, kWh/day, lat,      lon,      geo_conf, note
        ("Tum",     "2021-05", 450,  640, 6.25636, 35.52169, "high",
         "384 households / 40 SMEs / 26 institutions; household billing mean 22.2 kWh/month"),
        ("Omorate", "2021-05", 443, 1065, 4.80324, 36.05043, "high",
         "301 households / 112 SMEs / 30 institutions; demand suppressed by load-shedding (13 h/day by Dec 2022)"),
    ]
    df = pd.DataFrame(rows, columns=["site", "commissioned", "customers", "kwh_day", "lat", "lon", "geo_conf", "segment_note"])
    df["n_subset"] = df.customers
    df["kwh_cust_month"] = df.kwh_day * DAYS_PER_MONTH / df.customers
    df["survey_kwh_cust_month"] = float("nan")
    df["months_since_connection"] = 10.0   # midpoint of a 20-month measurement window starting at connection
    df["country"] = "ET"
    df["source"] = "Wassie & Ahlgren 2024, Energy Policy 185:113969"
    df["site_id"] = "wassie_" + df.site.str.lower()
    df["eval_set"] = "B"
    return df.drop(columns=["kwh_day"])

# Published sites that CANNOT be located (anonymised or no coordinates). Not scored per site;
# used only in the aggregate check against country averages (EVAL_PLAN set C).
UNLOCATED = pd.DataFrame([
    ("Scott & Coley 2021, Site A (island)", "TZ", 358, 3.17, "Energies 14:4207, Table 3; 2019"),
    ("Scott & Coley 2021, Site D (village)", "TZ", 135, 2.71, "Energies 14:4207, Table 3; 2019"),
    ("Hartvigsson et al. 2021, SW highlands hydro", "TZ", 1544, 33.9, "ESD 60:82-89; 3.5 days of logging only"),
    ("Mthembanji, Dedza", "MW", 60, 8.85, "Strathclyde 2022 technical report; 2021 sales / 60 customers"),
    ("Sierra Leone, ~40 sites (average)", "SL", None, 5.0, "CrossBoundary night-lights study; '4-6 kWh per month per connection'"),
], columns=["site", "country", "customers", "kwh_cust_month", "source"])

# AMDA benchmarks, kWh per customer per month.
AMDA = pd.DataFrame([
    # country/region, year, kwh, source
    ("KE", 2019, 4.1, "AMDA BAM 2022, Table 1"), ("KE", 2020, 3.7, "AMDA BAM 2022, Table 1"),
    ("TZ", 2019, 6.0, "AMDA BAM 2022, Table 1"), ("TZ", 2020, 8.0, "AMDA BAM 2022, Table 1"),
    ("NG", 2019, 15.8, "AMDA BAM 2022, Table 1"), ("NG", 2020, 11.0, "AMDA BAM 2022, Table 1"),
    ("SL", 2019, 1.0, "AMDA BAM 2022, Table 1"), ("SL", 2020, 6.4, "AMDA BAM 2022, Table 1"),
    ("MG", 2019, 8.1, "AMDA BAM 2022, Table 1"), ("MG", 2020, 6.8, "AMDA BAM 2022, Table 1"),
    ("ZM", 2019, 1.5, "AMDA BAM 2022, Table 1"), ("ZM", 2020, 1.5, "AMDA BAM 2022, Table 1"),
    ("EAST_SOUTH", 2023, 10.0, "AMDA BAM 2024, Table 6"), ("WEST_CENTRAL", 2023, 24.0, "AMDA BAM 2024, Table 6"),
], columns=["area", "year", "kwh_cust_month", "source"])

# AMDA BAM 2024 Table 7: residential vs commercial customers.
SEGMENTS = pd.DataFrame([
    ("EAST_SOUTH", "residential", 6.0), ("EAST_SOUTH", "commercial", 13.1),
    ("WEST_CENTRAL", "residential", 8.1), ("WEST_CENTRAL", "commercial", 39.8),
], columns=["region", "segment", "kwh_cust_month"])

# Growth after connection.
GROWTH = pd.DataFrame([
    ("Blodgett 2017 (8 KE sites)", "8% per year over first two years", 0.08),
    ("Wassie & Ahlgren 2024 (Tum, ET)", "+90% daily consumption over 20 months", (1.9 ** (12 / 20)) - 1),
    ("CrossBoundary tariff pilot (TZ, high users)", "10.1 -> 14.7 kWh over two years", (14.7 / 10.1) ** 0.5 - 1),
], columns=["source", "observation", "annual_growth"])

REGION = {"KE": "EAST_SOUTH", "TZ": "EAST_SOUTH", "UG": "EAST_SOUTH", "RW": "EAST_SOUTH", "ET": "EAST_SOUTH",
          "ZM": "EAST_SOUTH", "MG": "EAST_SOUTH", "MW": "EAST_SOUTH", "NG": "WEST_CENTRAL", "SL": "WEST_CENTRAL", "GH": "WEST_CENTRAL",
          "SN": "WEST_CENTRAL", "CM": "WEST_CENTRAL", "CD": "WEST_CENTRAL", "BJ": "WEST_CENTRAL"}
