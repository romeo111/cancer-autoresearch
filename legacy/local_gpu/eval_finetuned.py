#!/usr/bin/env python3
"""
eval_finetuned.py — Evaluate fine-tuned model vs. base model using evaluate.py

Runs the fine-tuned model on test cases, saves JSON reports,
scores them with evaluate.py, and compares against baseline.

Usage:
    # Evaluate LoRA adapter (Unsloth)
    python eval_finetuned.py --model models/cancer_treatment_lora

    # Evaluate GGUF via Ollama (after: ollama create cancer-treatment -f Modelfile)
    python eval_finetuned.py --ollama-model cancer-treatment

    # Compare fine-tuned vs base on held-out test set
    python eval_finetuned.py --model models/cancer_treatment_lora \\
                              --test finetune_data/test_chatml.jsonl \\
                              --baseline-model llama3.2:3b
"""

import argparse
import json
import os
import sys
import io
import glob
import urllib.request
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

OLLAMA_BASE = "http://localhost:11434"


def ollama_generate(prompt: str, model: str, system: str = "", timeout: int = 300) -> str:
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload = json.dumps({
        "model":   model,
        "messages": messages,
        "stream":  False,
        "options": {"temperature": 0.1, "num_predict": 8192},
    }).encode()
    req = urllib.request.Request(
        f"{OLLAMA_BASE}/api/chat",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
            return data.get("message", {}).get("content", "")
    except Exception as e:
        return f"ERROR: {e}"


def unsloth_generate(prompt: str, system: str, model_path: str, max_new_tokens: int = 4096) -> str:
    try:
        from unsloth import FastLanguageModel
        import torch
    except ImportError:
        return "ERROR: pip install unsloth"

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name  = model_path,
        max_seq_length = 4096,
        load_in_4bit   = True,
    )
    FastLanguageModel.for_inference(model)

    messages = [
        {"role": "system",    "content": system},
        {"role": "user",      "content": prompt},
    ]
    inputs = tokenizer.apply_chat_template(
        messages, tokenize=True, add_generation_prompt=True, return_tensors="pt"
    ).to("cuda")

    with torch.no_grad():
        outputs = model.generate(
            input_ids      = inputs,
            max_new_tokens = max_new_tokens,
            temperature    = 0.1,
            do_sample      = True,
        )
    return tokenizer.decode(outputs[0][inputs.shape[1]:], skip_special_tokens=True)


def extract_json(text: str) -> dict:
    """Try to parse JSON from model output."""
    import re
    # Try direct parse
    try:
        return json.loads(text)
    except Exception:
        pass
    # Try extracting JSON block
    match = re.search(r'\{[\s\S]+\}', text)
    if match:
        try:
            return json.loads(match.group())
        except Exception:
            pass
    return {}


def build_case_prompt(case: dict) -> tuple:
    """Build system + user prompt from a test case dict."""
    from prepare_finetune_data import SYSTEM_PROMPT
    system = SYSTEM_PROMPT + "\n\nReturn JSON with only the treatments array, sorted by composite_rating descending."
    user = (
        f"Cancer type: {case.get('cancer_type', '')}\n"
        f"Stage: {case.get('stage', '')}\n"
        f"Molecular profile: {', '.join(case.get('molecular_profile', []))}"
    )
    return system, user


def evaluate_output(generated: dict, report_path: str) -> dict:
    """Save generated treatments to a report skeleton and score it."""
    sys.path.insert(0, os.path.dirname(__file__) or ".")
    import evaluate as ev

    # Build minimal report skeleton for scoring
    report = {
        "report_metadata": {
            "generated_date":    datetime.now().isoformat()[:10],
            "cancer_type":       "evaluated",
            "stage":             "evaluated",
            "molecular_profile": [],
        },
        "treatments":             generated.get("treatments", []),
        "clinical_trials":        [],
        "combination_strategies": [],
        "supportive_care":        [],
        "sources":                [],
    }

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    result = ev.evaluate_report(report)
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate fine-tuned cancer treatment model vs. baseline"
    )
    parser.add_argument("--model",           default=None,
                        help="LoRA adapter path (Unsloth)")
    parser.add_argument("--ollama-model",    default=None,
                        help="Ollama model name (after ollama create)")
    parser.add_argument("--baseline-model",  default="llama3.2:3b",
                        help="Baseline Ollama model to compare against")
    parser.add_argument("--test",            default="finetune_data/test_chatml.jsonl",
                        help="Test JSONL (ChatML format)")
    parser.add_argument("--output-dir",      default="eval_results",
                        help="Where to save generated reports")
    parser.add_argument("--limit",           type=int, default=0,
                        help="Max test cases to evaluate (0 = all)")
    parser.add_argument("--no-baseline",     action="store_true",
                        help="Skip baseline comparison")
    args = parser.parse_args()

    if not args.model and not args.ollama_model:
        print("ERROR: Provide --model (LoRA path) or --ollama-model (Ollama name)")
        sys.exit(1)

    sys.path.insert(0, os.path.dirname(__file__) or ".")
    from prepare_finetune_data import SYSTEM_PROMPT

    # Load test data
    if not os.path.exists(args.test):
        print(f"Test file not found: {args.test}")
        print("Run: python prepare_finetune_data.py first")
        sys.exit(1)

    test_examples = []
    with open(args.test, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                test_examples.append(json.loads(line))

    if args.limit:
        test_examples = test_examples[:args.limit]

    print(f"Evaluating {len(test_examples)} test cases")
    os.makedirs(args.output_dir, exist_ok=True)

    finetuned_scores = []
    baseline_scores  = []

    for i, ex in enumerate(test_examples):
        messages = ex.get("messages", [])
        system  = next((m["content"] for m in messages if m["role"] == "system"), SYSTEM_PROMPT)
        user    = next((m["content"] for m in messages if m["role"] == "user"),   "")
        case_id = f"test_{i:03d}"

        print(f"\n[{i+1}/{len(test_examples)}] {user[:80]}")

        # Fine-tuned model
        print("  Fine-tuned: ", end="", flush=True)
        if args.model:
            ft_text = unsloth_generate(user, system, args.model)
        else:
            ft_text = ollama_generate(user, args.ollama_model, system)

        ft_json  = extract_json(ft_text)
        ft_path  = os.path.join(args.output_dir, f"{case_id}_finetuned.json")
        ft_result = evaluate_output(ft_json, ft_path)
        ft_score = ft_result["quality_score"]
        finetuned_scores.append(ft_score)
        print(f"{ft_score}/100")

        # Baseline
        if not args.no_baseline:
            print(f"  Baseline ({args.baseline_model}): ", end="", flush=True)
            bl_text  = ollama_generate(user, args.baseline_model, system)
            bl_json  = extract_json(bl_text)
            bl_path  = os.path.join(args.output_dir, f"{case_id}_baseline.json")
            bl_result = evaluate_output(bl_json, bl_path)
            bl_score  = bl_result["quality_score"]
            baseline_scores.append(bl_score)
            delta = ft_score - bl_score
            print(f"{bl_score}/100  (delta: {'+' if delta>=0 else ''}{delta})")

    # Summary
    print(f"\n{'='*60}")
    print(f"EVALUATION RESULTS ({len(test_examples)} test cases)")
    print(f"{'='*60}")
    ft_mean = sum(finetuned_scores) / len(finetuned_scores) if finetuned_scores else 0
    print(f"Fine-tuned model:  {ft_mean:.1f}/100  (min={min(finetuned_scores)}  max={max(finetuned_scores)})")
    if baseline_scores:
        bl_mean = sum(baseline_scores) / len(baseline_scores)
        delta   = ft_mean - bl_mean
        print(f"Baseline model:    {bl_mean:.1f}/100  (min={min(baseline_scores)}  max={max(baseline_scores)})")
        print(f"Fine-tune gain:    {'+' if delta>=0 else ''}{delta:.1f} pts")
        wins = sum(1 for f, b in zip(finetuned_scores, baseline_scores) if f > b)
        print(f"Win rate:          {wins}/{len(finetuned_scores)} cases fine-tuned > baseline")

    results_path = os.path.join(args.output_dir, "comparison.json")
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump({
            "evaluated_at":     datetime.now().isoformat(),
            "finetuned_model":  args.model or args.ollama_model,
            "baseline_model":   args.baseline_model,
            "finetuned_mean":   ft_mean,
            "baseline_mean":    sum(baseline_scores)/len(baseline_scores) if baseline_scores else None,
            "finetuned_scores": finetuned_scores,
            "baseline_scores":  baseline_scores,
        }, f, indent=2)
    print(f"\nDetailed results: {results_path}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
