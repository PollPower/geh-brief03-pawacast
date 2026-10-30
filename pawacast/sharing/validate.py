"""Validate PawaCast shared meter-data records.

k-anonymity: n_customers must be >= 10 (true count, and published count after
rounding to the nearest 5). Exact coordinates, meter IDs and per-customer kWh
are not in the schema and are rejected if present.
"""
from __future__ import annotations

import json
import math
import pathlib
from typing import Any

import h3

SCHEMA_PATH = pathlib.Path(__file__).resolve().parent / "schema.json"

H3_RES = 6
MIN_CUSTOMERS = 10
N_ROUND = 5
SHARE_ROUND = 0.1
KWH_MAX = 500.0
REQUIRED = (
    "h3_res6",
    "month",
    "months_since_power_on",
    "n_customers",
    "mean_kwh_cust",
    "p10_kwh_cust",
    "p50_kwh_cust",
    "p90_kwh_cust",
    "business_share",
    "tier",
    "proof_ref",
    "epsilon",
)
FORBIDDEN = (
    "lat",
    "lon",
    "latitude",
    "longitude",
    "meter_id",
    "customer_id",
    "kwh_by_customer",
    "readings",
    "site_name",
    "project_name",
)


class RecordError(ValueError):
    """Shared record failed schema or k-anonymity checks."""


def load_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def round_n_customers(n: int) -> int:
    """Nearest 5, half-up. True n < 10 is still rejected before publish."""
    if n < 0:
        raise RecordError("n_customers must be >= 0")
    return int(N_ROUND * math.floor(n / N_ROUND + 0.5))


def round_business_share(share: float) -> float:
    s = max(0.0, min(1.0, float(share)))
    tenths = int(math.floor(s / SHARE_ROUND + 0.5))
    return round(min(1.0, tenths * SHARE_ROUND), 1)


def h3_res6(lat: float, lon: float) -> str:
    cell = h3.latlng_to_cell(float(lat), float(lon), H3_RES)
    if h3.get_resolution(cell) != H3_RES:
        raise RecordError(f"expected H3 resolution {H3_RES}, got {cell}")
    return cell


def _num(record: dict, key: str) -> float:
    v = record[key]
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise RecordError(f"{key} must be a number")
    return float(v)


def _int(record: dict, key: str) -> int:
    v = record[key]
    if isinstance(v, bool) or not isinstance(v, int):
        raise RecordError(f"{key} must be an integer")
    return int(v)


def validate_record(record: Any) -> dict:
    """Return a copy of a valid record. Raise RecordError otherwise."""
    if not isinstance(record, dict):
        raise RecordError("record must be a JSON object")
    missing = [k for k in REQUIRED if k not in record]
    if missing:
        raise RecordError("missing fields: " + ", ".join(missing))
    leaked = [k for k in FORBIDDEN if k in record]
    if leaked:
        raise RecordError("forbidden fields (never share): " + ", ".join(leaked))
    extra = [k for k in record if k not in REQUIRED and k != "label"]
    if extra:
        raise RecordError("unknown fields: " + ", ".join(sorted(extra)))

    cell = record["h3_res6"]
    if not isinstance(cell, str) or not h3.is_valid_cell(cell):
        raise RecordError("h3_res6 is not a valid H3 cell")
    if h3.get_resolution(cell) != H3_RES:
        raise RecordError(f"h3_res6 must be resolution {H3_RES}")

    month = record["month"]
    if not isinstance(month, str) or len(month) != 7 or month[4] != "-":
        raise RecordError("month must be YYYY-MM")
    try:
        y, m = int(month[:4]), int(month[5:7])
    except ValueError as e:
        raise RecordError("month must be YYYY-MM") from e
    if not (1 <= m <= 12) or y < 2000 or y > 2100:
        raise RecordError("month out of range")

    age = _int(record, "months_since_power_on")
    if age < 0 or age > 360:
        raise RecordError("months_since_power_on out of range")

    n = _int(record, "n_customers")
    if n < MIN_CUSTOMERS:
        raise RecordError(f"n_customers {n} < {MIN_CUSTOMERS} (k-anonymity)")
    if n % N_ROUND != 0:
        raise RecordError(f"n_customers {n} is not a multiple of {N_ROUND}")

    mean = _num(record, "mean_kwh_cust")
    p10 = _num(record, "p10_kwh_cust")
    p50 = _num(record, "p50_kwh_cust")
    p90 = _num(record, "p90_kwh_cust")
    for name, v in (
        ("mean_kwh_cust", mean),
        ("p10_kwh_cust", p10),
        ("p50_kwh_cust", p50),
        ("p90_kwh_cust", p90),
    ):
        if v < 0 or v > KWH_MAX:
            raise RecordError(f"{name} out of range")
    if not (p10 <= p50 <= p90):
        raise RecordError("need p10_kwh_cust <= p50_kwh_cust <= p90_kwh_cust")

    share = _num(record, "business_share")
    if share < 0 or share > 1:
        raise RecordError("business_share must be in [0, 1]")
    rounded_share = round_business_share(share)
    if abs(share - rounded_share) > 1e-9:
        raise RecordError("business_share must be a multiple of 0.1")

    tier = _int(record, "tier")
    if tier not in (1, 2):
        raise RecordError("tier must be 1 (PollPower-metered) or 2 (other operator)")

    proof = record["proof_ref"]
    if not isinstance(proof, str) or not proof.strip() or len(proof) > 256:
        raise RecordError("proof_ref must be a non-empty string")

    eps = _num(record, "epsilon")
    if eps <= 0 or eps > 10:
        raise RecordError("epsilon must be in (0, 10]")

    if "label" in record and not isinstance(record["label"], str):
        raise RecordError("label must be a string")

    return dict(record)


def validate_records(records: list[Any]) -> list[dict]:
    out = []
    for i, rec in enumerate(records):
        try:
            out.append(validate_record(rec))
        except RecordError as e:
            raise RecordError(f"record {i}: {e}") from e
    return out
