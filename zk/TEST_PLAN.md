# Compact circuit test plan (not run here — compile on Linux, see COMPILE.md)

Compiler: compactc **0.30.0** on Linux. Do not compile on Windows. Do not deploy.

```
compactc.bin zk/record.compact zk/build
```

## Cases

### 1. Valid n = 25 (must accept)

Public: `publishedN = 25`, `publishedSumMilliKwh = 125000`.

Witness: 25 × 5000 millikWh, then 7 zeros.

Fixture: `zk/fixtures/valid_n25.json`.

### 2. n = 24 (must reject)

k-anonymity floor is 25.

Fixture: `zk/fixtures/n24_should_fail.json`.

### 3. Count mismatch (must reject)

Public `publishedN = 25`, witness `privateN = 26`.

### 4. Sum mismatch (must reject)

Public sum 125000, witness twenty-five values that sum to 125001.

### 5. Dirty padding (must reject)

n = 25, first 25 slots sum correctly, slot 26 is 1 instead of 0.

### 6. n = 32 at the bound (must accept)

32 values, no padding. Sum matches.
