# Compiling `zk/record.compact`

Target toolchain: Midnight **Compact 0.22** (`compactc 0.30.0`, language 0.22.0,
runtime 0.15.0, ledger 4.0.2). Same compactc build used by
`PollPower/contracts` (EBT v8 + tariff-registry).

Circuit compiles with compactc 0.30.0 (N_MAX 128, proving key 306 MB).
Circuit logic tested on 4 fixtures (valid; too few customers; wrong
commitment; non-zero padding). Not deployed; no on-chain proofs generated
during the sprint.

Do **not** compile this on Windows. `compact` on a Windows PATH is NTFS
compression (`C:\Windows\system32\compact.exe`), not Midnight Compact.
Do **not** deploy the compiled artifact to Midnight Preview without an explicit ask.

On kenya the binary lives at:

```
/home/pollpower/.compact/versions/0.30.0/x86_64-unknown-linux-musl/compactc
```

(`compactc.bin` is the same compiler; deploy scripts on kenya call `compactc.bin`.)

## Exact command

Run from the repo root. `compactc` must be the 0.30.0 build on your `PATH`
(or substitute the absolute path).

```
mkdir -p zk/build
compactc zk/record.compact zk/build/
```

Same invocation the contracts repo uses in `tariff-registry/deploy-preview.sh`:

```bash
compactc.bin "$CONTRACT_SRC" "$BUILD_DIR"
```

Expected: wall time on the order of seconds for N_MAX 32 and much longer for
N_MAX 128; no stderr beyond `Compiling 1 circuits:`. Build artifacts land
under `zk/build/` (gitignored — do not commit).

## Toolchain pinning

The source declares `pragma language_version >= 0.16 && <= 0.22;` — identical
to the EBT v8 / tariff-registry convention. compactc 0.30.0 speaks language
0.22.0 so the pragma range admits it.

If `compactc` isn’t installed, grab it from the Midnight toolchain installer
and verify with `compactc --version` (expect `0.30.0`) and
`compactc --language-version` (expect `0.22.0`).

## Output

`zk/build/` contains:

```
compiler/contract-info.json       circuit + witness manifest
contract/index.d.ts               TypeScript type definitions
contract/index.js                 compiled JS shim (importable)
contract/index.js.map             source map for the JS shim
keys/<circuit>.prover             proving key   (~306 MB for N_MAX 128 — NOT committed)
keys/<circuit>.verifier           verifying key
zkir/<circuit>.bzkir              zkir bytecode
zkir/<circuit>.zkir               zkir text
```

A frozen note of compiler versions lives at `zk/build-manifest.txt`.
`zk/build/` itself is gitignored.

## Vector width

`N_MAX = 128`. Sites with **n > 128** split into **c = ceil(n/128)** chunks of
**near-equal size** (sizes differ by at most 1). Examples: 130 → 65+65,
300 → 100+100+100. Never “full 128 chunks plus remainder”.

With **n ≥ 25** overall this guarantees every chunk has ≥ 64 customers, so
`K_MIN = 25` holds per chunk. The split lives in
`pawacast/sharing/chunk.py` (`chunk_sizes`, `split_into_chunks`).

## k-anonymity floor

`record.compact` uses `K_MIN() = 25`, the same floor as
`pawacast/sharing/validate.py` `MIN_CUSTOMERS = 25`. Raised from 10 because
Laplace |noise| at n=10 with a 20 kWh clip is 40% of a typical 5 kWh mean.

## Fixture harness

`zk/run-fixtures.mjs` loads the compiled JS shim and invokes
`prove_published_sum_and_count` once per fixture in `zk/fixtures/`. It checks
that accept/reject matches the fixture’s `expect` field. It does **not**
generate real proofs — it exercises assert/revert logic against the compiled
shim and compact-runtime.

Prerequisite: `@midnight-ntwrk/compact-runtime@0.15.0` must be resolvable.
On the sprint machine the simplest path is a symlink to the sibling
`PollPower/contracts/tariff-registry/node_modules`:

```
ln -sf ../../contracts/tariff-registry/node_modules zk/node_modules
cd zk
node run-fixtures.mjs
rm zk/node_modules
```

Expected (4 fixtures):

```
=== Fixture results ===
[PASS] dirty_padding.json: expect=reject outcome=reject err="failed assert: PADDING_NONZERO"
[PASS] n24_should_fail.json: expect=reject outcome=reject err="failed assert: N_BELOW_K_MIN"
[PASS] valid_n25.json: expect=accept outcome=accept
[PASS] wrong_commitment.json: expect=reject outcome=reject err="failed assert: COMMIT_MISMATCH"
```

The symlink is a convenience, not committed.

## Changes from the Compact 0.18 scaffold

Compact 0.22 (compactc 0.30.0) rejects the 0.18 forms (`export ledger {}`,
top-level `const`, `assert cond;`, `let mut acc`, `return true`). The 0.22
rewrite uses `pure circuit` bounds, `assert(cond, "LABEL")`, scratch ledger
cells reset each call, and a unit return type. Semantics (sum/count equality
+ k-anonymity + padding-is-zero + commitment bytes match) are what the
fixtures check.
