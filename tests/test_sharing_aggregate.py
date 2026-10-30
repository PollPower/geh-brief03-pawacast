"""Aggregation: k ≥ 10, rounding, Laplace, TRAIN-only (no test consumption)."""
from __future__ import annotations

from datetime import datetime

import numpy as np
import pandas as pd
import pytest

from pawacast.sharing.aggregate import (
    TIER2_RENEWVIA_LABEL,
    laplace_scale_mean,
    noise_table,
    publish_from_customers,
    records_from_job,
)
from pawacast.sharing.validate import validate_record
from pawacast.targets.renewvia import HeldOutError, SiteJob, TEST_SITES


def test_reject_n_below_10():
    kwh = np.array([3.0] * 9)
    biz = np.array([False] * 9)
    with pytest.raises(ValueError, match="n=9"):
        publish_from_customers(
            kwh, biz, lat=-1.87, lon=36.15, month="2022-06",
            months_since_power_on=12, site_id="renewvia_olkiramatian",
        )


def test_publish_n_10_rounds_and_validates():
    rng = np.random.default_rng(0)
    kwh = rng.uniform(1.0, 12.0, size=10)
    biz = np.array([False] * 8 + [True] * 2)
    rec = publish_from_customers(
        kwh, biz, lat=-1.87170849, lon=36.150046876, month="2022-06",
        months_since_power_on=16, site_id="renewvia_olkiramatian",
    )
    validate_record(rec)
    assert rec["n_customers"] == 10
    assert rec["tier"] == 2
    assert rec["epsilon"] == 1.0
    assert rec["label"] == TIER2_RENEWVIA_LABEL
    assert rec["p10_kwh_cust"] <= rec["p50_kwh_cust"] <= rec["p90_kwh_cust"]


def test_n_12_rounds_to_10():
    kwh = np.linspace(1.0, 8.0, 12)
    biz = np.zeros(12, dtype=bool)
    rec = publish_from_customers(
        kwh, biz, lat=-1.87, lon=36.15, month="2021-01",
        months_since_power_on=4, site_id="renewvia_demo",
    )
    assert rec["n_customers"] == 10


def test_laplace_scale_falls_with_n():
    s10 = laplace_scale_mean(10)
    s100 = laplace_scale_mean(100)
    s2000 = laplace_scale_mean(2000)
    assert s10 == pytest.approx(5.0)
    assert s100 == pytest.approx(0.5)
    assert s2000 == pytest.approx(0.025)
    assert s10 > s100 > s2000


def test_noise_table_documents_epsilon():
    rows = noise_table()
    assert rows[0]["n_customers"] == 10
    assert rows[0]["epsilon"] == 1.0
    assert rows[-1]["n_customers"] == 2000
    assert rows[-1]["typical_abs_noise_over_mean"] < rows[0]["typical_abs_noise_over_mean"]


def test_records_from_job_refuses_test_sites():
    job = SiteJob(
        project_name="Balep",
        country="Nigeria",
        lat=6.0,
        lon=8.0,
        power_on=pd.Timestamp(datetime(2020, 1, 1)),
        group="test",
        role="test",
        tz_hours=1,
        files=[],
    )
    assert job.project_name.split()[0] in TEST_SITES or "Balep" in TEST_SITES
    with pytest.raises(HeldOutError, match="test"):
        records_from_job(job)
