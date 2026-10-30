# Shared-record Compact circuit

The proof shows the operator's exact site-month total and customer count match
readings it committed to earlier, without revealing any customer's values.
Privacy noise is added after the proof, to the public release only. The
published (noised) figure is not itself proven.

This is the sprint slice of [SHARING_DESIGN.md](../SHARING_DESIGN.md) §2 / §6.3.

Circuit compiles with compactc 0.30.0 (N_MAX 128, proving key 306 MB).
Circuit logic tested on 4 fixtures (valid; too few customers; wrong
commitment; non-zero padding). Not deployed; no on-chain proofs generated
during the sprint.

Compile on Linux — see [COMPILE.md](COMPILE.md). Do not compile on Windows.
`compact` on Windows `PATH` is NTFS compression, not Midnight Compact.
`zk/check_toolchain.py` distinguishes them.

## What is proven

| Public (revealed) | Private (witness) |
|---|---|
| `publishedN` — customer count | `privateN` — same count |
| `publishedSumMilliKwh` — exact sum of monthly kWh × 1000 (before noise) | `privateValuesMilliKwh[128]` — per-customer millikWh, padded with zeros |
| `commitment` — 32-byte commitment the operator published earlier | `privateCommitment` — same 32 bytes |

Assertions:

1. `privateN == publishedN`
2. `privateN >= 25` (k-anonymity; `MIN_CUSTOMERS` in `validate.py`)
3. `privateN <= 128` (sites larger than this split into near-equal chunks)
4. `privateCommitment == commitment`
5. `sum(values[0..n)) == publishedSumMilliKwh`
6. padding slots `values[n..128)` are 0

## What is not proven

- P10 / P50 / P90 across customers (open question in SHARING_DESIGN.md).
- That the meters were honest (Tier 2 only proves consistency with the operator’s commitment).
- The published (Laplace-noised) mean. Noise is applied **after** this proof.

## Vector width

Sites with n > 128 split into c = ceil(n/128) chunks of near-equal size
(sizes differ by at most 1; e.g. 130 → 65+65, 300 → 100+100+100). Never
“full 128 plus remainder”. With n ≥ 25 overall every chunk has ≥ 64
customers, so K_MIN = 25 holds per chunk. See `pawacast/sharing/chunk.py`.

## Files

- `record.compact` — the circuit
- `TEST_PLAN.md` — the 4 fixtures
- `run-fixtures.mjs` — offline assert/revert harness (needs compact-runtime)
- `fixtures/valid_n25.json`, `n24_should_fail.json`, `wrong_commitment.json`, `dirty_padding.json`
