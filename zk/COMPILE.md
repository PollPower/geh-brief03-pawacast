# Compile `record.compact` on Linux

Do **not** compile this on Windows. `compact` on a Windows PATH is NTFS
compression (`C:\Windows\system32\compact.exe`), not Midnight Compact.
Do **not** deploy the compiled artifact to Midnight Preview without an explicit ask.

Toolchain matches the PollPower contracts repo (EBT v8 / TariffRegistry WI-13 pin):

| Piece | Version |
|---|---|
| `compactc` / `compactc.bin` | **0.30.0** |
| Compact language | `>= 0.16 && <= 0.22` |
| `@midnight-ntwrk/compact-runtime` | 0.15.0 |
| `@midnight-ntwrk/compact-js` | 2.5.0 |

On kenya the binary lives at:

```
/home/pollpower/.compact/versions/0.30.0/x86_64-unknown-linux-musl/compactc
```

(`compactc.bin` is the same compiler; deploy scripts on kenya call `compactc.bin`.)

## Steps (Linux)

```bash
# 1. Confirm you are not on Windows
uname -s    # expect Linux

# 2. Put compactc 0.30.0 and zkir on PATH (kenya layout)
export PATH="$HOME/.compact/versions/0.30.0/x86_64-unknown-linux-musl:$HOME/.compact/bin:$PATH"

# 3. Version must be 0.30.0
compactc.bin --version
# expected: compactc 0.30.0   (wording may include a git hash)

# 4. Compile this circuit only (no deploy)
cd /path/to/geh-brief03-pawacast
mkdir -p zk/build
compactc.bin zk/record.compact zk/build
```

Same invocation the contracts repo uses in `tariff-registry/deploy-preview.sh`:

```bash
compactc.bin "$CONTRACT_SRC" "$BUILD_DIR"
```

If the compiler is named `compactc` rather than `compactc.bin` on a laptop install:

```bash
compactc zk/record.compact zk/build
```

## After compile

Run the cases in `TEST_PLAN.md` (n ≥ 25 accept; n = 24 reject; sum/count mismatch reject; dirty padding reject). Write compiler version and pass/fail under `results/`. Still do not deploy.

If `compactc` 0.30.0 rejects the pragma or a syntax form, change `pragma language_version` to `>= 0.16 && <= 0.22` (already the pin) and match idioms in `ebt/ebt-v8.compact` in the contracts repo. Do not bump to 0.31.0.
