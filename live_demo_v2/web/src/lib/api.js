/** Thin client for the real backend. The run stream is strict NDJSON:
 * malformed events and missing terminal events are failures, never silently ignored. */
export async function fetchExamples({ signal } = {}) {
  const res = await fetch("/api/examples", { signal });
  if (!res.ok) throw new Error("Could not load examples.");
  return res.json();
}
export async function fetchArchitecture({ signal } = {}) {
  const res = await fetch("/api/architecture", { signal });
  if (!res.ok) throw new Error("Could not load architecture.");
  return res.json();
}
export async function fetchConfig({ signal } = {}) {
  const res = await fetch("/api/config", { signal });
  if (!res.ok) throw new Error("Could not load config.");
  return res.json();
}
export async function runVerification(body, onEvent, { signal } = {}) {
  const res = await fetch("/api/run", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body), signal,
  });
  if (!res.ok || !res.body) {
    let message = "The verification run could not be started.";
    try { const payload = await res.json(); if (payload?.error) message = payload.error; } catch { /* HTTP status is authoritative. */ }
    throw new Error(message);
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder("utf-8", { fatal: true });
  let buffer = "";
  let terminal = null;
  function consumeLine(rawLine) {
    const line = rawLine.trim();
    if (!line) return;
    if (terminal) throw new Error("The server sent data after the run ended.");
    let event;
    try { event = JSON.parse(line); } catch { throw new Error("The server sent a malformed verification event."); }
    if (!event || typeof event !== "object" || typeof event.stage !== "string" ||
        typeof event.status !== "string" ||
        (event.data !== undefined && (!event.data || typeof event.data !== "object" || Array.isArray(event.data)))) {
      throw new Error("The server sent an invalid verification event.");
    }
    if (event.stage === "error") {
      onEvent(event);
      terminal = "failed";
      throw new Error(event.data?.message || "The verification run failed.");
    }
    if (event.stage === "run" && event.status === "complete") terminal = "complete";
    onEvent(event);
  }
  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      let newlineIndex;
      while ((newlineIndex = buffer.indexOf("\n")) >= 0) {
        const line = buffer.slice(0, newlineIndex);
        buffer = buffer.slice(newlineIndex + 1);
        consumeLine(line);
      }
    }
    buffer += decoder.decode();
    if (buffer.trim()) consumeLine(buffer);
    if (terminal !== "complete") throw new Error("The server stream ended before reporting successful completion.");
  } catch (error) {
    if (signal?.aborted) { try { await reader.cancel(); } catch { /* connection already closed */ } }
    throw error;
  } finally {
    reader.releaseLock();
  }
}
