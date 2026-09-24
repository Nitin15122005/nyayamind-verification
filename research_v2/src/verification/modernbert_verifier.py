"""ModernBERT-large-NLI adapter with checkpoint-derived labels and auditable chunking."""
from __future__ import annotations
from dataclasses import dataclass
import os
import time
from typing import Any

MODEL_ID = "tasksource/ModernBERT-large-nli"
VERDICT_MAP = {"entailment": "ENTAILED", "neutral": "NOT_ENOUGH_INFORMATION", "contradiction": "CONTRADICTED"}

def _local_revision(path: str | None) -> str | None:
    if not path:
        return None
    metadata = __import__("pathlib").Path(path) / ".cache" / "huggingface" / "download" / "config.json.metadata"
    try:
        value = metadata.read_text(encoding="utf-8").splitlines()[0].strip()
        return value or None
    except (OSError, IndexError):
        return None

@dataclass(frozen=True)
class ModernBertConfig:
    model_id: str = MODEL_ID
    confidence_threshold: float = 0.70
    max_position_length: int = 2048
    device: str = "cuda"
    truncation_policy: str = "chunk_all_evidence_preserve_claim"
    model_path: str | None = None
    def __post_init__(self):
        if self.model_id != MODEL_ID: raise ValueError(f"This adapter is pinned to {MODEL_ID}")
        if not 0 <= self.confidence_threshold <= 1: raise ValueError("threshold must be in [0,1]")
        if self.max_position_length < 8: raise ValueError("max position length implausibly small")
        if self.device != "cpu" and not self.device.startswith("cuda"):
            raise ValueError("device must be cpu or an explicit cuda device such as cuda:0")

class ModernBertVerifier:
    def __init__(self, config: ModernBertConfig = ModernBertConfig(), model=None, tokenizer=None):
        self.config, self.model, self.tokenizer = config, model, tokenizer
        self.model_revision = None
        self.model_source = None
        if model is None or tokenizer is None: self._load()
        self.id2label = self._resolve_labels()

    def _device(self):
        import torch
        if self.config.device.startswith("cuda") and not torch.cuda.is_available():
            raise RuntimeError(f"CUDA device {self.config.device!r} requested but CUDA is unavailable; configure device='cpu' explicitly")
        return torch.device(self.config.device)

    def _load(self):
        # Check hardware before network/cache access to make failures explicit and cheap.
        self.device = self._device()
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
        source = self.config.model_path or os.environ.get("NYAYAMIND_MODERNBERT_PATH") or self.config.model_id
        self.model_source = source
        self.tokenizer = AutoTokenizer.from_pretrained(source, local_files_only=source != self.config.model_id)
        self.model = AutoModelForSequenceClassification.from_pretrained(source, local_files_only=source != self.config.model_id)
        self.model.to(self.device).eval()
        self.model_revision = getattr(getattr(self.model, "config", None), "_commit_hash", None) or _local_revision(source if source != self.config.model_id else None)
        configured = getattr(self.model.config, "max_position_embeddings", None)
        if configured:
            limit = min(self.config.max_position_length, int(configured))
            self.config = ModernBertConfig(model_id=self.config.model_id, model_path=self.config.model_path, confidence_threshold=self.config.confidence_threshold, max_position_length=limit, device=self.config.device, truncation_policy=self.config.truncation_policy)

    def _resolve_labels(self):
        raw = getattr(self.model.config, "id2label", None) or {}
        found = {}
        for idx, label in raw.items():
            name = str(label).lower().replace(" ", "_").replace("-", "_")
            for canonical in VERDICT_MAP:
                if name == canonical or name.endswith("_" + canonical): found[int(idx)] = canonical
        if set(found.values()) != set(VERDICT_MAP):
            raise ValueError(f"Checkpoint id2label must identify entailment, neutral, contradiction; got {raw}")
        return found

    def _encode_chunks(self, premise: str, hypothesis: str):
        """Return all premise chunks paired with the complete hypothesis; no evidence is dropped."""
        limit = self.config.max_position_length
        hyp = self.tokenizer(hypothesis, add_special_tokens=False)["input_ids"]
        prem = self.tokenizer(premise, add_special_tokens=False)["input_ids"]
        special = self.tokenizer.num_special_tokens_to_add(pair=True)
        premise_budget = limit - len(hyp) - special
        if premise_budget < 1:
            raise ValueError(f"Claim alone requires {len(hyp)+special} tokens, exceeding maximum {limit}; refusing to truncate claim")
        chunks = [prem[i:i + premise_budget] for i in range(0, len(prem), premise_budget)] or [[]]
        encoded = []
        for chunk in chunks:
            if hasattr(self.tokenizer, "prepare_for_model"):
                pair = self.tokenizer.prepare_for_model(chunk, hyp, add_special_tokens=True, truncation=False, return_attention_mask=True)
            else:
                # Transformers 5's TokenizersBackend removed prepare_for_model.
                # Decode only at the token boundary, then ask the checkpoint tokenizer
                # to assemble its normal pair format; no claim or evidence chunk is cut.
                chunk_text = self.tokenizer.backend_tokenizer.decode(chunk, skip_special_tokens=True)
                pair = self.tokenizer(chunk_text, hypothesis, add_special_tokens=True, truncation=False, return_attention_mask=True)
            if len(pair["input_ids"]) > limit: raise RuntimeError("Pair construction exceeded configured max length")
            encoded.append(pair)
        full = self.tokenizer(premise, hypothesis, add_special_tokens=True, truncation=False)
        lengths = {"evidence_tokens": len(prem), "claim_tokens": len(hyp),
                   "original_pair_tokens": len(full["input_ids"]),
                   "used_tokens_per_chunk": [len(pair["input_ids"]) for pair in encoded],
                   "truncated": len(encoded) > 1,
                   "chunk_count": len(encoded), "evidence_tokens_dropped": 0,
                   "claim_tokens_removed": 0,
                   "policy": "mean_probability_across_ordered_evidence_chunks" if len(encoded) > 1 else "single_full_pair"}
        return encoded, lengths

    def verify(self, premise: str, hypothesis: str) -> dict[str, Any]:
        import torch
        device = getattr(self, "device", None) or self._device()
        encoded_chunks, lengths = self._encode_chunks(premise, hypothesis)
        started = time.perf_counter()
        chunk_probabilities = []
        with torch.inference_mode():
            for encoded in encoded_chunks:
                inputs = {k: torch.tensor([v], dtype=torch.long, device=device) for k,v in encoded.items()
                          if k in {"input_ids", "attention_mask", "token_type_ids"}}
                logits = self.model(**inputs).logits[0]
                probs = torch.softmax(logits.float(), dim=-1).cpu().tolist()
                if any(not (float(p) >= 0 and float(p) <= 1) for p in probs): raise ValueError("Invalid probability")
                chunk_probabilities.append([float(p) for p in probs])
        latency = time.perf_counter()-started
        # Fixed, deterministic aggregation: arithmetic mean of the full class distributions,
        # equal weight per ordered evidence chunk. Threshold is applied once after aggregation.
        probs = [sum(row[i] for row in chunk_probabilities) / len(chunk_probabilities) for i in range(len(chunk_probabilities[0]))]
        pred_id = max(range(len(probs)), key=probs.__getitem__)
        raw_label = self.id2label.get(pred_id)
        if raw_label is None: raise ValueError(f"No semantic mapping for predicted label id {pred_id}")
        confidence = float(probs[pred_id]); low = confidence < self.config.confidence_threshold
        verdict = "NOT_ENOUGH_INFORMATION" if low else VERDICT_MAP[raw_label]
        prefix_probs=chunk_probabilities[0]
        prefix_id=max(range(len(prefix_probs)),key=prefix_probs.__getitem__)
        prefix_raw=self.id2label[prefix_id]
        prefix_low=prefix_probs[prefix_id] < self.config.confidence_threshold
        prefix_verdict="NOT_ENOUGH_INFORMATION" if prefix_low else VERDICT_MAP[prefix_raw]
        return {"label": verdict, "confidence": confidence,
            "probability_distribution": {self.id2label[i]: float(probs[i]) for i in range(len(probs))},
            "chunk_probability_distributions": [{self.id2label[i]: row[i] for i in range(len(row))} for row in chunk_probabilities],
            "aggregation": "arithmetic_mean_equal_weight_then_argmax_threshold",
            "prefix_only_verdict": prefix_verdict,
            "prefix_only_confidence": float(prefix_probs[prefix_id]),
            "chunk_aggregation_changes_verdict": len(chunk_probabilities)>1 and prefix_verdict != verdict,
            "raw_model_label": str(getattr(self.model.config, "id2label", {}).get(pred_id, raw_label)),
            "normalized_verdict": verdict, "sub_reason": "low_confidence" if low else None,
            "low_confidence": low, "model_id": self.config.model_id, "model_revision": self.model_revision,
            "latency_seconds": latency, "token_lengths": lengths}
