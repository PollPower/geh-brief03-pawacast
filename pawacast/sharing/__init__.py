"""Meter-data sharing: public records, k-anonymity, ingest into the prior.

Day-one frozen coefficients are never refit from shared records.
"""
from .validate import (
    MIN_CUSTOMERS,
    RecordError,
    h3_res6,
    round_business_share,
    round_n_customers,
    validate_record,
    validate_records,
)

__all__ = [
    "MIN_CUSTOMERS",
    "RecordError",
    "h3_res6",
    "round_business_share",
    "round_n_customers",
    "validate_record",
    "validate_records",
]
