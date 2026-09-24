import pytest
from research_v2.src.generation.qwen3_adapter import Qwen3Adapter, Qwen3Config, MODEL_ID as QWEN_ID
from research_v2.src.verification.modernbert_verifier import ModernBertVerifier, ModernBertConfig, MODEL_ID as MB_ID

class TinyTokenizer:
    def __call__(self, a, b=None, add_special_tokens=True, truncation=False, **kw):
        ids_a = list(range(len(a.split())))
        if b is None:
            return {"input_ids": ([99] + ids_a + [98]) if add_special_tokens else ids_a}
        ids_b = list(range(len(b.split())))
        return {"input_ids": [99] + ids_a + [97] + ids_b + [98]}
    def num_special_tokens_to_add(self, pair=True): return 3
    def prepare_for_model(self, ids, pair_ids=None, **kw):
        return {"input_ids": [99] + ids + [97] + (pair_ids or []) + [98], "attention_mask": [1] * (len(ids)+(len(pair_ids or []))+3)}

class Cfg:
    id2label = {0: "entailment", 1: "neutral", 2: "contradiction"}
    max_position_embeddings = 2048
class Model: config = Cfg()


def verifier(config=ModernBertConfig()):
    return ModernBertVerifier(config, model=Model(), tokenizer=TinyTokenizer())

def test_qwen3_pinned_and_deterministic_defaults():
    c = Qwen3Config()
    assert c.model_id == QWEN_ID == "Qwen/Qwen3-4B-Instruct-2507"
    assert c.do_sample is False and c.seed == 42 and c.quantization == "4bit_nf4"
    with pytest.raises(ValueError): Qwen3Config(model_id="Qwen/Qwen3-4B")
    with pytest.raises(ValueError): Qwen3Config(quantization="8bit")

def test_modernbert_discovers_labels_from_config():
    assert verifier().id2label == {0: "entailment", 1: "neutral", 2: "contradiction"}

def test_modernbert_rejects_unmapped_checkpoint_labels():
    class Bad: config = type("BadConfig", (), {"id2label": {0: "LABEL_0", 1: "LABEL_1", 2: "LABEL_2"}})()
    with pytest.raises(ValueError, match="id2label"):
        ModernBertVerifier(model=Bad(), tokenizer=TinyTokenizer())

def test_long_evidence_is_chunked_without_dropping_tokens_or_claim():
    v = verifier(ModernBertConfig(max_position_length=12))
    chunks, info = v._encode_chunks("one two three four five six seven eight nine ten eleven", "claim words")
    assert len(chunks) > 1 and info["truncated"]
    assert info["evidence_tokens_dropped"] == info["claim_tokens_removed"] == 0
    assert info["chunk_count"] == len(chunks)
    assert all(len(c["input_ids"]) <= 12 for c in chunks)
    # At 12 positions, three special tokens + two claim tokens leave seven evidence tokens.
    assert sum(info["used_tokens_per_chunk"]) - (3 * len(chunks)) == 11 + 2 * len(chunks)

def test_claim_too_long_fails_instead_of_silent_truncation():
    v = verifier(ModernBertConfig(max_position_length=8))
    with pytest.raises(ValueError, match="Claim alone"):
        v._encode_chunks("evidence", "a long claim has more than enough tokens here")

def test_cuda_unavailable_requires_explicit_cpu(monkeypatch):
    torch = pytest.importorskip("torch")
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    with pytest.raises(RuntimeError, match="configure device='cpu'"):
        verifier()._device()
    assert str(verifier(ModernBertConfig(device="cpu"))._device()) == "cpu"

def test_verdict_threshold_configuration_fixed_default():
    assert ModernBertConfig().confidence_threshold == 0.70
    assert MB_ID == "tasksource/ModernBERT-large-nli"


def test_confidence_extraction_normalizes_and_marks_low_confidence():
    import torch
    from types import SimpleNamespace
    class PredictingModel(Model):
        def __call__(self, **inputs):
            return SimpleNamespace(logits=torch.tensor([[0.1, 0.2, 5.0]]))
    verifier = ModernBertVerifier(ModernBertConfig(device="cpu"), model=PredictingModel(), tokenizer=TinyTokenizer())
    result = verifier.verify("premise words", "contradicted claim")
    assert result["label"] == "CONTRADICTED"
    assert result["normalized_verdict"] == "CONTRADICTED"
    assert result["confidence"] > 0.70
    assert result["probability_distribution"]["contradiction"] == result["confidence"]
    assert result["sub_reason"] is None


def test_deterministic_result_schema_and_neutral_low_confidence_override():
    import torch
    from types import SimpleNamespace
    class UncertainModel(Model):
        def __call__(self, **inputs):
            return SimpleNamespace(logits=torch.tensor([[0.2, 0.1, 0.0]]))
    verifier = ModernBertVerifier(ModernBertConfig(device="cpu"), model=UncertainModel(), tokenizer=TinyTokenizer())
    first = verifier.verify("premise", "hypothesis")
    second = verifier.verify("premise", "hypothesis")
    assert first["normalized_verdict"] == "NOT_ENOUGH_INFORMATION"
    assert first["sub_reason"] == "low_confidence"
    assert first["probability_distribution"] == second["probability_distribution"]
    assert first["model_id"] == MB_ID


def test_qwen3_generation_adapter_schema_timing_and_determinism():
    import torch
    class ChatTokenizer:
        pad_token_id=0;eos_token_id=0
        def apply_chat_template(self,messages,**kwargs): return "prompt"
        def __call__(self,text,return_tensors=None,**kwargs):
            ids=[1,2,3]
            if return_tensors:return {"input_ids":torch.tensor([ids]),"attention_mask":torch.ones((1,len(ids)),dtype=torch.long)}
            return {"input_ids":ids}
        def decode(self,ids,skip_special_tokens=True): return "generated statutory paragraph"
    class CausalModel:
        device="cpu"
        def generate(self,input_ids,attention_mask,**kwargs):return torch.cat([input_ids,torch.tensor([[4,5]])],dim=1)
    adapter=Qwen3Adapter(Qwen3Config(device="cpu",quantization="none",max_input_length=20),model=CausalModel(),tokenizer=ChatTokenizer())
    first=adapter.generate("case facts")
    second=adapter.generate("case facts")
    assert first["text"]=="generated statutory paragraph"
    assert first["input_tokens"]==3 and first["output_tokens"]==2
    assert first["latency_seconds"]>=0 and first["input_truncated"] is False
    assert first["model_id"]==QWEN_ID and first["config"]["do_sample"] is False
    assert first["text"]==second["text"]


def test_qwen3_refuses_silent_prompt_truncation():
    import torch
    class LongTokenizer:
        pad_token_id=0;eos_token_id=0
        def apply_chat_template(self,messages,**kwargs):return "long"
        def __call__(self,text,return_tensors=None,**kwargs):
            ids=list(range(10))
            return {"input_ids":ids}
    adapter=Qwen3Adapter(Qwen3Config(device="cpu",quantization="none",max_input_length=4),model=object(),tokenizer=LongTokenizer())
    with pytest.raises(ValueError,match="refusing silent truncation"):
        adapter.generate("case")
