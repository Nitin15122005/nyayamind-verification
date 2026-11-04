from types import SimpleNamespace

from src.run_manifest import build_run_manifest


def _evidence(text="Provision text"):
    return SimpleNamespace(
        dataset_citation_key="IPC|section|302",
        act="Indian Penal Code",
        provision_type="Section",
        provision_number="302",
        canonical_text=text,
    )


def test_manifest_is_deterministic_for_same_inputs():
    config = {"seed": 7, "generation": {"model_id": "model@revision"}}
    first = build_run_manifest(config, [_evidence()])
    second = build_run_manifest(config, [_evidence()])

    assert first == second
    assert len(first["config_sha256"]) == 64
    assert len(first["evidence_sha256"]) == 64
    assert first["evidence_records"] == 1


def test_manifest_changes_when_effective_config_or_evidence_changes():
    config = {"seed": 7, "generation": {"model_id": "model@revision"}}
    baseline = build_run_manifest(config, [_evidence()])

    changed_config = build_run_manifest(
        {"seed": 8, "generation": {"model_id": "model@revision"}}, [_evidence()]
    )
    changed_evidence = build_run_manifest(config, [_evidence("Amended provision text")])

    assert changed_config["config_sha256"] != baseline["config_sha256"]
    assert changed_evidence["evidence_sha256"] != baseline["evidence_sha256"]


def test_manifest_does_not_claim_model_weight_hashes():
    manifest = build_run_manifest(
        {"generation": {"model_id": "mutable/model-alias"}}, []
    )

    assert "model_revision_note" in manifest
    assert "not weight" in manifest["model_revision_note"]
