#!/usr/bin/env python3
"""
prepare_finetune_data.py — Convert research reports into fine-tuning training examples

Produces three datasets:
  1. finetune_data/train.jsonl   — 80% of reports (instruction fine-tuning format)
  2. finetune_data/val.jsonl     — 10% (held out for loss monitoring)
  3. finetune_data/test.jsonl    — 10% (evaluate.py scoring after training)

Output format: Alpaca instruction format (works with Unsloth, Axolotl, LLaMA-Factory)

Each example = one treatment ranking task:
  instruction: system prompt with schema + rating rules
  input:       patient case (cancer_type, stage, markers, context)
  output:      treatments array JSON

Usage:
    python prepare_finetune_data.py
    python prepare_finetune_data.py --reports experiment_reports --augment
    python prepare_finetune_data.py --task full_report  # includes all sections
"""

import argparse
import glob
import json
import os
import random
import sys

SYSTEM_PROMPT = """You are an expert oncology research assistant. Given a patient cancer case, produce a ranked list of evidence-based treatments in valid JSON format.

RATING SYSTEM (composite = ev*0.30 + surv*0.30 + access*0.15 + safety*0.15 + biomarker*0.10):

Evidence Level (1-10):
- 10: Phase 3 RCT, N>=500, top journal
- 7-8: Phase 3 RCT, N<500 OR Phase 2 strong results
- 5-6: Phase 2 moderate results
- 2-4: Phase 1 or case series
- 1: Case reports only

Survival Benefit (1-10):
- 10: >12 months OS improvement or curative
- 7-8: 6-12 months OS gain
- 5-6: 3-6 months OS gain
- 3-4: 1-3 months OS gain
- 1-2: <1 month or no survival data

Accessibility (1-10): 10=FDA+EMA approved, 7=trial available, 3-4=Phase 1 only
Safety Profile (1-10): 10=minimal toxicity, 7-8=manageable, 3-4=serious toxicity
Biomarker Match (1-10): 10=no biomarker required, 7-8=common marker, 3-4=rare marker

RULES:
- Sort treatments descending by composite_rating
- intent MUST be one of: curative, adjuvant, neoadjuvant, palliative, salvage, maintenance
- evidence_level >=8 requires a Phase 3 RCT cited
- survival_benefit >=7 requires OS or PFS data
- Include 8-15 treatments minimum
- Each treatment needs study_name, sample_size, hazard_ratio when available"""


def case_from_report(report: dict) -> dict:
    """Extract the patient case input from report metadata."""
    meta = report.get("report_metadata", {})
    return {
        "cancer_type":       meta.get("cancer_type", ""),
        "stage":             meta.get("stage", ""),
        "molecular_profile": meta.get("molecular_profile", []),
        "case_id":           meta.get("case_id", ""),
    }


def treatments_output(report: dict) -> str:
    """Extract treatments array as compact JSON string."""
    treatments = report.get("treatments", [])
    # Keep only the fields the model needs to generate
    clean = []
    for t in treatments:
        clean.append({
            "rank":             t.get("rank"),
            "name":             t.get("name"),
            "category":         t.get("category"),
            "intent":           t.get("intent"),
            "composite_rating": t.get("composite_rating"),
            "rating_breakdown": t.get("rating_breakdown"),
            "mechanism_of_action": t.get("mechanism_of_action"),
            "key_evidence":     t.get("key_evidence"),
            "biomarker_requirements": t.get("biomarker_requirements"),
            "ps_requirement":   t.get("ps_requirement"),
            "notable_side_effects": t.get("notable_side_effects"),
            "qol_impact":       t.get("qol_impact"),
            "availability":     t.get("availability"),
            "source_urls":      t.get("source_urls"),
        })
    return json.dumps({"treatments": clean}, indent=2, ensure_ascii=False)


def full_report_output(report: dict) -> str:
    """Full report output including trials, combos, supportive care."""
    out = {
        "treatments":             report.get("treatments", []),
        "clinical_trials":        report.get("clinical_trials", []),
        "combination_strategies": report.get("combination_strategies", []),
        "supportive_care":        report.get("supportive_care", []),
    }
    return json.dumps(out, indent=2, ensure_ascii=False)


def augment_case(case: dict, seed: int) -> dict:
    """Light augmentation: vary phrasing of molecular markers."""
    rng = random.Random(seed)
    aug = dict(case)
    mol = list(aug.get("molecular_profile", []))
    if mol and rng.random() < 0.5:
        rng.shuffle(mol)
        aug["molecular_profile"] = mol
    return aug


def build_example(case: dict, output: str, task: str) -> dict:
    """Build one Alpaca-format training example."""
    input_text = (
        f"Cancer type: {case['cancer_type']}\n"
        f"Stage: {case['stage']}\n"
        f"Molecular profile: {', '.join(case.get('molecular_profile', []))}\n"
        f"Case ID: {case.get('case_id', 'unknown')}"
    )
    instruction = SYSTEM_PROMPT
    if task == "full_report":
        instruction += "\n\nReturn the complete JSON with treatments, clinical_trials, combination_strategies, and supportive_care arrays."
    else:
        instruction += "\n\nReturn JSON with only the treatments array, sorted by composite_rating descending."

    return {
        "instruction": instruction,
        "input":       input_text,
        "output":      output,
    }


def build_chat_example(case: dict, output: str) -> dict:
    """Build ChatML format for models like llama3.2, phi3."""
    input_text = (
        f"Cancer type: {case['cancer_type']}\n"
        f"Stage: {case['stage']}\n"
        f"Molecular profile: {', '.join(case.get('molecular_profile', []))}"
    )
    return {
        "messages": [
            {"role": "system",    "content": SYSTEM_PROMPT},
            {"role": "user",      "content": input_text},
            {"role": "assistant", "content": output},
        ]
    }


def main():
    parser = argparse.ArgumentParser(
        description="Convert research reports to fine-tuning training data"
    )
    parser.add_argument("--reports",   default="experiment_reports",
                        help="Directory with *_report.json files")
    parser.add_argument("--output",    default="finetune_data",
                        help="Output directory (default: finetune_data)")
    parser.add_argument("--task",      choices=["treatments", "full_report"],
                        default="treatments",
                        help="What to train on (default: treatments array only)")
    parser.add_argument("--format",    choices=["alpaca", "chatml", "both"],
                        default="both",
                        help="Output format (default: both)")
    parser.add_argument("--augment",   action="store_true",
                        help="Generate 2x augmented copies of each example")
    parser.add_argument("--min-score", type=int, default=75,
                        help="Only include reports scoring >= this (default: 75)")
    parser.add_argument("--split",     type=str, default="80,10,10",
                        help="Train/val/test split pct (default: 80,10,10)")
    parser.add_argument("--seed",      type=int, default=42)
    args = parser.parse_args()

    random.seed(args.seed)
    splits = [int(x) for x in args.split.split(",")]
    assert len(splits) == 3 and sum(splits) == 100, "Splits must sum to 100"

    # Load evaluate.py for quality filtering
    sys.path.insert(0, os.path.dirname(__file__) or ".")
    import evaluate as ev_module
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    # Find reports
    report_files = sorted(glob.glob(os.path.join(args.reports, "*_report.json")))
    print(f"Found {len(report_files)} reports")

    # Load, score, filter
    examples = []
    skipped  = 0
    for path in report_files:
        try:
            with open(path, encoding="utf-8") as f:
                report = json.load(f)
        except Exception as e:
            print(f"  SKIP {path}: {e}")
            continue

        # Quality filter
        try:
            result = ev_module.evaluate_report(report)
            score  = result["quality_score"]
        except Exception:
            score = 0

        if score < args.min_score:
            skipped += 1
            continue

        case   = case_from_report(report)
        output = full_report_output(report) if args.task == "full_report" else treatments_output(report)

        if not case["cancer_type"] or not report.get("treatments"):
            skipped += 1
            continue

        examples.append((case, output, score, path))

        # Augmentation
        if args.augment:
            for i in range(2):
                aug_case = augment_case(case, seed=args.seed + hash(path) + i)
                examples.append((aug_case, output, score, path))

    print(f"Filtered in: {len(examples)} examples  (skipped {skipped} below {args.min_score}/100)")

    if not examples:
        print("No examples to write. Lower --min-score or check reports directory.")
        return

    # Shuffle and split
    random.shuffle(examples)
    n      = len(examples)
    n_train = int(n * splits[0] / 100)
    n_val   = int(n * splits[1] / 100)
    train_ex = examples[:n_train]
    val_ex   = examples[n_train:n_train+n_val]
    test_ex  = examples[n_train+n_val:]

    print(f"Split: train={len(train_ex)}  val={len(val_ex)}  test={len(test_ex)}")

    # Write files
    os.makedirs(args.output, exist_ok=True)

    def write_jsonl(data, path_base, fmt):
        path = f"{path_base}_{fmt}.jsonl"
        with open(path, "w", encoding="utf-8") as f:
            for case, output, score, src in data:
                if fmt in ("alpaca", "both_alpaca"):
                    rec = build_example(case, output, args.task)
                else:
                    rec = build_chat_example(case, output)
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        return path, len(data)

    for split_name, split_data in [("train", train_ex), ("val", val_ex), ("test", test_ex)]:
        base = os.path.join(args.output, split_name)
        if args.format in ("alpaca", "both"):
            p, n = write_jsonl(split_data, base, "alpaca")
            print(f"  {p}  ({n} examples)")
        if args.format in ("chatml", "both"):
            p, n = write_jsonl(split_data, base, "chatml")
            print(f"  {p}  ({n} examples)")

    # Write metadata
    meta = {
        "generated_at":     __import__("datetime").datetime.now().isoformat(),
        "source_reports":   args.reports,
        "task":             args.task,
        "min_score_filter": args.min_score,
        "augmented":        args.augment,
        "total_examples":   len(examples),
        "train":            len(train_ex),
        "val":              len(val_ex),
        "test":             len(test_ex),
        "format":           args.format,
        "system_prompt_chars": len(SYSTEM_PROMPT),
    }
    with open(os.path.join(args.output, "metadata.json"), "w") as f:
        json.dump(meta, f, indent=2)

    print(f"\nDone. Training data in: {args.output}/")
    print(f"\nNext step — fine-tune with Unsloth (recommended for RTX 5050):")
    print(f"  pip install unsloth")
    print(f"  python finetune.py --train {args.output}/train_chatml.jsonl --val {args.output}/val_chatml.jsonl")


if __name__ == "__main__":
    main()
