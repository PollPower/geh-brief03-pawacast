#!/usr/bin/env node
// Offline harness for zk/record.compact (Compact 0.22 port).
//
// For each fixture under zk/fixtures/:
//   * builds witnesses from fixture.witness
//   * if fixture.public.commitment == "AUTO", computes the correct chained
//     persistentHash commitment from (salt, n, values) and feeds it in
//   * otherwise uses the provided commitment hex (lets a fixture inject a
//     deliberately-wrong commitment to prove COMMITMENT_MISMATCH fires)
//   * invokes prove_published_sum_and_count via the compiled TS/JS shim
//   * checks the outcome matches fixture.expect ("accept" or "reject")
//   * for reject fixtures, prints the assert label from the thrown error
//
// Does NOT generate a real proof — exercises the circuit's assert/revert
// surface against the Compact runtime (0.15.0). No deploy.

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import {
  createCircuitContext,
  createConstructorContext,
  dummyContractAddress,
  persistentHash,
  CompactTypeBytes,
  CompactTypeVector,
} from '@midnight-ntwrk/compact-runtime';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const BUILD_INDEX = path.resolve(HERE, 'build/contract/index.js');
const FIXTURES_DIR = path.resolve(HERE, 'fixtures');

const buildModule = await import(pathToFileURL(BUILD_INDEX).href);
const { Contract } = buildModule;

// pad(32, s) — UTF-8 encode s, zero-pad to 32 bytes (matches Compact `pad`).
function pad32(s) {
  const out = new Uint8Array(32);
  const encoded = new TextEncoder().encode(s);
  if (encoded.length > 32) throw new Error(`pad32: '${s}' is ${encoded.length} bytes, max 32`);
  out.set(encoded, 0);
  return out;
}

// u32-as-Field-as-Bytes32 — matches Compact's `(v as Field) as Bytes<32>` which
// goes through compactRuntime.convertFieldToBytes(32, x, ...). That function
// writes LITTLE-ENDIAN into the output: a[0] = x & 0xff, a[1] = (x>>8) & 0xff,
// … up to a[31]. See casts.js. Must match exactly or the harness's commitment
// won't equal the circuit's.
function u32ToBytes32(n) {
  const out = new Uint8Array(32);
  let x = BigInt(n);
  for (let i = 0; i < 32; i++) {
    out[i] = Number(x & 0xffn);
    x = x / 0x100n;
    if (x === 0n) break;
  }
  return out;
}

// Hex helpers.
function toHex(u8) {
  return Array.from(u8).map((b) => b.toString(16).padStart(2, '0')).join('');
}
function fromHex(hex) {
  if (hex.startsWith('0x')) hex = hex.slice(2);
  if (hex.length !== 64) throw new Error(`fromHex expected 64 chars (32 bytes), got ${hex.length}`);
  const out = new Uint8Array(32);
  for (let i = 0; i < 32; i++) out[i] = parseInt(hex.slice(2 * i, 2 * i + 2), 16);
  return out;
}

// Replicate the circuit's commitment chain:
//   h0 = persistentHash<Vec<3,Bytes<32>>>([pad("pp:pawacast:record:v1:init"), salt, u32ToBytes32(n)])
//   h_{i+1} = persistentHash<Vec<3,Bytes<32>>>([pad("pp:pawacast:record:v1:absorb"), h_i, u32ToBytes32(v_i)])
const VEC3_BYTES32_TYPE = new CompactTypeVector(3, new CompactTypeBytes(32));
const TAG_INIT = pad32('pp:pawacast:record:v1:init');
const TAG_ABSORB = pad32('pp:pawacast:record:v1:absorb');

function computeCommitment(salt, n, values) {
  if (values.length !== 128) {
    throw new Error(`computeCommitment: values must have length 128 (N_MAX), got ${values.length}`);
  }
  const nBytes = u32ToBytes32(n);
  let h = persistentHash(VEC3_BYTES32_TYPE, [TAG_INIT, salt, nBytes]);
  for (let i = 0; i < values.length; i++) {
    const vBytes = u32ToBytes32(values[i]);
    h = persistentHash(VEC3_BYTES32_TYPE, [TAG_ABSORB, h, vBytes]);
  }
  return h;
}

function makeWitnesses(fixture) {
  const n = BigInt(fixture.witness.privateN);
  const values = fixture.witness.privateValuesMilliKwh.map((v) => BigInt(v));
  if (values.length !== 128) {
    throw new Error(`fixture privateValuesMilliKwh must have length 128, got ${values.length}`);
  }
  const salt = fromHex(fixture.witness.privateSalt);
  return {
    witnesses: {
      privateSalt: (ps) => [ps, salt],
      privateN: (ps) => [ps, n],
      privateValuesMilliKwh: (ps) => [ps, values],
    },
    salt,
    n: Number(n),
    valuesAsNumbers: values.map((v) => Number(v)),
  };
}

function runFixture(fixturePath) {
  const fixture = JSON.parse(fs.readFileSync(fixturePath, 'utf8'));
  const { witnesses, salt, n, valuesAsNumbers } = makeWitnesses(fixture);

  // Resolve the public commitment: AUTO = compute from witness; else hex.
  let commitment;
  let commitmentNote;
  if (fixture.public.commitment === 'AUTO') {
    commitment = computeCommitment(salt, n, valuesAsNumbers);
    commitmentNote = 'auto-computed';
  } else {
    commitment = fromHex(fixture.public.commitment);
    commitmentNote = `from fixture (${fixture.public.commitment.slice(0, 10)}…)`;
  }

  const contract = new Contract(witnesses);
  const ctorCtx = createConstructorContext(null, '0'.repeat(64));
  const { currentContractState, currentPrivateState, currentZswapLocalState } =
    contract.initialState(ctorCtx);

  const circuitCtx = createCircuitContext(
    dummyContractAddress(),
    currentZswapLocalState.coinPublicKey,
    currentContractState.data,
    currentPrivateState,
  );

  const publishedN = BigInt(fixture.public.publishedN);
  const publishedSum = BigInt(fixture.public.publishedSumMilliKwh);
  const expect = fixture.expect;

  let outcome;
  let errMsg = null;
  try {
    contract.circuits.prove_published_sum_and_count(
      circuitCtx,
      publishedN,
      publishedSum,
      commitment,
    );
    outcome = 'accept';
  } catch (e) {
    outcome = 'reject';
    errMsg = e?.message ?? String(e);
  }

  const passed = outcome === expect;
  return {
    fixturePath,
    publishedN,
    publishedSum,
    commitmentHex: toHex(commitment),
    commitmentNote,
    expect,
    outcome,
    errMsg,
    passed,
  };
}

const fixtures = fs
  .readdirSync(FIXTURES_DIR)
  .filter((f) => f.endsWith('.json'))
  .sort();

const results = [];
for (const f of fixtures) {
  try {
    const r = runFixture(path.join(FIXTURES_DIR, f));
    results.push(r);
  } catch (e) {
    results.push({
      fixturePath: f,
      passed: false,
      errMsg: `HARNESS ERROR: ${e?.message ?? e}\n${e?.stack ?? ''}`,
    });
  }
}

console.log('=== Fixture results ===');
for (const r of results) {
  const name = path.basename(r.fixturePath);
  const tag = r.passed ? 'PASS' : 'FAIL';
  const detail = r.outcome
    ? `expect=${r.expect} outcome=${r.outcome} commitment=${r.commitmentNote}` +
      (r.errMsg ? ` err="${r.errMsg.split('\n')[0]}"` : '')
    : r.errMsg;
  console.log(`[${tag}] ${name}: ${detail}`);
}

const anyFail = results.some((r) => !r.passed);
process.exit(anyFail ? 1 : 0);
