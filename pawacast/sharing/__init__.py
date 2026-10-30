"""Meter-data sharing: public records, k-anonymity, ingest into the prior.

Day-one frozen coefficients are never refit from shared records.
"""
from .chunk import N_MAX, chunk_sizes, split_into_chunks
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
    "N_MAX",
    "RecordError",
    "chunk_sizes",
    "h3_res6",
    "round_business_share",
    "round_n_customers",
    "split_into_chunks",
    "validate_record",
    "validate_records",
]
