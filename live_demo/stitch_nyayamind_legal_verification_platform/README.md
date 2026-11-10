# NyayaMind live demo — design references

The running application is the React + Vite frontend in `live_demo/web/` and
the Python standard-library streaming backend in `live_demo/server/`. The HTML files and
screenshots in this directory are historical Stitch design references only;
they are not separate applications and are not used by the runtime.

## Run the current application

From the repository root, start the backend:

```bash
research/.venv/Scripts/python.exe live_demo/server/app.py
```

In another terminal, start the frontend:

```bash
cd live_demo/web
npm ci
npm run dev
```

The frontend runs at `http://localhost:5174` and proxies `/api` requests
to the backend at `http://127.0.0.1:8421`.

## Directory policy

- `live_demo/web/` is the single maintained browser frontend.
- `live_demo/server/` is its backend adapter to the real research pipeline.
- `legacy-demo-export/`, `nyayamind_home/`, and
  `nyayamind_design_system/` are preserved visual references, not runnable
  demos. Do not link to or deploy them as live applications.
- The separate Python evaluation walkthroughs live in
  `research/prototype/evaluation/demo_suite/`; they are research scripts,
  not a second web frontend.
