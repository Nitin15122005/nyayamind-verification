import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.archive_model_artifact_hashes import sha256_file


def test_sha256_file_hashes_large_files_incrementally(tmp_path):
    artifact = tmp_path / "weights.bin"
    payload = b"nyayamind-model-artifact\x00" * 100_000
    artifact.write_bytes(payload)

    expected = hashlib.sha256(payload).hexdigest()
    assert sha256_file(artifact) == expected
