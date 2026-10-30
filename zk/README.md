# Shared-record Compact circuit

Prove that a published PawaCast record's **sum** and **count** equal the sum and count of committed per-customer monthly kWh, and that **count ≥ 25**, **without disclosing any per-customer value, the exact count, or the blinding salt**. The proof reveals only the equality assertions (`publishedN`, `publishedSumMilliKwh`, `commitment` all match the witness).

This is the sprint slice of [SHARING_DESIGN.md](../SHARING_DESIGN.md) §2 / §6.3. **Not deployed.** Midnight Preview deploy needs an explicit ask.

## What is proven

| Public (circuit arg, pre-published) | Private (witness, never leaks) |
|---|---|
| `publishedN` — customer count | `privateN` — same count |
| `publishedSumMilliKwh` — sum of monthly kWh × 1000 | `privateValuesMilliKwh[128]` — per-customer millikWh, padded with zeros |
| `commitment` — 32-byte chained-hash binding | `privateSalt` — 32-byte blinding salt |

Assertions:

1. `privateN == publishedN`                       (N_MISMATCH)
2. `privateN >= 25` (k-anonymity)                 (N_BELOW_K_MIN)
3. `privateN <= 128` (circuit bound; larger sites chunk — see COMPILE.md §chunking) (N_ABOVE_N_MAX)
4. for the prefix `values[0..n)`: `sum(values[0..n)) == publishedSumMilliKwh`  (SUM_MISMATCH)
5. for every padding slot `values[n..128)`: `v == 0`  (PADDING_NONZERO)
6. `persistentHash(salt | n | values) == commitment` (chained; COMMITMENT_MISMATCH)

Assertion 6 binds the proof to a specific `(salt, n, values)` tuple. The operator publishes `commitment` alongside the EBT settlement entry for the same month — then anyone who later sees both the record and the proof can verify the proof corresponds to exactly the data that was committed, without ever seeing the per-customer values or the exact `n`.

## What is not proven

- P10 / P50 / P90 across customers (open question in SHARING_DESIGN.md).
- That the meters were honest (Tier 2 only proves consistency with the operator's commitment).
- Laplace noise: applied **after** this proof to the published mean. ε is in the JSON record.

## ZK-safety invariants

1. **No ledger scratch** carrying any witness-derived value. The only ledger field is `_version: Uint<8>`, written once as the constant `1` purely to force compactc 0.30.0 to classify this file as a proof-generating contract. No `disclose(witness)` anywhere.
2. **Commitment hiding.** The chained-hash commitment includes a 32-byte `privateSalt` witness, so a public attacker who sees `commitment` and the record (`publishedN`, `publishedSumMilliKwh`) cannot grind the per-customer values back out of the hash without knowing the salt.
3. **Fold accumulation.** Sum + padding check live in a single `fold` reducer over the 128-wide value vector; no `let mut`, no in-circuit mutable locals, no scratch ledger cells touched by the hot path.

See `COMPILE.md` §Design for the generated-code audit (`disclose` call-sites: zero; ledger fields: one marker; public transcript ops touching witnesses: zero).

## Toolchain status

Compiles with `compactc` 0.30.0 (language 0.22.0, runtime 0.15.0) — the build in `PollPower/contracts`. See `COMPILE.md` for the exact command, output layout, the offline fixture harness, and the N_MAX chunking policy. The circuit is **not** deployed to Midnight Preview; deploy needs an explicit ask.

`compact` on Windows `PATH` is `C:\Windows\system32\compact.exe` (NTFS file compression) and is NOT the Midnight compiler. The repo's `zk/check_toolchain.py` distinguishes them.

## Files

- `record.compact` — the circuit
- `COMPILE.md` — build command, output layout, k-anonymity floor, chunking policy, design audit
- `TEST_PLAN.md` — logical cases (fixture-mapped)
- `run-fixtures.mjs` — offline harness that invokes the compiled shim against each fixture
- `build-manifest.txt` — frozen sha256 listing of every `zk/build/` artifact
- `fixtures/valid_n25.json` — accept at k_min=25
- `fixtures/n24_should_fail.json` — reject at n=24 (one below k_min)
- `fixtures/wrong_commitment.json` — reject when public commitment doesn't match the witness
- `fixtures/nonzero_padding.json` — reject when a padding slot after n is nonzero
