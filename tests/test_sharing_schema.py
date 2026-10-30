"""Shared-record schema: k-anonymity, rounding, H3 res-6, no PII fields."""
from __future__ import annotations

import copy

import pytest

from pawacast.sharing.validate import (
    RecordError,
    h3_res6,
    round_business_share,
    round_n_customers,
    validate_record,
)


def _ok(**kwargs):
    rec = {
        "h3_res6": h3_res6(-1.33866, 35.71253),
        "month": "2022-06",
        "months_since_power_on": 16,
        "n_customers": 65,
        "mean_kwh_cust": 5.4,
        "p10_kwh_cust": 1.2,
        "p50_kwh_cust": 4.1,
        "p90_kwh_cust": 12.3,
        "business_share": 0.2,
        "tier": 2,
        "proof_ref": "demo:train:example:2022-06",
        "epsilon": 1.0,
        "label": "Tier 2 demo built from Renewvia open data (CC BY-SA 4.0)",
    }
    rec.update(kwargs)
    return rec


def test_valid_record_passes():
    out = validate_record(_ok())
    assert out["n_customers"] == 65
    assert out["tier"] == 2


def test_reject_n_below_10():
    with pytest.raises(RecordError, match="k-anonymity"):
        validate_record(_ok(n_customers=9))
    with pytest.raises(RecordError, match="k-anonymity"):
        validate_record(_ok(n_customers=5))
    with pytest.raises(RecordError, match="k-anonymity"):
        validate_record(_ok(n_customers=0))


def test_reject_n_not_multiple_of_5():
    with pytest.raises(RecordError, match="multiple of 5"):
        validate_record(_ok(n_customers=11))
    with pytest.raises(RecordError, match="multiple of 5"):
        validate_record(_ok(n_customers=12))


def test_round_n_customers():
    assert round_n_customers(10) == 10
    assert round_n_customers(12) == 10
    assert round_n_customers(13) == 15
    assert round_n_customers(52) == 50
    assert round_n_customers(9) == 10  # rounding only; validator still rejects true n < 10


def test_round_business_share():
    assert round_business_share(0.0) == 0.0
    assert round_business_share(0.04) == 0.0
    assert round_business_share(0.05) == 0.1
    assert round_business_share(0.24) == 0.2
    assert round_business_share(1.0) == 1.0


def test_reject_unrounded_business_share():
    with pytest.raises(RecordError, match="0.1"):
        validate_record(_ok(business_share=0.25))


def test_reject_percentile_order():
    with pytest.raises(RecordError, match="p10"):
        validate_record(_ok(p10_kwh_cust=8.0, p50_kwh_cust=4.0, p90_kwh_cust=12.0))


def test_reject_bad_tier():
    with pytest.raises(RecordError, match="tier"):
        validate_record(_ok(tier=3))
    with pytest.raises(RecordError, match="tier"):
        validate_record(_ok(tier=0))


def test_reject_coordinates_and_meter_ids():
    rec = _ok()
    rec["lat"] = -1.33
    rec["lon"] = 35.71
    with pytest.raises(RecordError, match="forbidden"):
        validate_record(rec)
    rec = _ok()
    rec["meter_id"] = "abc"
    with pytest.raises(RecordError, match="forbidden"):
        validate_record(rec)


def test_h3_res6_is_resolution_six():
    import h3

    cell = h3_res6(-1.87170849, 36.150046876)
    assert h3.get_resolution(cell) == 6
    rec = _ok(h3_res6=cell)
    validate_record(rec)


def test_reject_wrong_h3_resolution():
    import h3

    cell7 = h3.latlng_to_cell(-1.33866, 35.71253, 7)
    with pytest.raises(RecordError, match="resolution"):
        validate_record(_ok(h3_res6=cell7))


def test_reject_missing_field():
    rec = _ok()
    del rec["proof_ref"]
    with pytest.raises(RecordError, match="missing"):
        validate_record(rec)


def test_copy_does_not_mutate():
    rec = _ok()
    original = copy.deepcopy(rec)
    validate_record(rec)
    assert rec == original
