"""Renewvia site-month demand targets.

Source: Selby, Renewvia mini-grid operational dataset, Zenodo 10.5281/zenodo.22149101, CC BY-SA 4.0.
Derived site-month aggregates are released under the same licence.

Target: mean kWh per active customer meter per month, by months since powerOnDate.
Active = at least one 15-min slot with imputation_method = 'observed' in that month.
Partial months: per meter, kWh/day over days with slots, then x 30.44; drop site-months
with fewer than 10 active meters or fewer than 20 site-days of observed data.

Held-out consumption (role == 'test' in renewvia_split.csv) is sealed at BUILD time:
those readings files are never opened unless PAWACAST_FINAL_EVAL=1. The loader also
refuses test rows without that flag. Set B published sites are not in this dataset.
"""
from __future__ import annotations

import os
import pathlib
import sys
from dataclasses import dataclass

import duckdb
import pandas as pd

from .public import DAYS_PER_MONTH

ROOT = pathlib.Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw" / "renewvia"
TARGET_DIR = ROOT / "data" / "targets"
TRAIN_PATH = TARGET_DIR / "renewvia_site_months_train.parquet"
TEST_PATH = TARGET_DIR / "renewvia_site_months_test.parquet"
SPLIT_CSV = pathlib.Path(__file__).resolve().parent / "renewvia_split.csv"
CUSTOMERS = RAW / "customers.parquet"
PART_DIR = TARGET_DIR / "_parts"

# EVAL_PLAN Amendment 1. Filename stems of sparkmeterreadings_clean_*.parquet.
TEST_SITES = frozenset({"Balep", "Bendeghe-Afi", "Opu", "Ozuzu", "Kapelbok"})
TEST_FILE_STEMS = frozenset(TEST_SITES)
MIN_ACTIVE = 10
MIN_DAYS = 20
TZ_HOURS = {"Kenya": 3, "Nigeria": 1, "KE": 3, "NG": 1}


class HeldOutError(RuntimeError):
    """Held-out Renewvia consumption was requested or about to be read without the flag."""


def final_eval_enabled() -> bool:
    return os.environ.get("PAWACAST_FINAL_EVAL", "") == "1"


def site_id_of(project_name: str) -> str:
    slug = project_name.lower().replace(" ", "_").replace("-", "_")
    while "__" in slug:
        slug = slug.replace("__", "_")
    return "renewvia_" + slug


def tariff_class(tariff) -> str:
    if tariff is None or (isinstance(tariff, float) and pd.isna(tariff)):
        return "other"
    t = str(tariff).strip()
    if t == "Residential" or t.startswith("Tariff "):
        return "residential"
    if t == "Commercial":
        return "commercial"
    if t == "Religious Institution":
        return "institution"
    return "other"


def readings_path_is_sealed(path: pathlib.Path) -> bool:
    name = path.name
    prefix = "sparkmeterreadings_clean_"
    if not name.startswith(prefix) or not name.endswith(".parquet"):
        return False
    stem = name[len(prefix) : -len(".parquet")]
    return stem in TEST_FILE_STEMS


def ensure_readings_allowed(path: pathlib.Path) -> None:
    """Raise before any read_parquet on a sealed test-site readings file."""
    if readings_path_is_sealed(path) and not final_eval_enabled():
        raise HeldOutError(
            f"sealed held-out readings file {path.name}; set PAWACAST_FINAL_EVAL=1 to open"
        )


def _q(s: str) -> str:
    return "'" + str(s).replace("'", "''") + "'"


def _connect() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    con.execute("SET memory_limit='400MB'")
    con.execute("SET threads=2")
    tmp = ROOT / "data" / "tmp" / "duckdb"
    tmp.mkdir(parents=True, exist_ok=True)
    con.execute(f"SET temp_directory='{tmp.as_posix()}'")
    return con


def clean_files_for(project_name: str) -> list[pathlib.Path]:
    """Map minigrid projectName to gap-filled readings parquet files. Does not open them."""
    if project_name == "Kalobeyei Settlement":
        return sorted(RAW.glob("sparkmeterreadings_clean_Kalobeyei_Settlement_Village_*.parquet"))
    if project_name == "Kakuma 3 - Okapi":
        p = RAW / "sparkmeterreadings_clean_Kakuma_3A.parquet"
        return [p] if p.exists() else []
    stem = project_name.replace(" ", "_")
    p = RAW / f"sparkmeterreadings_clean_{stem}.parquet"
    return [p] if p.exists() else []


@dataclass
class SiteJob:
    project_name: str
    country: str
    lat: float
    lon: float
    power_on: pd.Timestamp
    group: str
    role: str
    tz_hours: int
    files: list[pathlib.Path]


def load_split() -> pd.DataFrame:
    s = pd.read_csv(SPLIT_CSV)
    s["powerOnDate"] = pd.to_datetime(s["powerOnDate"])
    return s


def iter_build_jobs(final_eval: bool | None = None) -> list[SiteJob]:
    """Sites whose readings may be opened. Test sites are omitted unless final eval."""
    if final_eval is None:
        final_eval = final_eval_enabled()
    jobs: list[SiteJob] = []
    for r in load_split().itertuples(index=False):
        if r.role == "test" and not final_eval:
            continue
        files = clean_files_for(r.projectName)
        jobs.append(
            SiteJob(
                project_name=r.projectName,
                country=r.country,
                lat=float(r.lat),
                lon=float(r.long),
                power_on=pd.Timestamp(r.powerOnDate),
                group=r.group,
                role=r.role,
                tz_hours=int(TZ_HOURS[r.country]),
                files=files,
            )
        )
    jobs.sort(key=lambda j: sum(p.stat().st_size if p.exists() else 0 for p in j.files))
    return jobs


def _slot_select(path: pathlib.Path, tz_hours: int, year: int | None) -> str:
    year_filter = ""
    if year is not None:
        year_filter = (
            f" AND slot_start >= TIMESTAMP '{year}-01-01' "
            f"AND slot_start < TIMESTAMP '{year + 1}-01-01'"
        )
    return f"""
      SELECT
        r.meter_customer_code,
        r.energy_kwh,
        r.imputation_method,
        r.slot_start + (INTERVAL 1 HOUR) * {int(tz_hours)} AS local_ts
      FROM read_parquet({_q(path.as_posix())}) r
      INNER JOIN cust c ON r.meter_customer_code = c.meter_customer_code
      WHERE 1=1 {year_filter}
    """


def _create_cust(con: duckdb.DuckDBPyConnection, project_name: str) -> int:
    con.execute("DROP TABLE IF EXISTS cust")
    con.execute(
        f"""
        CREATE TEMP TABLE cust AS
        SELECT customerAccountNumber AS meter_customer_code, tariff
        FROM read_parquet({_q(CUSTOMERS.as_posix())})
        WHERE projectName = {_q(project_name)}
          AND meterRole IN ('Customer Meter', 'Customer meter')
        """
    )
    n = con.execute("SELECT COUNT(*) FROM cust").fetchone()[0]
    return int(n)


def _query_file(
    con: duckdb.DuckDBPyConnection, path: pathlib.Path, tz_hours: int, year: int | None
) -> tuple[pd.DataFrame, pd.DataFrame]:
    slots = _slot_select(path, tz_hours, year)
    mm = con.execute(
        f"""
        WITH s AS ({slots}),
        t AS (
          SELECT meter_customer_code, energy_kwh, imputation_method,
                 date_trunc('month', local_ts) AS month_start,
                 CAST(local_ts AS DATE) AS local_date
          FROM s
        )
        SELECT
          t.meter_customer_code,
          t.month_start,
          ANY_VALUE(c.tariff) AS tariff,
          SUM(t.energy_kwh) AS kwh,
          SUM(CASE WHEN t.imputation_method = 'observed' THEN t.energy_kwh ELSE 0 END) AS kwh_observed,
          SUM(CASE WHEN t.imputation_method <> 'observed' THEN t.energy_kwh ELSE 0 END) AS kwh_imputed,
          COUNT(*) FILTER (WHERE t.imputation_method = 'observed') AS n_observed_slots,
          COUNT(DISTINCT t.local_date) AS n_days,
          COUNT(DISTINCT t.local_date) FILTER (WHERE t.imputation_method = 'observed') AS n_days_observed
        FROM t
        INNER JOIN cust c ON t.meter_customer_code = c.meter_customer_code
        GROUP BY t.meter_customer_code, t.month_start
        """
    ).fetchdf()
    days = con.execute(
        f"""
        WITH s AS ({slots})
        SELECT
          date_trunc('month', local_ts) AS month_start,
          CAST(local_ts AS DATE) AS local_date,
          BOOL_OR(imputation_method = 'observed') AS has_observed
        FROM s
        GROUP BY 1, 2
        """
    ).fetchdf()
    return mm, days


def _aggregate_file(
    con: duckdb.DuckDBPyConnection, path: pathlib.Path, tz_hours: int
) -> tuple[pd.DataFrame, pd.DataFrame]:
    ensure_readings_allowed(path)
    try:
        return _query_file(con, path, tz_hours, year=None)
    except Exception as e:
        msg = str(e).lower()
        if "memory" not in msg and "out of memory" not in msg:
            raise
        print(f"    memory pressure on {path.name}; retrying by year", flush=True)
        mm_parts, day_parts = [], []
        for year in range(2018, 2027):
            mm, days = _query_file(con, path, tz_hours, year=year)
            if len(mm):
                mm_parts.append(mm)
            if len(days):
                day_parts.append(days)
        mm = pd.concat(mm_parts, ignore_index=True) if mm_parts else pd.DataFrame()
        days = pd.concat(day_parts, ignore_index=True) if day_parts else pd.DataFrame()
        if len(mm):
            mm = (
                mm.groupby(["meter_customer_code", "month_start"], as_index=False)
                .agg(
                    tariff=("tariff", "first"),
                    kwh=("kwh", "sum"),
                    kwh_observed=("kwh_observed", "sum"),
                    kwh_imputed=("kwh_imputed", "sum"),
                    n_observed_slots=("n_observed_slots", "sum"),
                    n_days=("n_days", "max"),
                    n_days_observed=("n_days_observed", "max"),
                )
            )
        if len(days):
            days = days.groupby(["month_start", "local_date"], as_index=False).agg(
                has_observed=("has_observed", "max")
            )
        return mm, days


def _combine_meter_months(parts: list[pd.DataFrame]) -> pd.DataFrame:
    mm = pd.concat(parts, ignore_index=True)
    keys = ["meter_customer_code", "month_start"]
    if mm.duplicated(keys).any():
        mm = mm.groupby(keys, as_index=False).agg(
            tariff=("tariff", "first"),
            kwh=("kwh", "sum"),
            kwh_observed=("kwh_observed", "sum"),
            kwh_imputed=("kwh_imputed", "sum"),
            n_observed_slots=("n_observed_slots", "sum"),
            n_days=("n_days", "max"),
            n_days_observed=("n_days_observed", "max"),
        )
    return mm


def _site_months(mm: pd.DataFrame, days: pd.DataFrame, job: SiteJob, n_registry: int) -> pd.DataFrame:
    if mm.empty:
        return pd.DataFrame()
    mm = mm.copy()
    mm["month_start"] = pd.to_datetime(mm["month_start"]).dt.normalize()
    active = mm[mm.n_observed_slots >= 1].copy()
    if active.empty:
        return pd.DataFrame()
    active = active[(active.n_days >= 1) & (active.n_days_observed >= 1)]
    active["kwh_cust_month"] = (active.kwh / active.n_days) * DAYS_PER_MONTH
    active["kwh_cust_month_observed_only"] = (
        active.kwh_observed / active.n_days_observed
    ) * DAYS_PER_MONTH
    active["tariff_class"] = active.tariff.map(tariff_class)
    active["is_zero"] = active.kwh <= 0
    if days.empty:
        obs_map: dict[pd.Timestamp, int] = {}
    else:
        d = days.copy()
        d["month_start"] = pd.to_datetime(d["month_start"]).dt.normalize()
        obs_map = {
            pd.Timestamp(k): int(v)
            for k, v in (
                d.loc[d.has_observed.astype(bool)]
                .groupby("month_start")["local_date"]
                .nunique()
                .items()
            )
        }

    rows = []
    for month_start, g in active.groupby("month_start"):
        n_active = int(len(g))
        dc = int(obs_map.get(pd.Timestamp(month_start), 0))
        if n_active < MIN_ACTIVE or dc < MIN_DAYS:
            continue
        tot = float(g.kwh.sum())
        po = job.power_on
        ms = pd.Timestamp(month_start)
        months_since = (ms.year - po.year) * 12 + (ms.month - po.month)
        rows.append(
            {
                "site_id": site_id_of(job.project_name),
                "projectName": job.project_name,
                "country": job.country,
                "lat": job.lat,
                "lon": job.lon,
                "group": job.group,
                "role": job.role,
                "powerOnDate": po,
                "month": ms.normalize(),
                "months_since_power_on": int(months_since),
                "n_active": n_active,
                "n_registry_customer_meters": int(n_registry),
                "kwh_cust_month": float(g.kwh_cust_month.mean()),
                "kwh_cust_month_observed_only": float(g.kwh_cust_month_observed_only.mean()),
                "days_covered": dc,
                "share_imputed": float(g.kwh_imputed.sum() / tot) if tot else 0.0,
                "share_zero_meters": float(g.is_zero.mean()),
                "share_residential": float((g.tariff_class == "residential").mean()),
                "share_commercial": float((g.tariff_class == "commercial").mean()),
                "share_institution": float((g.tariff_class == "institution").mean()),
                "share_other": float((g.tariff_class == "other").mean()),
            }
        )
    return pd.DataFrame(rows)


def process_site(job: SiteJob) -> pd.DataFrame:
    if job.role == "test" and not final_eval_enabled():
        raise HeldOutError(f"refusing to process test site {job.project_name}")
    if not job.files:
        print(f"skip {job.project_name}: no sparkmeterreadings_clean file", flush=True)
        return pd.DataFrame()
    for p in job.files:
        ensure_readings_allowed(p)
        if not p.exists():
            print(f"skip {job.project_name}: missing {p.name}", flush=True)
            return pd.DataFrame()

    con = _connect()
    try:
        n_registry = _create_cust(con, job.project_name)
        print(
            f"{job.project_name}: {len(job.files)} file(s), {n_registry} customer meters, tz=+{job.tz_hours}",
            flush=True,
        )
        mm_parts, day_parts = [], []
        for p in job.files:
            print(f"  {p.name} ({p.stat().st_size / 1e6:.0f} MB)", flush=True)
            mm, days = _aggregate_file(con, p, job.tz_hours)
            print(f"    meter-months={len(mm)}  date-rows={len(days)}", flush=True)
            if len(mm):
                mm_parts.append(mm)
            if len(days):
                day_parts.append(days)
    finally:
        con.close()

    if not mm_parts:
        print(f"skip {job.project_name}: no customer-meter readings after join", flush=True)
        return pd.DataFrame()
    mm = _combine_meter_months(mm_parts)
    days = pd.concat(day_parts, ignore_index=True)
    days = days.groupby(["month_start", "local_date"], as_index=False).agg(
        has_observed=("has_observed", "max")
    )
    out = _site_months(mm, days, job, n_registry)
    print(f"  kept site-months={len(out)}", flush=True)
    return out


def _write_parquet(df: pd.DataFrame, path: pathlib.Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)


def build(refresh: bool = False, final_eval: bool | None = None) -> dict[str, pd.DataFrame]:
    """Aggregate TRAIN sites. Test sites are skipped unless PAWACAST_FINAL_EVAL=1."""
    if final_eval is None:
        final_eval = final_eval_enabled()
    TARGET_DIR.mkdir(parents=True, exist_ok=True)
    PART_DIR.mkdir(parents=True, exist_ok=True)

    split = load_split()
    sealed = split.loc[split.role == "test", "projectName"].tolist()
    if not final_eval:
        print("sealed (not opened): " + ", ".join(sealed), flush=True)
    else:
        print("PAWACAST_FINAL_EVAL=1: will also aggregate test sites", flush=True)

    train_parts, test_parts = [], []
    for job in iter_build_jobs(final_eval=final_eval):
        part_path = PART_DIR / f"{site_id_of(job.project_name)}.parquet"
        if part_path.exists() and not refresh:
            print(f"have {job.project_name}", flush=True)
            df = pd.read_parquet(part_path)
        else:
            df = process_site(job)
            if len(df):
                _write_parquet(df, part_path)
        if df.empty:
            continue
        if job.role == "test":
            test_parts.append(df)
        else:
            train_parts.append(df)

    result: dict[str, pd.DataFrame] = {}
    if train_parts:
        train = pd.concat(train_parts, ignore_index=True).sort_values(
            ["projectName", "month"]
        ).reset_index(drop=True)
        if (train.role == "test").any():
            raise HeldOutError("train output contained test-site rows")
        _write_parquet(train, TRAIN_PATH)
        print(f"wrote {TRAIN_PATH}  rows={len(train)}  sites={train.projectName.nunique()}", flush=True)
        result["train"] = train
    else:
        print("no train site-months produced", flush=True)
        result["train"] = pd.DataFrame()

    if final_eval:
        if test_parts:
            test = pd.concat(test_parts, ignore_index=True).sort_values(
                ["projectName", "month"]
            ).reset_index(drop=True)
            _write_parquet(test, TEST_PATH)
            print(f"wrote {TEST_PATH}  rows={len(test)}  sites={test.projectName.nunique()}", flush=True)
            result["test"] = test
        else:
            print("final eval on, but no test site-months produced", flush=True)
            result["test"] = pd.DataFrame()
    elif TEST_PATH.exists():
        print(f"note: {TEST_PATH.name} already on disk; not rewritten (flag off)", flush=True)

    return result


def load_site_months(*, role: str = "train") -> pd.DataFrame:
    """Load aggregated site-months. Test role raises unless PAWACAST_FINAL_EVAL=1."""
    if role not in ("train", "test"):
        raise ValueError(f"role must be 'train' or 'test', got {role!r}")
    if role == "test" and not final_eval_enabled():
        raise HeldOutError(
            "held-out Renewvia test sites are sealed; set PAWACAST_FINAL_EVAL=1 to load them"
        )
    path = TRAIN_PATH if role == "train" else TEST_PATH
    if not path.exists():
        raise FileNotFoundError(path)
    df = pd.read_parquet(path)
    if role == "train" and "role" in df.columns and (df.role == "test").any():
        raise HeldOutError("train parquet contains test-site rows")
    return df


def train_summary(df: pd.DataFrame | None = None) -> pd.DataFrame:
    if df is None:
        df = load_site_months(role="train")
    if df.empty:
        return df
    if (df.role == "test").any():
        raise HeldOutError("summary asked to include test sites")
    g = df.groupby("projectName", sort=True)
    out = pd.DataFrame(
        {
            "site": g.projectName.first(),
            "country": g.country.first(),
            "months": g.month.count(),
            "median_kwh_cust_month": g.kwh_cust_month.median(),
            "customers": g.n_active.median(),
            "median_share_imputed": g.share_imputed.median(),
            "median_days_covered": g.days_covered.median(),
        }
    ).reset_index(drop=True)
    return out


def feature_sites() -> pd.DataFrame:
    """All 24 Renewvia sites (coordinates only; no consumption)."""
    s = load_split()
    return pd.DataFrame(
        {
            "site_id": [site_id_of(n) for n in s.projectName],
            "name": s.projectName,
            "lat": s.lat,
            "lon": s.long,
            "country": s.country.map({"Kenya": "KE", "Nigeria": "NG"}),
            "group": s.group,
            "role": s.role,
        }
    )


def build_sprint_features(refresh: bool = False) -> dict[str, pd.DataFrame]:
    """Cached Overture/VIIRS/GridFinder features for 24 Renewvia sites and 3 demo sites."""
    from ..features import build_features
    from .demo import DEMO_SITES

    rv = feature_sites()
    print(f"features: {len(rv)} Renewvia sites", flush=True)
    f_rv = build_features(rv, name="renewvia", refresh=refresh)
    demo = DEMO_SITES.copy()
    print(f"features: {len(demo)} demo sites", flush=True)
    f_demo = build_features(demo, name="demo_sites", refresh=refresh)
    return {"renewvia": f_rv, "demo": f_demo}


def _print_summary(df: pd.DataFrame) -> None:
    pd.set_option("display.width", 220)
    pd.set_option("display.max_rows", 50)
    s = train_summary(df)
    print(s.to_string(index=False, float_format=lambda x: f"{x:8.3f}"))
    results = ROOT / "results"
    results.mkdir(exist_ok=True)
    out = results / "renewvia_train_summary.csv"
    s.to_csv(out, index=False, encoding="utf-8", lineterminator="\n")
    print(f"wrote {out}", flush=True)


def main(argv: list[str] | None = None) -> None:
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--refresh", action="store_true", help="recompute even if per-site parts exist")
    p.add_argument("--features", action="store_true", help="build cached site features")
    p.add_argument("--summary-only", action="store_true")
    args = p.parse_args(argv)
    if args.summary_only:
        _print_summary(load_site_months(role="train"))
        return
    if args.features:
        feats = build_sprint_features(refresh=args.refresh)
        for k, f in feats.items():
            print(k, list(f.columns), f"rows={len(f)}")
        return
    built = build(refresh=args.refresh)
    if len(built.get("train", pd.DataFrame())):
        _print_summary(built["train"])


if __name__ == "__main__":
    sys.exit(main())
