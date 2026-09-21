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
      // ignore
    }
    throw new Error(message);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let newlineIndex;
    // eslint-disable-next-line no-cond-assign
    while ((newlineIndex = buffer.indexOf("\n")) >= 0) {
      const line = buffer.slice(0, newlineIndex).trim();
      buffer = buffer.slice(newlineIndex + 1);
      if (!line) continue;
      try {
        onEvent(JSON.parse(line));
      } catch {
        // ignore a malformed/partial line
      }
    }
  }
  if (buffer.trim()) {
    try {
      onEvent(JSON.parse(buffer.trim()));
    } catch {
      // ignore
    }
  }
}
