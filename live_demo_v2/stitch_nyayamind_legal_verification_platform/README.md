# NyayaMind Live Demo

Two processes, run from the repo root.

## 1. Backend (real pipeline API)

```bash
research/.venv/Scripts/python.exe live_demo/server/app.py
```

Serves on `http://127.0.0.1:8421`. Loads the production config, the real evidence pool, and the
real DeBERTa verifier at startup. The Qwen2.5-7B-Instruct correction model loads lazily, live, the
first time a custom-text run actually triggers a correction (curated examples replay an
already-committed real correction instead -- see `server/app.py`'s module docstring).

Watch this process's own terminal while using the site -- it prints real `[NyayaMind]` progress
lines as each pipeline stage actually executes.

## 2. Frontend

```bash
cd live_demo/web
npm install   # first time only
npm run dev
```

Serves on `http://localhost:5174`, proxying `/api` to the backend above.

`nyayamind_home/`, `nyayamind_live_demo/`, and `nyayamind_design_system/` are the original Stitch
visual references -- untouched, not part of the running site.
