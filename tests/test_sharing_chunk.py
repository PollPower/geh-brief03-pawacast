"""Near-equal Compact chunks: sizes in [25, 128], differ by ≤ 1, sum to n."""
from __future__ import annotations

import pytest

from pawacast.sharing.chunk import N_MAX, chunk_sizes, split_into_chunks
from pawacast.sharing.validate import MIN_CUSTOMERS


@pytest.mark.parametrize("n", [25, 128, 129, 130, 300, 1000])
def test_chunk_sizes_near_equal_and_in_bounds(n):
    sizes = chunk_sizes(n)
    assert sum(sizes) == n
    assert all(MIN_CUSTOMERS <= s <= N_MAX for s in sizes)
    assert max(sizes) - min(sizes) <= 1


def test_examples_from_compile_docs():
    assert chunk_sizes(130) == [65, 65]
    assert chunk_sizes(300) == [100, 100, 100]
    assert chunk_sizes(25) == [25]
    assert chunk_sizes(128) == [128]


def test_never_full_128_plus_remainder():
    # The wrong rule would be [128, 1] for n=129.
    assert chunk_sizes(129) == [65, 64]
    assert 1 not in chunk_sizes(129)


def test_split_into_chunks_covers_values():
    values = list(range(130))
    parts = split_into_chunks(values)
    assert [len(p) for p in parts] == [65, 65]
    assert [x for p in parts for x in p] == values
