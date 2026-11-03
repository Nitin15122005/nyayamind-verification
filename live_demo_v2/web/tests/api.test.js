import test from "node:test";
import assert from "node:assert/strict";
import { runVerification } from "../src/lib/api.js";

function mockStream(text) {
  return new Response(new ReadableStream({
    start(controller) {
      controller.enqueue(new TextEncoder().encode(text));
      controller.close();
    },
  }), { status: 200, headers: { "Content-Type": "application/x-ndjson" } });
}

function event(stage, status, data = {}) {
  return JSON.stringify({ stage, status, data }) + "\n";
}

test("accepts a complete successful event stream", async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => mockStream(
    event("run", "started") +
    event("input", "complete") +
    event("run", "complete")
  );
  const received = [];
  try {
    await runVerification({ mode: "custom", text: "claim" }, (e) => received.push(e));
    assert.equal(received.at(-1).stage, "run");
    assert.equal(received.at(-1).status, "complete");
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("rejects malformed NDJSON instead of silently dropping it", async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => mockStream('{"stage":broken}\n');
  try {
    await assert.rejects(
      runVerification({ mode: "custom", text: "claim" }, () => {}),
      /malformed verification event/
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("rejects streams that end without a successful terminal event", async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => mockStream(event("input", "complete"));
  try {
    await assert.rejects(
      runVerification({ mode: "custom", text: "claim" }, () => {}),
      /ended before reporting successful completion/
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("surfaces explicit backend failure events", async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => mockStream(event("error", "failed", { message: "inference failed" }));
  const received = [];
  try {
    await assert.rejects(
      runVerification({ mode: "custom", text: "claim" }, (e) => received.push(e)),
      /inference failed/
    );
    assert.equal(received[0].stage, "error");
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("rejects data after a terminal success event", async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => mockStream(
    event("run", "complete") + event("result", "complete")
  );
  try {
    await assert.rejects(
      runVerification({ mode: "custom", text: "claim" }, () => {}),
      /data after the run ended/
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});
