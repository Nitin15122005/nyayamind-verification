import torch

from src.corrector import SelectiveCorrector


class FakeBatch(dict):
    def to(self, device):
        return self


class FakeTokenizer:
    def __init__(self, decoded):
        self.decoded = decoded
        self.prompt = None

    def apply_chat_template(self, messages, tokenize, add_generation_prompt):
        self.prompt = messages
        return "mock prompt"

    def __call__(self, prompt, return_tensors):
        return FakeBatch(input_ids=torch.tensor([[1, 2]]))

    def decode(self, generated_ids, skip_special_tokens):
        return self.decoded


class FakeModel:
    device = "cpu"

    def generate(self, **kwargs):
        return torch.tensor([[1, 2, 3, 4]])


class FakeGenerator:
    model_id = "mock-generator"
    seed = 42
    _model = FakeModel()

    def __init__(self, decoded):
        self._tokenizer = FakeTokenizer(decoded)

    def is_loaded(self):
        return True


def _corrector(decoded):
    return SelectiveCorrector(
        generator=FakeGenerator(decoded),
        max_new_tokens=100,
        do_sample=False,
        system_prompt="system",
    )


def test_structured_patch_parser_accepts_exact_schema():
    patch, meta = _corrector(
        '{"original_span":"a fine only","replacement_span":"imprisonment and fine"}'
    ).correct_assertion_patch(
        case_text="case facts",
        target_span="Section 302 prescribes a fine only.",
        evidence_text="statute",
        assertion_span_system_prompt="system",
        max_new_tokens=100,
    )
    assert patch == {
        "original_span": "a fine only",
        "replacement_span": "imprisonment and fine",
    }
    assert meta.model_id == "mock-generator"


def test_structured_patch_parser_rejects_extra_keys():
    patch, _ = _corrector(
        '{"original_span":"wrong","replacement_span":"right","explanation":"x"}'
    ).correct_assertion_patch(
        case_text="facts", target_span="wrong claim", evidence_text="law",
        assertion_span_system_prompt="system", max_new_tokens=100,
    )
    assert patch == {"original_span": "", "replacement_span": ""}


def test_structured_patch_parser_accepts_fenced_json():
    patch, _ = _corrector(
        ' ```json\n{"original_span":"wrong","replacement_span":"right"}\n``` '
    ).correct_assertion_patch(
        case_text="facts", target_span="wrong claim", evidence_text="law",
        assertion_span_system_prompt="system", max_new_tokens=100,
    )
    assert patch == {"original_span": "wrong", "replacement_span": "right"}


def test_structured_patch_parser_fails_closed_on_non_json():
    patch, _ = _corrector("The corrected phrase is right.").correct_assertion_patch(
        case_text="facts", target_span="wrong claim", evidence_text="law",
        assertion_span_system_prompt="system", max_new_tokens=100,
    )
    assert patch == {"original_span": "", "replacement_span": ""}
