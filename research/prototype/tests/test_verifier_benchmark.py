"""
Tests for verifier benchmark generation and QwenLLMVerifier.
"""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from src.data_loader import EvidenceRecord
from src.verifier import ENTAILED, CONTRADICTED, NOT_ENOUGH_INFORMATION
from src.llm_verifier import QwenLLMVerifier
from scripts.build_verifier_benchmark import build_benchmark_claims


class TestVerifierBenchmark(unittest.TestCase):

    def test_build_benchmark_claims(self):
        records = [
            EvidenceRecord(
                dataset_citation_key="Section 302 in The Indian Penal Code, 1860",
                act="The Indian Penal Code, 1860",
                provision_type="Section",
                provision_number="302",
                subsection=None,
                canonical_text="Whoever commits murder shall be punished with death, or imprisonment for life, and shall also be liable to fine.",
                source_url="http://example.com",
                audit_verdict="VERIFIED_EXACT",
                act_norm="indian penal code 1860",
            )
        ]

        items = build_benchmark_claims(records, seed=42)
        self.assertEqual(len(items), 3)

        labels = [item["expected_label"] for item in items]
        self.assertIn("ENTAILED", labels)
        self.assertIn("CONTRADICTED", labels)
        self.assertIn("NOT_ENOUGH_INFORMATION", labels)

        contradicted_item = [item for item in items if item["expected_label"] == "CONTRADICTED"][0]
        self.assertIn("exempt from punishment", contradicted_item["hypothesis"])

    def test_qwen_llm_verifier_parsing(self):
        mock_gen = MagicMock()
        mock_gen.is_loaded.return_value = True

        mock_tokenizer = MagicMock()
        mock_tokenizer.pad_token_id = 0
        mock_tokenizer.eos_token_id = 0
        mock_tokenizer.padding_side = "right"
        mock_tokenizer.apply_chat_template.return_value = "Prompt"
        mock_tokenizer.side_effect = lambda *args, **kwargs: {
            "input_ids": MagicMock(to=lambda dev: MagicMock(shape=[1, 5])),
            "attention_mask": MagicMock(to=lambda dev: MagicMock(shape=[1, 5])),
        }
        mock_gen._tokenizer = mock_tokenizer

        mock_model = MagicMock()
        mock_model.generate.return_value = [[0, 1, 2, 3, 4, 5]]
        mock_gen._model = mock_model

        # Test ENTAILED response
        mock_tokenizer.decode.return_value = "ENTAILED: The claim is supported."
        verifier = QwenLLMVerifier(mock_gen)
        res = verifier.verify("Premise", "Hypothesis")
        self.assertEqual(res.label, ENTAILED)

        # Test CONTRADICTED response
        mock_tokenizer.decode.return_value = "CONTRADICTED"
        res = verifier.verify("Premise", "Hypothesis")
        self.assertEqual(res.label, CONTRADICTED)

        # Test NOT_ENOUGH_INFORMATION response
        mock_tokenizer.decode.return_value = "NOT_ENOUGH_INFORMATION"
        res = verifier.verify("Premise", "Hypothesis")
        self.assertEqual(res.label, NOT_ENOUGH_INFORMATION)


if __name__ == "__main__":
    unittest.main()
