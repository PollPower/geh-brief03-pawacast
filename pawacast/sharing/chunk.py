"""Split a site-month of n customers into Compact-sized chunks.

N_MAX = 128. Sites with n > 128 become c = ceil(n/128) chunks of near-equal
size (sizes differ by at most 1). Never “full 128 plus a remainder”.

With n ≥ MIN_CUSTOMERS (25) overall, every chunk is ≥ 64, so K_MIN = 25 holds
per chunk.
"""
from __future__ import annotations

import math
from collections.abc import Sequence

N_MAX = 128
MIN_CHUNK = 25


def chunk_sizes(n: int, max_n: int = N_MAX) -> list[int]:
    """Near-equal chunk lengths that sum to n, each in [1, max_n] when n > 0."""
    if n < 0:
        raise ValueError("n must be >= 0")
    if n == 0:
        return []
    if n <= max_n:
        return [n]
    c = math.ceil(n / max_n)
    q, r = divmod(n, c)
    return [q + 1] * r + [q] * (c - r)


def split_into_chunks(values: Sequence, max_n: int = N_MAX) -> list[list]:
    """Partition `values` into near-equal chunks of length ≤ max_n."""
    n = len(values)
    sizes = chunk_sizes(n, max_n=max_n)
    out: list[list] = []
    i = 0
    for s in sizes:
        out.append(list(values[i : i + s]))
        i += s
    if i != n:
        raise RuntimeError("chunk split did not cover n")
    return out
