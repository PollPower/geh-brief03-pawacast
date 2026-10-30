# Compact circuit test plan (not run — compiler missing)

Install the Midnight Compact toolchain (`compactc`, matching `pragma language_version` in `record.compact`). Then:

```
compactc compile zk/record.compact
```

If the pragma is rejected, bump it to the installed language version. Do not deploy the compiled artifact.

## Cases

### 1. Valid n = 10 (must accept)

Public: `publishedN = 10`, `publishedSumMilliKwh = 50000` (50 kWh total → 5 kWh mean).

Witness: `privateN = 10`, `privateValuesMilliKwh = [5000, 5000, …, 5000]` (10 entries) then 22 zeros.

Expect: circuit returns true.

Fixture: `zk/fixtures/valid_n10.json`.

### 2. n = 9 (must reject)

Public: `publishedN = 9`, sum any.

Witness: 9 values + padding.

Expect: assert `n >= K_MIN` fails.

Fixture: `zk/fixtures/n9_should_fail.json`.

### 3. Count mismatch (must reject)

Public `publishedN = 10`, witness `privateN = 12`.

Expect: `n == publishedN` fails.

### 4. Sum mismatch (must reject)

Public sum 50000, witness ten values that sum to 50001.

Expect: `acc == publishedSumMilliKwh` fails.

### 5. Dirty padding (must reject)

n = 10, first 10 slots sum correctly, slot 11 is 1 instead of 0.

Expect: `v == 0` on padding fails.

### 6. n = 32 at the bound (must accept)

32 values, no padding. Sum matches.

## After compile

Record compiler version, language version, and pass/fail of cases 1–6 in `results/` (do not fabricate). Still do not deploy.
