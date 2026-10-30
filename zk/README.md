# Shared-record Compact circuit

Prove that a published PawaCast record’s **sum** and **count** equal the sum and count of committed per-customer monthly kWh, and that **count ≥ 10**. The proof reveals those two numbers and nothing else (no meter IDs, no per-customer values, no exact coordinates).

This is the sprint slice of [SHARING_DESIGN.md](../SHARING_DESIGN.md) §2 / §6.3. **Not deployed.** Midnight Preview deploy needs an explicit ask. Compile on Linux with compactc 0.30.0 — see [COMPILE.md](COMPILE.md). Do not compile on Windows.

## What is proven

| Public (revealed) | Private (witness) |
|---|---|
| `publishedN` — customer count | `privateN` — same count |
| `publishedSumMilliKwh` — sum of monthly kWh × 1000 | `privateValuesMilliKwh[32]` — per-customer millikWh, padded with zeros |

Assertions:

1. `privateN == publishedN`
2. `privateN >= 10` (k-anonymity)
3. `privateN <= 32` (circuit bound; larger sites chunk or raise N_MAX)
4. `sum(values[0..n)) == publishedSumMilliKwh`
5. padding slots `values[n..32)` are 0

## What is not proven

- P10 / P50 / P90 across customers (open question in SHARING_DESIGN.md).
- That the meters were honest (Tier 2 only proves consistency with the operator’s commitment).
- Laplace noise: applied **after** this proof to the published mean. ε is in the JSON record.

## Toolchain status (this machine)

`compact` on PATH is Windows `C:\Windows\system32\compact.exe` (NTFS file compression), **not** Midnight Compact. `compactc` was not found. The circuit in `record.compact` was **not compiled** here. See `TEST_PLAN.md` for the cases to run once `compactc` is installed.

## Files

- `record.compact` — the circuit
- `TEST_PLAN.md` — local compile + test cases
- `fixtures/valid_n10.json` / `fixtures/n9_should_fail.json` — example public/private inputs
