"""Held-out Renewvia consumption must stay sealed unless PAWACAST_FINAL_EVAL=1."""
from __future__ import annotations

import pathlib

import pytest

from pawacast.targets.renewvia import (
    TEST_SITES,
    HeldOutError,
    ensure_readings_allowed,
    iter_build_jobs,
    load_site_months,
    readings_path_is_sealed,
    tariff_class,
)


def test_load_test_raises_without_flag(monkeypatch):
    monkeypatch.delenv("PAWACAST_FINAL_EVAL", raising=False)
    with pytest.raises(HeldOutError, match="sealed"):
        load_site_months(role="test")


def test_load_test_not_heldout_error_with_flag(monkeypatch):
    monkeypatch.setenv("PAWACAST_FINAL_EVAL", "1")
    try:
        load_site_months(role="test")
    except HeldOutError:
        pytest.fail("PAWACAST_FINAL_EVAL=1 must allow loading test site-months")
    except FileNotFoundError:
        pass


def test_ensure_readings_allowed_blocks_test_files(monkeypatch, tmp_path):
    monkeypatch.delenv("PAWACAST_FINAL_EVAL", raising=False)
    for stem in ("Balep", "Bendeghe-Afi", "Opu", "Ozuzu", "Kapelbok"):
        p = tmp_path / f"sparkmeterreadings_clean_{stem}.parquet"
        assert readings_path_is_sealed(p)
        with pytest.raises(HeldOutError):
            ensure_readings_allowed(p)


def test_ensure_readings_allowed_permits_train_filename(monkeypatch, tmp_path):
    monkeypatch.delenv("PAWACAST_FINAL_EVAL", raising=False)
    p = tmp_path / "sparkmeterreadings_clean_Lomekwi.parquet"
    assert not readings_path_is_sealed(p)
    ensure_readings_allowed(p)


def test_iter_build_jobs_skips_test_sites_without_flag(monkeypatch):
    monkeypatch.delenv("PAWACAST_FINAL_EVAL", raising=False)
    jobs = iter_build_jobs(final_eval=False)
    names = {j.project_name for j in jobs}
    assert names.isdisjoint(TEST_SITES)
    assert all(j.role == "train" for j in jobs)
    for j in jobs:
        for p in j.files:
            assert not readings_path_is_sealed(pathlib.Path(p))


def test_iter_build_jobs_lists_test_sites_only_when_final(monkeypatch):
    monkeypatch.delenv("PAWACAST_FINAL_EVAL", raising=False)
    off = {j.project_name for j in iter_build_jobs(final_eval=False)}
    on = {j.project_name for j in iter_build_jobs(final_eval=True)}
    assert TEST_SITES.isdisjoint(off)
    assert TEST_SITES <= on


def test_tariff_class_mapping():
    assert tariff_class("Residential") == "residential"
    assert tariff_class("Tariff A") == "residential"
    assert tariff_class("Commercial") == "commercial"
    assert tariff_class("Religious Institution") == "institution"
    assert tariff_class("Spoke-Energy Package (Kwh)") == "other"
    assert tariff_class(None) == "other"
