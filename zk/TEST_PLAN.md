# Compact circuit test plan

The circuit compiles with `compactc` 0.30.0 (language 0.22.0, runtime 0.15.0).
Build command, output layout, and the chunking policy for sites larger than
N_MAX are in `zk/COMPILE.md`. Do not deploy the compiled artifact without an
explicit ask.

```
compactc zk/record.compact zk/build/
```

Then exercise the circuit against every fixture via the offline harness:

```
# From repo root, with @midnight-ntwrk/compact-runtime 0.15.0 resolvable:
ln -sf ../../contracts/tariff-registry/node_modules zk/node_modules
cd zk && node run-fixtures.mjs
rm zk/node_modules
```

Expected: `[PASS]` on every row, exit 0.

## Cases (one fixture each)

Each fixture pins both the public inputs and the witness. The harness computes
the correct commitment for "accept" fixtures by replaying the circuit's
`persistentHash` chain in JS (`convertFieldToBytes` little-endian; see
`run-fixtures.mjs` for the exact encoding).

### 1. `valid_n25.json` — must accept

Public: `publishedN=25`, `publishedSumMilliKwh=125000`, `commitment=AUTO`
(harness computes).
Witness: `privateN=25`, 25 × 5000 + 103 zero-pad slots, `privateSalt=0xa1…a1`.

Expect: circuit returns `[]` (no revert). This is the k_min boundary — n is
exactly `K_MIN()`.

### 2. `n24_should_fail.json` — must reject with `N_BELOW_K_MIN`

Public: `publishedN=24`, `publishedSumMilliKwh=120000`, `commitment=AUTO`.
Witness: `privateN=24`, 24 × 5000 + 104 zero-pad slots.

Expect: `assert(n >= K_MIN(), "N_BELOW_K_MIN")` fires. The sum, padding, and
commitment checks never run (short-circuit on the first failed assert).

### 3. `wrong_commitment.json` — must reject with `COMMITMENT_MISMATCH`

Public: `publishedN=25`, `publishedSumMilliKwh=125000`,
`commitment=0xffff…ffff` (32 bytes of 0xff, not the real chain hash).
Witness: valid n=25, 25 × 5000 + 103 zeros, `privateSalt=0xc3…c3`.

Expect: the sum fold and padding check pass; the chained-hash fold produces
`H ≠ 0xff…ff`; the final `assert(hFinal == commitment, "COMMITMENT_MISMATCH")`
fires. Guards against a prover trying to attach a stale/forged commitment.

### 4. `nonzero_padding.json` — must reject with `PADDING_NONZERO`

Public: `publishedN=25`, `publishedSumMilliKwh=125000`, `commitment=AUTO`.
Witness: `privateN=25`, 25 × 5000 followed by slot[25]=7 then 102 zeros.

Expect: the sum fold enters the padding branch at index 25 (`remaining ==
0`) and asserts `v == 0`; v is 7, so `PADDING_NONZERO` fires. Guards against
a prover sneaking extra value into a padded slot to inflate the hidden
distribution without affecting the sum (which still matches because the
reducer only sums the first `n` slots).

## After compile

The current pass/fail status is recorded in `run-fixtures.mjs` output and in
`build-manifest.txt` (per-artifact sha256 so repeat runs are byte-identical).
Do not deploy.

## Cases NOT YET fixtured

These used to live in the Compact 0.18 plan; keeping them here as a
follow-up to-do list, not as current fixtures:

- Count mismatch (`publishedN=25`, witness `privateN=27`) — would fire
  `N_MISMATCH`.
- Sum mismatch (correct n and padding, witness sums to 125001 but public
  claims 125000) — would fire `SUM_MISMATCH`.
- `n = N_MAX = 128` with 128 real values and no padding — accept case at
  the upper bound.

Add these as fixtures when the chunking / aggregator plumbing lands.
