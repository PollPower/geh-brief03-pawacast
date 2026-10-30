# Compact circuit test plan

The circuit compiles with `compactc` 0.30.0 (language 0.22.0, runtime 0.15.0,
N_MAX 128, proving key 306 MB). Build command, output layout, and the offline
fixture harness are in `zk/COMPILE.md`. Do not compile on Windows. Do not
deploy. No on-chain proofs generated during the sprint.

```
compactc zk/record.compact zk/build/
```

k-min is **25**, matching `pawacast/sharing/validate.py` `MIN_CUSTOMERS`.
Vector width is **128**; larger sites split into near-equal chunks (COMPILE.md
§Vector width).

Circuit logic is tested on **4 fixtures**:

## Cases

### 1. Valid n = 25 (must accept)

Public: `publishedN = 25`, `publishedSumMilliKwh = 125000`, commitment =
SHA-256 of those 25 millikWh values.

Witness: 25 × 5000 millikWh, then 103 zeros; `privateCommitment` equals the
public commitment.

Fixture: `zk/fixtures/valid_n25.json`.

### 2. Too few customers — n = 24 (must reject)

k-anonymity floor is 25. Expect `N_BELOW_K_MIN`.

Fixture: `zk/fixtures/n24_should_fail.json`.

### 3. Wrong commitment (must reject)

Valid n = 25 and matching sum, but public `commitment` ≠ `privateCommitment`.
Expect `COMMIT_MISMATCH`.

Fixture: `zk/fixtures/wrong_commitment.json`.

### 4. Non-zero padding (must reject)

n = 25, first 25 slots sum correctly, slot 26 is 1 instead of 0.
Expect `PADDING_NONZERO`.

Fixture: `zk/fixtures/dirty_padding.json`.

## What the proof does not claim

The proof shows the operator's exact site-month total and customer count match
readings it committed to earlier, without revealing any customer's values.
Privacy noise is added after the proof, to the public release only. The
published (noised) figure is not itself proven.

## After compile

Record compiler version, language version, proving-key size, and pass/fail of
the 4 fixtures in `results/` (do not fabricate). Still do not deploy.
