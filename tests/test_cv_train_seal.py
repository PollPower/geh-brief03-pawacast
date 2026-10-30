"""Block 2 must never score or fit on sealed Renewvia test sites."""
from pawacast.model.loglinear import imputation_check, load_train_sites
from pawacast.targets.renewvia import TEST_SITES, HeldOutError, load_site_months


def test_train_load_excludes_test_sites():
    sm = load_site_months(role="train")
    assert set(sm.projectName).isdisjoint(TEST_SITES)
    assert not (sm.role == "test").any()


def test_site_level_excludes_test_sites():
    sites, sm, check, switched = load_train_sites()
    assert set(sites.projectName).isdisjoint(TEST_SITES)
    assert set(sm.projectName).isdisjoint(TEST_SITES)
    assert set(TEST_SITES).isdisjoint(set(switched))


def test_imputation_does_not_switch_after_conservation_decision():
    sites, sm, check, switched = load_train_sites()
    assert switched == []
    assert not check.use_observed_only.any()
    em = check.loc[check.projectName == "Emereoke"].iloc[0]
    ks = check.loc[check.projectName == "Kalobeyei Settlement"].iloc[0]
    assert em.median_abs_rel > 0.15 and ks.median_abs_rel > 0.15
    # training target is gap-filled for every site
    assert (sm.kwh_used == sm.kwh_cust_month).all()


def test_load_test_still_sealed(monkeypatch):
    monkeypatch.delenv("PAWACAST_FINAL_EVAL", raising=False)
    try:
        load_site_months(role="test")
    except HeldOutError:
        return
    except FileNotFoundError:
        raise AssertionError("test load must raise HeldOutError before missing-file")
    raise AssertionError("test load must raise")
