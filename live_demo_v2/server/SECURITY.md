# Live Demo API security configuration

The live-demo API is a **local development service**, not a public deployment
server. It binds to `127.0.0.1:8421` and validates both the HTTP Host and
browser Origin headers.

## Default browser origins

The server allows only these origins by default:

- `http://localhost:5174` — configured Vite development port
- `http://127.0.0.1:5174`
- `http://localhost:4173` — Vite preview default
- `http://127.0.0.1:4173`

CORS does not use a wildcard and does not enable credentials. State-changing
`POST /api/run` requests require an explicitly allowed Origin. Preflight
requests are restricted to GET/POST and the `Content-Type` request header.

## Custom local frontend origin

If the frontend is served from a different trusted local origin, set
`NYAYAMIND_ALLOWED_ORIGINS` before starting the Python server. The value is a
comma-separated list of exact origins, including scheme and port, with no
paths. For example:

```powershell
$env:NYAYAMIND_ALLOWED_ORIGINS = "http://localhost:5174,http://127.0.0.1:5174"
research/.venv/Scripts/python.exe live_demo_v2/server/app.py
```

The allowed Host names can also be overridden with
`NYAYAMIND_ALLOWED_HOSTS`, as a comma-separated list including the port.
Only configure hostnames that resolve to the local machine and that you
control. These environment variables are read at process startup; restart the
server after changing them.

## Request limits and schema

- Maximum HTTP request body: **1 MiB**.
- Maximum custom input text: **100,000 Unicode characters**.
- Request body read timeout: **10 seconds**.
- POST requires `Content-Type: application/json` and a valid
  `Content-Length`; chunked request bodies are not accepted.
- Example requests must have exactly `mode` and `id`, and the ID must exist.
- Custom requests must have exactly `mode` and `text`; text must be a
  non-empty string.
- Non-object JSON, duplicate JSON keys, unknown fields, invalid modes, and
  invalid field types are rejected before pipeline state is accessed.

## Security boundary

Host and Origin checks mitigate browser-based cross-origin access and common
DNS-rebinding attempts. They are **not authentication** and do not protect
against malicious software or users already running code on the same machine.
Do not change the server bind address to `0.0.0.0`, expose port 8421 to a LAN,
or treat this local demo as an internet-facing service. A public deployment
requires a separate authenticated deployment architecture, TLS termination,
rate limiting, and operational monitoring.

## Regression tests

Run from the repository root:

```powershell
research/.venv/Scripts/python.exe -m unittest discover -s live_demo_v2/server/tests -v
```

The tests use a real loopback HTTP socket and leave model/pipeline state
uninitialised. Valid requests therefore stop at the expected startup response;
the tests do not download models or run GPU inference.
