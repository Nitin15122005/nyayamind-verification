# nyayamind-verification — research/prototype reproducibility image
#
# Built strictly from the Dockerization audit (research/requirements.txt,
# research/prototype/config/prototype.yaml, research/prototype/src/generator.py,
# research/prototype/src/verifier.py). Nothing in research/ is modified by
# this image — it only installs the exact pinned deps and copies source/data
# in read-only-equivalent form.
#
# Base: CUDA 12.1.1 + Ubuntu 22.04 (matches torch==2.2.2+cu121 and
# bitsandbytes==0.43.1, and the RTX 4050 6GB card this was validated on).
# "runtime" (not "devel") is sufficient — no compilation happens; torch and
# bitsandbytes wheels ship their own CUDA kernels.
FROM nvidia/cuda:12.1.1-runtime-ubuntu22.04

# Avoid interactive tzdata/apt prompts during build.
ENV DEBIAN_FRONTEND=noninteractive

# Python 3.11 (matches research/.venv: Python 3.11.9) via deadsnakes PPA —
# Ubuntu 22.04's system Python is 3.10.
RUN apt-get update && apt-get install -y --no-install-recommends \
        software-properties-common \
        curl \
    && add-apt-repository -y ppa:deadsnakes/ppa \
    && apt-get update && apt-get install -y --no-install-recommends \
        python3.11 \
        python3.11-venv \
        python3.11-distutils \
    && rm -rf /var/lib/apt/lists/* \
    && curl -sS https://bootstrap.pypa.io/get-pip.py | python3.11 \
    && ln -sf /usr/bin/python3.11 /usr/local/bin/python \
    && ln -sf /usr/bin/python3.11 /usr/local/bin/python3

WORKDIR /app

# Install the EXACT pinned dependency set from research/requirements.txt
# (torch==2.2.2+cu121, transformers==4.40.2, accelerate==0.29.3 — load-
# bearing pin, do not let pip re-resolve it — bitsandbytes==0.43.1,
# peft==0.10.0, trl==0.8.6, etc.). Copied alone first so this layer only
# rebuilds when requirements.txt changes, not on every source edit.
COPY research/requirements.txt research/requirements.txt
RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir -r research/requirements.txt

# Application code + read-only evidence/case data (see audit: these are not
# re-downloadable and must ship with the image).
COPY research/prototype/ research/prototype/
COPY research/data/evidence/ research/data/evidence/
COPY research/data/nyayarag/ research/data/nyayarag/
COPY research/baseline/scripts/ research/baseline/scripts/
COPY research/baseline/config/ research/baseline/config/

# Output directory the pipeline writes JSONL run records into. Created here
# so it exists even before the outputs volume is mounted; the volume mount
# in docker-compose.yml is what actually makes it persistent.
RUN mkdir -p /app/research/prototype/outputs

# Hugging Face cache lives here for the lifetime of the container/volume.
# No model is downloaded at build time — Qwen/Qwen2.5-7B-Instruct and the
# DeBERTa-v3 verifier are pulled by transformers on first real run only,
# into whatever HF_HOME points at (mounted as a named volume in compose).
ENV HF_HOME=/root/.cache/huggingface
# HF_TOKEN is deliberately NOT set/baked here — see docker-compose.yml,
# which passes it through from the host environment only if supplied.
# Only the gated baseline model (meta-llama/Llama-2-7b-chat-hf) needs it;
# the prototype's Qwen/DeBERTa models are both public.

# Default command loads no model, downloads nothing, uses no GPU — see
# audit point 8. Override with `docker compose run --rm app <cmd>` for a
# real Mode A/B/C run.
CMD ["python", "research/prototype/scripts/run_mvp.py", "--check"]
