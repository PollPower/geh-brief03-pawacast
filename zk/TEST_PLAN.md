# Compact circuit test plan

The circuit compiles with `compactc` 0.30.0 (language 0.22.0, runtime 0.15.0,
N_MAX 128, proving key 306 MB). Build command, output layout, and the
near-equal chunking policy for sites larger than N_MAX are in `zk/COMPILE.md`.
Do not compile on Windows. Do not deploy. No on-chain proofs generated during
the sprint.

```
compactc zk/record.compact zk/build/
```

Then exercise the circuit against every fixture via the offline harness:

```
ln -sf ../../contracts/tariff-registry/node_modules zk/node_modules
cd zk && node run-fixtures.mjs
rm zk/node_modules
```

k-min is **25**, matching `pawacast/sharing/validate.py` `MIN_CUSTOMERS`.
Vector width is **128**; larger sites split into near-equal chunks
(COMPILE.md §Vector width).

Circuit logic is tested on **4 fixtures**:

## Cases (one fixture each)

Each fixture pins both the public inputs and the witness. The harness computes
the correct commitment for "accept" fixtures by replaying the circuit's
`persistentHash` chain in JS (`convertFieldToBytes` little-endian; see
`run-fixtures.mjs`).

### 1. `valid_n25.json` — must accept

Public: `publishedN=25`, `publishedSumMilliKwh=125000`, `commitment=AUTO`
(harness computes).
Witness: `privateN=25`, 25 × 5000 + 103 zero-pad slots, `privateSalt=0xa1…a1`.

Expect: circuit returns `[]` (no revert). This is the k_min boundary — n is
exactly `K_MIN()`.

### 2. `n24_should_fail.json` — must reject with `N_BELOW_K_MIN`

Public: `publishedN=24`, `publishedSumMilliKwh=120000`, `commitment=AUTO`.
Witness: `privateN=24`, 24 × 5000 + 104 zero-pad slots.

Expect: `assert(n >= K_MIN(), "N_BELOW_K_MIN")` fires.

### 3. `wrong_commitment.json` — must reject with `COMMITMENT_MISMATCH`

Public: `publishedN=25`, `publishedSumMilliKwh=125000`,
`commitment=0xffff…ffff` (32 bytes of 0xff, not the real chain hash).
Witness: valid n=25, 25 × 5000 + 103 zeros, `privateSalt=0xc3…c3`.

Expect: the sum fold and padding check pass; the chained-hash fold produces
`H ≠ 0xff…ff`; the final `assert(hFinal == commitment, "COMMITMENT_MISMATCH")`
fires.

### 4. `nonzero_padding.json` — must reject with `PADDING_NONZERO`

Public: `publishedN=25`, `publishedSumMilliKwh=125000`, `commitment=AUTO`.
Witness: `privateN=25`, 25 × 5000 followed by slot[25]=7 then 102 zeros.

Expect: the sum fold enters the padding branch at index 25 (`remaining ==
0`) and asserts `v == 0`; v is 7, so `PADDING_NONZERO` fires.

## What the proof does not claim

The proof shows the operator's exact site-month total and customer count match
readings it committed to earlier, without revealing any customer's values.
Privacy noise is added after the proof, to the public release only. The
published (noised) figure is not itself proven.

## After compile

Record compiler version, language version, proving-key size, and pass/fail of
the 4 fixtures. Still do not deploy. The only ledger field is `_version`
(constant 1); there are no `_proofSum` / `_proofIdx` cells.
