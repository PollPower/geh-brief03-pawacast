#!/usr/bin/env node
// Offline harness for zk/record.compact. Loads the compiled TS/JS shim,
// constructs a dummy circuit context, invokes prove_published_sum_and_count
// with witnesses sourced from zk/fixtures/*.json, and reports pass/fail.
//
// Not a Midnight Preview deploy. Pure local circuit execution — proving-key
// isn't exercised here; we're verifying the circuit's assert/revert logic
// behaves per fixture 'expect' field.

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import {
  createCircuitContext,
  createConstructorContext,
  dummyContractAddress,
} from '@midnight-ntwrk/compact-runtime';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const BUILD_INDEX = path.resolve(HERE, 'build/contract/index.js');
const FIXTURES_DIR = path.resolve(HERE, 'fixtures');

const buildModule = await import(pathToFileURL(BUILD_INDEX).href);
const { Contract } = buildModule;

const N_MAX = 128;

function hexToBytes(hex) {
  const h = String(hex).replace(/^0x/, "");
  if (h.length !== 64) {
    throw new Error(`commitment hex must be 32 bytes, got ${h.length / 2}`);
  }
  const out = new Uint8Array(32);
  for (let i = 0; i < 32; i += 1) {
    out[i] = parseInt(h.slice(i * 2, i * 2 + 2), 16);
  }
  return out;
}

function makeWitnesses(fixture) {
  const n = BigInt(fixture.witness.privateN);
  const values = fixture.witness.privateValuesMilliKwh.map((v) => BigInt(v));
  if (values.length !== N_MAX) {
    throw new Error(
      `fixture privateValuesMilliKwh must have length ${N_MAX}, got ${values.length}`,
    );
  }
  const bound = hexToBytes(fixture.witness.privateCommitment);
  return {
    privateN: (ps) => [ps, n],
    privateValuesMilliKwh: (ps) => [ps, values],
    privateCommitment: (ps) => [ps, bound],
  };
}

function runFixture(fixturePath) {
  const fixture = JSON.parse(fs.readFileSync(fixturePath, 'utf8'));
  const witnesses = makeWitnesses(fixture);
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
  const commitment = hexToBytes(fixture.public.commitment);
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
  return { fixturePath, publishedN, publishedSum, expect, outcome, errMsg, passed };
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
    results.push({ fixturePath: f, passed: false, errMsg: `HARNESS ERROR: ${e?.message ?? e}` });
  }
}

console.log('=== Fixture results ===');
for (const r of results) {
  const name = path.basename(r.fixturePath);
  const tag = r.passed ? 'PASS' : 'FAIL';
  const detail = r.outcome
    ? `expect=${r.expect} outcome=${r.outcome}` + (r.errMsg ? ` err="${r.errMsg.split('\n')[0]}"` : '')
    : r.errMsg;
  console.log(`[${tag}] ${name}: ${detail}`);
}

const anyFail = results.some((r) => !r.passed);
process.exit(anyFail ? 1 : 0);
