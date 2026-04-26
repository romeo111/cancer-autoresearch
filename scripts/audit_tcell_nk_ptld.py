"""Per-disease audit for T-cell, NK-cell, PTLD entries in OpenOnco KB.

Counts indications (1L standard / 1L alt / 2L+ / maintenance), algorithms (1L / 2L+),
patient fixtures, and whether reviewer_signoffs == 0. Outputs a markdown table.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
KB = ROOT / "knowledge_base" / "hosted" / "content"
EXAMPLES = ROOT / "examples"

DISEASES = [
    ("AITL", "DIS-AITL", "aitl"),
    ("ALCL", "DIS-ALCL", "alcl"),
    ("PTCL-NOS", "DIS-PTCL-NOS", "ptcl"),
    ("EATL", "DIS-EATL", "eatl"),
    ("HSTCL", "DIS-HSTCL", "hstcl"),
    ("T-LBL", "DIS-T-ALL", "t_all"),  # T-LBL/T-ALL share entity in this KB
    ("T-PLL", "DIS-T-PLL", "t_pll"),
    ("MF-Sezary", "DIS-MF-SEZARY", "mf_"),  # mf_, sezary tags
    ("ATLL", "DIS-ATLL", "atll"),
    ("NK/T-nasal", "DIS-NK-T-NASAL", "nk_t_nasal"),
    ("PTLD", "DIS-PTLD", "ptld"),
]

def load_yaml(p: Path):
    with open(p, encoding="utf-8") as f:
        return yaml.safe_load(f)

def list_yaml(d: Path):
    return sorted(d.glob("*.yaml"))

def audit():
    inds = {p.name: load_yaml(p) for p in list_yaml(KB / "indications")}
    algos = {p.name: load_yaml(p) for p in list_yaml(KB / "algorithms")}
    fixtures = list(EXAMPLES.glob("patient_*.json"))

    rows = []
    for label, dis_id, slug in DISEASES:
        d_inds = [(n, y) for n, y in inds.items()
                  if y and (y.get("applicable_to") or {}).get("disease_id") == dis_id]
        l1 = [(n, y) for n, y in d_inds if (y["applicable_to"].get("line_of_therapy") == 1)]
        l2plus = [(n, y) for n, y in d_inds if (y["applicable_to"].get("line_of_therapy") and y["applicable_to"]["line_of_therapy"] >= 2)]
        std = [n for n, y in l1 if (y.get("plan_track") == "standard")]
        alt = [n for n, y in l1 if (y.get("plan_track") == "aggressive")]
        # maintenance heuristic
        maint = [n for n, y in d_inds if "maint" in n.lower() or "consolid" in n.lower()
                 or (y.get("notes") or "").lower().__contains__("maintenance")]

        d_algos = [n for n, y in algos.items()
                   if y and y.get("applicable_to_disease") == dis_id]
        algo1 = [n for n in d_algos if "1l" in n.lower()]
        algo2 = [n for n in d_algos if "2l" in n.lower()]

        # fixtures
        slug_re = re.compile(rf"patient_{re.escape(slug)}", re.I)
        d_fixtures = [p.name for p in fixtures if slug_re.search(p.name)]
        # MF/Sezary special
        if label == "MF-Sezary":
            d_fixtures = [p.name for p in fixtures if re.search(r"patient_(mf_|sezary)", p.name, re.I)]
        if label == "PTCL-NOS":
            d_fixtures = [p.name for p in fixtures if re.search(r"patient_ptcl_", p.name, re.I)]
        if label == "T-LBL":
            d_fixtures = [p.name for p in fixtures if re.search(r"patient_(t_lbl|t_all)", p.name, re.I)]

        rows.append({
            "disease": label,
            "indications_total": len(d_inds),
            "1L_std": len(std),
            "1L_alt": len(alt),
            "2L+": len(l2plus),
            "maint": len(maint),
            "algo_1L": "yes" if algo1 else "NO",
            "algo_2L+": "yes" if algo2 else "NO",
            "fixtures": len(d_fixtures),
            "fixture_files": d_fixtures,
            "ind_files": [n for n, _ in d_inds],
        })
    return rows

def md_table(rows):
    headers = ["Disease", "Total ind", "1L std", "1L alt", "2L+", "Maint/Cons", "Algo 1L", "Algo 2L+", "Fixtures"]
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    for r in rows:
        lines.append("| " + " | ".join([
            r["disease"], str(r["indications_total"]), str(r["1L_std"]),
            str(r["1L_alt"]), str(r["2L+"]), str(r["maint"]),
            r["algo_1L"], r["algo_2L+"], str(r["fixtures"]),
        ]) + " |")
    return "\n".join(lines)

if __name__ == "__main__":
    rows = audit()
    print(md_table(rows))
    print("\n--- detail ---")
    for r in rows:
        print(f"\n{r['disease']}:")
        print(f"  indications: {r['ind_files']}")
        print(f"  fixtures: {r['fixture_files']}")
