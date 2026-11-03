/** Thin client for the real backend. fetchExamples/fetchArchitecture are
 * plain JSON; runVerification streams newline-delimited JSON stage events
 * as the real pipeline executes them (server/app.py's run_streaming), so
 * onEvent fires in genuine real time, never on a fixed timer. */

export async function fetchExamples() {
  const res = await fetch("/api/examples");
  if (!res.ok) throw new Error("Could not load examples.");
  return res.json();
}

export async function fetchArchitecture() {
  const res = await fetch("/api/architecture");
  if (!res.ok) throw new Error("Could not load architecture.");
  return res.json();
}

export async function fetchConfig() {
  const res = await fetch("/api/config");
  if (!res.ok) throw new Error("Could not load config.");
  return res.json();
}

/**
 * Runs the real pipeline via POST /api/run and streams stage events.
 * `body` is either {mode:"example", id} or {mode:"custom", text}.
 * `onEvent({stage, status, data})` is called once per real stage event, in
 * the order the backend actually completed them.
 */
export async function runVerification(body, onEvent, { signal } = {}) {
  const res = await fetch("/api/run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });
  if (!res.ok || !res.body) {
    let message = "The verification run could not be started.";
    try {
      const payload = await res.json();
      if (payload?.error) message = payload.error;
    } catch {
      // Keep the stable fallback message for non-JSON server failures.
    }
    throw new Error(message);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder("utf-8", { fatal: true });
  let buffer = "";
  let completed = false;

  function dispatchLine(rawLine) {
    const line = rawLine.trim();
    if (!line) return;
    let event;
    try {
      event = JSON.parse(line);
    } catch {
      throw new Error("The verification stream returned an invalid event. No result was accepted.");
    }
    if (!event || typeof event.stage !== "string" || typeof event.status !== "string") {
      throw new Error("The verification stream returned an incomplete event. No result was accepted.");
    }
    onEvent(event);
    if (event.stage === "error") {
      throw new Error(event.data?.message || "The verification run failed.");
    }
    if (event.stage === "run" && event.status === "complete") completed = true;
  }

  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      let newlineIndex;
      // eslint-disable-next-line no-cond-assign
      while ((newlineIndex = buffer.indexOf("\n")) >= 0) {
        const line = buffer.slice(0, newlineIndex);
        buffer = buffer.slice(newlineIndex + 1);
        dispatchLine(line);
      }
    }
    buffer += decoder.decode();
    if (buffer.trim()) dispatchLine(buffer);
  } catch (error) {
    try { await reader.cancel(); } catch { /* stream already closed */ }
    throw error;
  }

  if (!completed) {
    throw new Error("The verification stream ended before a successful final status was received. The result was not accepted.");
  }
}
