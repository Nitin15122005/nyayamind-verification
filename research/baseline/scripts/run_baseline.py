"""
Clean CLI wrapper around the published RhetoricLLaMA inference logic from
baseline/LegalSeg/code/RhetoricLLaMA/inference.py.

Original file is left untouched. The only behavioral changes made here are:
  - Data path is passed in via --input-csv instead of the hardcoded
    "../../data/RhetoricLLaMA/test.csv" (which also had a case mismatch
    against the repo's actual "Data/" directory).
  - The LoRA adapter is loaded with AutoPeftModelForCausalLM (PEFT), instead
    of the original script's AutoModelForCausalLM.from_pretrained() call on
    an adapter-only checkpoint directory, which cannot resolve base model
    weights on its own.
  - The HF access token is read from the HF_TOKEN environment variable
    instead of being hardcoded in source.
  - Output path is passed in via --output-csv instead of the hardcoded
    "pred_41-50.csv".

The prompt template, the 0-6 label task definition, the preprocessing
(last-1000-whitespace-token truncation), the tokenizer call, and the
generation settings (max_new_tokens=100, greedy defaults, 4-bit NF4
double-quant BitsAndBytesConfig) are preserved exactly as in the original
script. The raw decoded generation is stored unmodified (no re-mapping or
constraining of the label text), matching the original script's behavior.
"""

import argparse
import os

import pandas as pd
import torch
from peft import AutoPeftModelForCausalLM
from transformers import AutoTokenizer, BitsAndBytesConfig
from tqdm import tqdm


def preprocess_case(text):
    max_tokens = 1000
    tokens = text.split(' ')
    num_tokens_to_extract = min(max_tokens, len(tokens))
    text1 = ' '.join(tokens[-num_tokens_to_extract:len(tokens)])
    return text1


def create_prompt(case_pro):
    prompt = f""" ### Instructions:
    Analyze the given legal sentence and predict its rhetorical role as a number: None-0, Facts-1, Issue-2, Arguments of Petitioner-3, Arguments of Respondent-4, Reasoning-5, Decision-6.
    Note: The response must only contain a number between 0 and 6 representing the label of sentence. \

  ### Input:
  case_proceeding: <{case_pro}>

  ### Response:
  """
    return prompt


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run RhetoricLLaMA (LoRA over Llama-2-7b-chat-hf) baseline inference."
    )
    parser.add_argument(
        "--input-csv",
        required=True,
        help='Path to test CSV with a "Text" column (e.g. Data/RhetoricLLaMA/test.csv or Data/test.csv).',
    )
    parser.add_argument(
        "--output-csv",
        required=True,
        help='Path to write predictions CSV (adds a "llama_p" column).',
    )
    parser.add_argument(
        "--model-id",
        default=os.path.join("baseline", "LegalSeg", "saved_models", "RhetoricLLaMA"),
        help="Path to the RhetoricLLaMA LoRA adapter directory (adapter_config.json, adapter_model.safetensors, tokenizer files).",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    hf_token = os.environ.get("HF_TOKEN")
    if not hf_token:
        raise RuntimeError(
            "HF_TOKEN environment variable is not set. Export a valid Hugging Face "
            "access token with access to meta-llama/Llama-2-7b-chat-hf before running."
        )

    df = pd.read_csv(args.input_csv)

    for i, row in tqdm(df.iterrows()):
        input_text = row['Text']
        input_text = preprocess_case(input_text)
        df.at[i, 'Text'] = input_text

    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
    )

    # AutoPeftModelForCausalLM resolves base_model_name_or_path from the
    # adapter's adapter_config.json and loads base weights + LoRA adapter.
    model = AutoPeftModelForCausalLM.from_pretrained(
        args.model_id,
        quantization_config=bnb_config,
        device_map="auto",
        token=hf_token,
    )
    tokenizer = AutoTokenizer.from_pretrained(args.model_id)

    df["llama_p"] = ""
    for i, row in tqdm(df.iterrows(), total=len(df)):
        case_pro = row["Text"]
        prompt = create_prompt(case_pro)
        input_ids = tokenizer(prompt, return_tensors='pt', truncation=True).input_ids.cuda()
        outputs = model.generate(input_ids=input_ids, max_new_tokens=100)
        output = tokenizer.batch_decode(outputs.detach().cpu().numpy(), skip_special_tokens=True)[0][len(prompt):]
        df.at[i, "llama_p"] = output

    df.to_csv(args.output_csv, index=False)


if __name__ == "__main__":
    main()
