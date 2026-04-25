"""CIViC loader — TSV → YAML.

CIViC publishes nightly bulk TSV dumps at
https://civicdb.org/downloads/nightly/nightly-ClinicalEvidenceSummaries.tsv

CC0 licence — we can host fully (SOURCE_INGESTION_SPEC §2.5).

Output: knowledge_base/hosted/civic/<date>/evidence.yaml
"""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import yaml


def _split_molecular_profile(mp: str) -> tuple[str | None, str | None]:
    """CIViC `molecular_profile` is typically 'GENE VARIANT' — split conservatively."""
    if not mp:
        return None, None
    parts = mp.strip().split(None, 1)
    if len(parts) == 1:
        return parts[0], None
    return parts[0], parts[1]


def parse_civic_tsv(path: Path) -> list[dict]:
    """Parse CIViC nightly ClinicalEvidenceSummaries TSV.

    Column names per actual TSV header (verified 2026-04-25): molecular_profile,
    disease, doid, therapies, evidence_type, evidence_direction, evidence_level,
    significance, citation_id, source_type, evidence_id, rating, evidence_status, ...
    """
    entries: list[dict] = []
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            gene, variant = _split_molecular_profile(row.get("molecular_profile") or "")
            therapies = row.get("therapies") or ""
            # Therapies separated by comma OR semicolon depending on row
            drugs = [
                t.strip() for t in therapies.replace(";", ",").split(",") if t.strip()
            ]
            citation_id = (row.get("citation_id") or "").strip() or None
            source_type = (row.get("source_type") or "").strip()
            entries.append({
                "id": row.get("evidence_id") or row.get("id"),
                "molecular_profile": row.get("molecular_profile"),
                "gene": gene,
                "variant": variant,
                "disease": row.get("disease"),
                "doid": row.get("doid"),
                "therapies": drugs,
                "therapy_interaction_type": row.get("therapy_interaction_type") or None,
                "evidence_level": row.get("evidence_level"),
                "evidence_type": row.get("evidence_type"),
                "evidence_direction": row.get("evidence_direction"),
                "significance": row.get("significance"),
                "citation_id": citation_id,
                "citation_source_type": source_type or None,
                "pmid": citation_id if source_type.lower() == "pubmed" else None,
                "rating": row.get("rating"),
                "evidence_status": row.get("evidence_status"),
                "civic_url": row.get("evidence_civic_url"),
            })
    return entries


def load_civic(tsv_path: Path, out_root: Path, snapshot_date: str | None = None) -> Path:
    snapshot_date = snapshot_date or date.today().isoformat()
    entries = parse_civic_tsv(tsv_path)

    out_dir = out_root / snapshot_date
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "evidence.yaml"
    payload = {
        "source_id": "SRC-CIVIC",
        "snapshot_date": snapshot_date,
        "source_url": "https://civicdb.org/downloads/nightly/",
        "license": "CC0-1.0",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "evidence_items": entries,
    }
    out_path.write_text(
        yaml.safe_dump(payload, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    return out_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Load a CIViC nightly TSV into YAML.")
    parser.add_argument("tsv", type=Path)
    parser.add_argument(
        "--out-root",
        type=Path,
        default=Path("knowledge_base/hosted/civic"),
    )
    parser.add_argument("--date", help="YYYY-MM-DD snapshot date (default: today)")
    args = parser.parse_args()

    if not args.tsv.is_file():
        print(f"ERROR: TSV not found: {args.tsv}", file=sys.stderr)
        return 2

    out = load_civic(args.tsv, args.out_root, snapshot_date=args.date)
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
