#!/usr/bin/env python3
"""
finetune.py — QLoRA fine-tuning on RTX 5050 using Unsloth

Fine-tunes llama3.2:3b-instruct (or any supported model) to:
  - Output valid JSON in our exact report schema
  - Apply correct rating anchors (Phase 3 = 8-10, Phase 2 = 5-7)
  - Include mandatory fields (intent, HR, p-value, sample_size)
  - Sort treatments by composite_rating correctly

Requirements:
    pip install "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git"
    pip install trl peft accelerate bitsandbytes

Hardware targets (RTX 5050 with 8 GB VRAM):
    llama3.2:3b  — fits comfortably, ~4.5 GB VRAM during training
    phi3:mini    — fits, ~5.5 GB VRAM during training
    mistral:7b   — too large for 8 GB (needs 16+ GB)

Usage:
    # Basic run (auto-selects best settings for your GPU)
    python finetune.py

    # Custom paths
    python finetune.py --train finetune_data/train_chatml.jsonl \\
                       --val   finetune_data/val_chatml.jsonl \\
                       --model unsloth/Llama-3.2-3B-Instruct \\
                       --output models/cancer_llama3_v1

    # Dry run — verify data loading and model init without training
    python finetune.py --dry-run

    # After training, export to GGUF for Ollama:
    python finetune.py --export-gguf --model-path models/cancer_llama3_v1
"""

import argparse
import json
import os
import sys

# ── Config ────────────────────────────────────────────────────────────────────

DEFAULTS = {
    # Model — Unsloth's 4-bit pre-quantized variants load faster
    "model":        "unsloth/Llama-3.2-3B-Instruct-bnb-4bit",

    # LoRA rank: higher = more capacity, more VRAM
    # 16 = good for format learning; 64 = better for domain adaptation
    "lora_r":       16,
    "lora_alpha":   32,         # typically 2x lora_r
    "lora_dropout": 0.0,        # 0.0 = recommended by Unsloth

    # LoRA target modules (attention + FFN projections)
    "lora_targets": ["q_proj", "k_proj", "v_proj", "o_proj",
                     "gate_proj", "up_proj", "down_proj"],

    # Training hyperparams — tuned for small dataset (130 examples)
    "epochs":        3,          # 3-5 for small dataset; more = overfit risk
    "batch_size":    2,          # per-device; 2 safe for 8 GB VRAM
    "grad_accum":    4,          # effective batch = 2*4 = 8
    "lr":            2e-4,       # standard for LoRA
    "warmup_steps":  10,
    "max_seq_len":   4096,       # treatments JSON can be long
    "weight_decay":  0.01,
    "scheduler":     "cosine",

    # Context packing (Unsloth) — packs multiple short examples into one sequence
    "packing":       True,

    # Output
    "output":       "models/cancer_treatment_lora",
    "save_steps":    50,
    "eval_steps":    25,
    "logging_steps": 5,
}


# ── GGUF Export ───────────────────────────────────────────────────────────────

def export_to_gguf(model_path: str, quantization: str = "q4_k_m"):
    """Export fine-tuned model to GGUF format for Ollama."""
    try:
        from unsloth import FastLanguageModel
    except ImportError:
        print("ERROR: pip install unsloth")
        return

    print(f"Loading model from {model_path}...")
    model, tokenizer = FastLanguageModel.from_pretrained(model_path)

    gguf_path = model_path.rstrip("/") + f"_{quantization}.gguf"
    print(f"Exporting to {gguf_path} ({quantization})...")
    model.save_pretrained_gguf(gguf_path, tokenizer, quantization_method=quantization)
    print(f"Done: {gguf_path}")

    # Write Modelfile for ollama
    modelfile = f"""FROM {gguf_path}

SYSTEM \"\"\"You are an expert oncology research assistant. Given a patient cancer case, produce a ranked list of evidence-based treatments in valid JSON format. Apply the rating system exactly: evidence_level (Phase 3 RCT=8-10, Phase 2=5-7, Phase 1=2-4), survival_benefit based on OS delta, composite = ev*0.30 + surv*0.30 + access*0.15 + safety*0.15 + biomarker*0.10.\"\"\"

PARAMETER temperature 0.1
PARAMETER top_p 0.9
PARAMETER num_predict 8192
"""
    modelfile_path = gguf_path.replace(".gguf", ".Modelfile")
    with open(modelfile_path, "w") as f:
        f.write(modelfile)
    print(f"\nModelfile: {modelfile_path}")
    print(f"\nTo load in Ollama:")
    print(f"  ollama create cancer-treatment -f {modelfile_path}")
    print(f"  ollama run cancer-treatment")


# ── Training ──────────────────────────────────────────────────────────────────

def load_dataset_from_jsonl(path: str) -> "list[dict]":
    """Load ChatML format JSONL."""
    examples = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                examples.append(json.loads(line))
    return examples


def format_chatml(example: dict, tokenizer) -> dict:
    """Apply ChatML template using tokenizer's chat template."""
    messages = example.get("messages", [])
    text = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=False,
    )
    return {"text": text}


def main():
    parser = argparse.ArgumentParser(
        description="QLoRA fine-tuning for cancer treatment ranking (RTX 5050 optimized)"
    )
    parser.add_argument("--train",     default="finetune_data/train_chatml.jsonl")
    parser.add_argument("--val",       default="finetune_data/val_chatml.jsonl")
    parser.add_argument("--model",     default=DEFAULTS["model"])
    parser.add_argument("--output",    default=DEFAULTS["output"])
    parser.add_argument("--epochs",    type=int,   default=DEFAULTS["epochs"])
    parser.add_argument("--lora-r",    type=int,   default=DEFAULTS["lora_r"])
    parser.add_argument("--lr",        type=float, default=DEFAULTS["lr"])
    parser.add_argument("--batch",     type=int,   default=DEFAULTS["batch_size"])
    parser.add_argument("--max-seq",   type=int,   default=DEFAULTS["max_seq_len"])
    parser.add_argument("--dry-run",   action="store_true",
                        help="Load model + data, print config, exit without training")
    parser.add_argument("--export-gguf", action="store_true",
                        help="Export trained model to GGUF for Ollama (skips training)")
    parser.add_argument("--model-path", default=None,
                        help="Path to trained LoRA adapter (for --export-gguf)")
    parser.add_argument("--quant",     default="q4_k_m",
                        choices=["q4_k_m", "q5_k_m", "q8_0", "f16"],
                        help="GGUF quantization level (default: q4_k_m)")
    args = parser.parse_args()

    # Export-only mode
    if args.export_gguf:
        path = args.model_path or args.output
        export_to_gguf(path, args.quant)
        return

    # ── Load Unsloth ──────────────────────────────────────────────────────────
    try:
        from unsloth import FastLanguageModel
        import torch
    except ImportError:
        print("ERROR: Unsloth not installed.")
        print("Install with:")
        print("  pip install \"unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git\"")
        print("  pip install trl peft accelerate bitsandbytes")
        print()
        print("Or see: https://github.com/unslothai/unsloth#installation")
        sys.exit(1)

    try:
        from trl import SFTTrainer
        from transformers import TrainingArguments
        from datasets import Dataset
    except ImportError as e:
        print(f"ERROR: Missing dependency: {e}")
        print("pip install trl transformers datasets")
        sys.exit(1)

    print(f"GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU (slow!)'}")
    print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB" if torch.cuda.is_available() else "")
    print(f"Model: {args.model}")
    print(f"LoRA rank: {args.lora_r}  |  LR: {args.lr}  |  Epochs: {args.epochs}")
    print()

    # ── Load model ────────────────────────────────────────────────────────────
    print("Loading base model (4-bit)...")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name     = args.model,
        max_seq_length = args.max_seq,
        dtype          = None,        # auto-detect (bfloat16 on Ampere+)
        load_in_4bit   = True,
    )
    print(f"Model loaded. Attaching LoRA adapters (r={args.lora_r})...")

    model = FastLanguageModel.get_peft_model(
        model,
        r                       = args.lora_r,
        target_modules          = DEFAULTS["lora_targets"],
        lora_alpha              = args.lora_r * 2,
        lora_dropout            = DEFAULTS["lora_dropout"],
        bias                    = "none",
        use_gradient_checkpointing = "unsloth",   # saves ~30% VRAM
        random_state            = 42,
    )
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total     = sum(p.numel() for p in model.parameters())
    print(f"Trainable params: {trainable:,} / {total:,} ({100*trainable/total:.2f}%)")

    # ── Load data ─────────────────────────────────────────────────────────────
    print(f"\nLoading training data from {args.train}...")
    train_raw = load_dataset_from_jsonl(args.train)
    val_raw   = load_dataset_from_jsonl(args.val) if os.path.exists(args.val) else []

    # Apply chat template
    train_formatted = [format_chatml(ex, tokenizer) for ex in train_raw]
    val_formatted   = [format_chatml(ex, tokenizer) for ex in val_raw]

    train_ds = Dataset.from_list(train_formatted)
    val_ds   = Dataset.from_list(val_formatted) if val_formatted else None

    print(f"Train examples: {len(train_ds)}")
    if val_ds:
        print(f"Val examples:   {len(val_ds)}")

    # Sample preview
    print(f"\nSample (first 400 chars):")
    print(train_formatted[0]["text"][:400])
    print("...")

    if args.dry_run:
        print("\n[dry-run] Config verified. Exiting without training.")
        return

    # ── Train ─────────────────────────────────────────────────────────────────
    print(f"\nStarting training -> {args.output}")
    trainer = SFTTrainer(
        model     = model,
        tokenizer = tokenizer,
        train_dataset = train_ds,
        eval_dataset  = val_ds,
        dataset_text_field = "text",
        max_seq_length     = args.max_seq,
        dataset_num_proc   = 2,
        packing            = DEFAULTS["packing"],
        args = TrainingArguments(
            per_device_train_batch_size = args.batch,
            gradient_accumulation_steps = DEFAULTS["grad_accum"],
            warmup_steps                = DEFAULTS["warmup_steps"],
            num_train_epochs            = args.epochs,
            learning_rate               = args.lr,
            fp16                        = not torch.cuda.is_bf16_supported(),
            bf16                        = torch.cuda.is_bf16_supported(),
            logging_steps               = DEFAULTS["logging_steps"],
            optim                       = "adamw_8bit",   # memory efficient
            weight_decay                = DEFAULTS["weight_decay"],
            lr_scheduler_type           = DEFAULTS["scheduler"],
            seed                        = 42,
            output_dir                  = args.output,
            save_steps                  = DEFAULTS["save_steps"],
            evaluation_strategy         = "steps" if val_ds else "no",
            eval_steps                  = DEFAULTS["eval_steps"] if val_ds else None,
            load_best_model_at_end      = bool(val_ds),
            report_to                   = "none",
        ),
    )

    # VRAM usage before training
    if torch.cuda.is_available():
        used = torch.cuda.memory_allocated() / 1e9
        total_vram = torch.cuda.get_device_properties(0).total_memory / 1e9
        print(f"VRAM before training: {used:.1f}/{total_vram:.1f} GB")

    trainer_stats = trainer.train()

    print(f"\nTraining complete!")
    print(f"  Runtime:      {trainer_stats.metrics['train_runtime']:.0f}s")
    print(f"  Loss:         {trainer_stats.metrics['train_loss']:.4f}")
    print(f"  Samples/sec:  {trainer_stats.metrics['train_samples_per_second']:.1f}")

    # Save LoRA adapter
    print(f"\nSaving LoRA adapter to {args.output}...")
    model.save_pretrained(args.output)
    tokenizer.save_pretrained(args.output)
    print("Saved.")

    # Export to GGUF automatically
    print(f"\nExporting to GGUF for Ollama ({args.quant})...")
    export_to_gguf(args.output, args.quant)

    print(f"\n{'='*60}")
    print("FINE-TUNING COMPLETE")
    print(f"LoRA adapter:  {args.output}/")
    print(f"GGUF model:    {args.output}_{args.quant}.gguf")
    print()
    print("To evaluate vs. base model:")
    print(f"  python eval_finetuned.py --model {args.output}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
