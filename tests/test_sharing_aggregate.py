"""Aggregation: k ≥ 25, rounding, Laplace clip 20, TRAIN-only (no test consumption)."""
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


def test_reject_n_below_25():
    kwh = np.array([3.0] * 10)
    biz = np.array([False] * 10)
    with pytest.raises(ValueError, match="n=10"):
        publish_from_customers(
            kwh, biz, lat=-1.87, lon=36.15, month="2022-06",
            months_since_power_on=12, site_id="renewvia_olkiramatian",
        )
    kwh24 = np.array([3.0] * 24)
    with pytest.raises(ValueError, match="n=24"):
        publish_from_customers(
            kwh24, np.zeros(24, dtype=bool), lat=-1.87, lon=36.15, month="2022-06",
            months_since_power_on=12, site_id="renewvia_olkiramatian",
        )


def test_publish_n_25_rounds_and_validates():
    rng = np.random.default_rng(0)
    kwh = rng.uniform(1.0, 12.0, size=25)
    biz = np.array([False] * 20 + [True] * 5)
    rec = publish_from_customers(
        kwh, biz, lat=-1.87170849, lon=36.150046876, month="2022-06",
        months_since_power_on=16, site_id="renewvia_olkiramatian",
    )
    validate_record(rec)
    assert rec["n_customers"] == 25
    assert rec["tier"] == 2
    assert rec["epsilon"] == 1.0
    assert rec["epsilon_period"] == "month"
    assert rec["yearly_epsilon_budget"] == 12.0
    assert rec["kwh_clip"] == 20.0
    assert rec["label"] == TIER2_RENEWVIA_LABEL
    assert rec["p10_kwh_cust"] <= rec["p50_kwh_cust"] <= rec["p90_kwh_cust"]


def test_n_27_rounds_to_25():
    kwh = np.linspace(1.0, 8.0, 27)
    biz = np.zeros(27, dtype=bool)
    rec = publish_from_customers(
        kwh, biz, lat=-1.87, lon=36.15, month="2021-01",
        months_since_power_on=4, site_id="renewvia_demo",
    )
    assert rec["n_customers"] == 25


def test_laplace_scale_clip_20():
    assert laplace_scale_mean(10) == pytest.approx(2.0)
    assert laplace_scale_mean(25) == pytest.approx(0.8)
    assert laplace_scale_mean(50) == pytest.approx(0.4)
    assert laplace_scale_mean(200) == pytest.approx(0.1)
    # n=10 is 40% of a typical 5 kWh mean → above the 30% bar, so we do not publish.
    assert laplace_scale_mean(10) / 5.0 == pytest.approx(0.4)
    assert laplace_scale_mean(25) / 5.0 == pytest.approx(0.16)


def test_noise_table_documents_epsilon_and_sizes():
    rows = noise_table()
    ns = [r["n_customers"] for r in rows]
    assert ns == [10, 25, 50, 200]
    assert rows[0]["epsilon"] == 1.0
    assert rows[0]["kwh_clip"] == 20.0
    assert rows[0]["typical_abs_noise_over_mean"] == pytest.approx(0.4)
    assert rows[1]["typical_abs_noise_over_mean"] == pytest.approx(0.16)


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
