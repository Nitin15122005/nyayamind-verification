#!/usr/bin/env python3
"""Execute the four generator/verifier pairings on the paired natural cases."""
from __future__ import annotations
import subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
if __name__=="__main__":
    cmd=[sys.executable,str(ROOT/"research_v2"/"scripts"/"run_full_pipeline.py"),"--matrix","--limit","50"]+sys.argv[1:]
    raise SystemExit(subprocess.call(cmd,cwd=ROOT))
