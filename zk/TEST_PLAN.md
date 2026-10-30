# Compact circuit test plan

The circuit compiles with `compactc` 0.30.0 (language 0.22.0, runtime 0.15.0).
Build command, output layout, and the offline fixture harness are in
`zk/COMPILE.md`. Do not deploy the compiled artifact without an explicit ask.

```
compactc zk/record.compact zk/build/
```

> **k_min raised to 25.** The case descriptions below still use the old k=10
> wording (n=10 accepts, n=9 rejects); the live circuit uses k_min=25 so the
> "accept" boundary is n=25 and the "just-below" rejection is n=24. Fixtures
> `valid_n10.json` and `n9_should_fail.json` were updated to the new floor
> but keep their historical filenames. Treat case numbers below as logical
> intent (accept at k_min, reject just below) rather than literal n values.

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
