"""One-shot generator for BiomarkerActionability cells (drivers + heme scope).

Generates YAML files into knowledge_base/hosted/content/biomarker_actionability/.
Idempotent — overwrites existing files. Used by CSD-1-authoring-drivers agent
(2026-04-27). After running, validate with knowledge_base.validation.loader.
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "knowledge_base" / "hosted" / "content" / "biomarker_actionability"


def emit(cell_id: str, body: str) -> None:
    fname = "bma_" + cell_id.removeprefix("BMA-").lower().replace("-", "_") + ".yaml"
    (OUT / fname).write_text(body, encoding="utf-8")


def yaml_cell(
    *,
    cell_id: str,
    biomarker_id: str,
    variant_qualifier: str | None,
    disease_id: str,
    escat_tier: str,
    oncokb_level: str,
    summary: str,
    fda: list[str] | None = None,
    ema: list[str] | None = None,
    ukraine: list[str] | None = None,
    combos: list[str] | None = None,
    contraindicated: list[str] | None = None,
    sources: list[str],
    notes: str,
) -> str:
    fda = fda or []
    ema = ema or []
    ukraine = ukraine or []
    combos = combos or []
    contraindicated = contraindicated or []

    def _yaml_list(items: list[str], indent: int = 4) -> str:
        if not items:
            return " []"
        sp = " " * indent
        return "\n" + "\n".join(f"{sp}- {q(it)}" for it in items)

    def q(s: str) -> str:
        return '"' + s.replace('"', '\\"') + '"'

    vq_line = f'variant_qualifier: {q(variant_qualifier)}\n' if variant_qualifier else "variant_qualifier: null\n"

    lines = []
    lines.append(f"id: {cell_id}")
    lines.append(f"biomarker_id: {biomarker_id}")
    lines.append(vq_line.rstrip())
    lines.append(f"disease_id: {disease_id}")
    lines.append(f"escat_tier: {q(escat_tier)}")
    lines.append(f"oncokb_level: {q(oncokb_level)}")
    lines.append("evidence_summary: >")
    for ln in dedent(summary).strip().splitlines():
        lines.append("  " + ln.rstrip())
    lines.append("regulatory_approval:")
    lines.append(f"  fda:{_yaml_list(fda)}")
    lines.append(f"  ema:{_yaml_list(ema)}")
    lines.append(f"  ukraine:{_yaml_list(ukraine)}")
    lines.append(f"recommended_combinations:{_yaml_list(combos, indent=2)}")
    lines.append(f"contraindicated_monotherapy:{_yaml_list(contraindicated, indent=2)}")
    lines.append("primary_sources:")
    for s in sources:
        lines.append(f"  - {s}")
    lines.append('last_verified: "2026-04-27"')
    lines.append('oncokb_snapshot_version: "v3.20-2026-04"')
    lines.append("notes: >")
    for ln in dedent(notes).strip().splitlines():
        lines.append("  " + ln.rstrip())
    return "\n".join(lines) + "\n"


# ───────────────────────── KRAS ─────────────────────────────────────────────
KRAS_CELLS = []


def add_kras():
    # KRAS G12C — variant-specific BIO exists
    KRAS_CELLS.append(yaml_cell(
        cell_id="BMA-KRAS-G12C-NSCLC",
        biomarker_id="BIO-KRAS-G12C",
        variant_qualifier="G12C",
        disease_id="DIS-NSCLC",
        escat_tier="IA", oncokb_level="1",
        summary="""
            KRAS G12C in advanced NSCLC (~13% of adenocarcinoma): sotorasib
            (CodeBreaK 100/200) and adagrasib (KRYSTAL-1) are FDA/EMA-approved
            for previously-treated metastatic disease. ORR ~40%, PFS ~6 mo.
            Frontline KRYSTAL-7 (adagrasib + pembrolizumab) and CodeBreaK 202
            ongoing.
        """,
        fda=["sotorasib (Lumakras) — locally advanced/metastatic G12C NSCLC after ≥1 prior systemic therapy (FDA 2021, full approval after CodeBreaK 200)",
             "adagrasib (Krazati) — pretreated G12C NSCLC (FDA accelerated 2022)"],
        ema=["sotorasib — G12C NSCLC (EMA 2022)", "adagrasib — G12C NSCLC (EMA 2024)"],
        combos=["sotorasib monotherapy", "adagrasib monotherapy"],
        contraindicated=["non-G12C KRAS — sotorasib/adagrasib not active on G12D/G12V/G13D/Q61"],
        sources=["SRC-NCCN-NSCLC-2025", "SRC-ESMO-NSCLC-METASTATIC-2024"],
        notes="ESCAT IA. OncoKB Level 1. Reflex testing for KRAS G12C in metastatic NSCLC. STK11/KEAP1 co-mutations may modulate response.",
    ))
    KRAS_CELLS.append(yaml_cell(
        cell_id="BMA-KRAS-G12C-CRC",
        biomarker_id="BIO-KRAS-G12C",
        variant_qualifier="G12C",
        disease_id="DIS-CRC",
        escat_tier="IB", oncokb_level="1",
        summary="""
            KRAS G12C in mCRC (~3-4%): single-agent KRASG12C inhibitors
            insufficient (intrinsic EGFR feedback). Combination adagrasib +
            cetuximab (KRYSTAL-1, Yaeger et al. NEJM 2023) ORR 46%, PFS 6.9
            mo. Sotorasib + panitumumab (CodeBreaK 300, Fakih et al. NEJM
            2023) ORR 26% vs investigator's choice. Both FDA-approved 2024.
        """,
        fda=["adagrasib + cetuximab — pretreated G12C mCRC (FDA 2024)",
             "sotorasib + panitumumab — pretreated G12C mCRC (FDA 2024)"],
        ema=["sotorasib + panitumumab — G12C mCRC (EMA 2024)"],
        combos=["adagrasib + cetuximab", "sotorasib + panitumumab"],
        contraindicated=["KRASG12C inhibitor monotherapy in CRC (analogous to BRAFi-monotherapy failure: EGFR-mediated reactivation)"],
        sources=["SRC-NCCN-COLON-2025", "SRC-ESMO-COLON-2024"],
        notes="ESCAT IB. OncoKB Level 1. Combo with anti-EGFR antibody is mandatory. Frontline still FOLFOX/FOLFIRI ± bev.",
    ))
    KRAS_CELLS.append(yaml_cell(
        cell_id="BMA-KRAS-G12C-PDAC",
        biomarker_id="BIO-KRAS-G12C",
        variant_qualifier="G12C",
        disease_id="DIS-PDAC",
        escat_tier="IIB", oncokb_level="3A",
        summary="""
            KRAS G12C is rare in PDAC (~1-2%, vs ~30% G12D and ~25% G12V).
            Sotorasib (CodeBreaK 100 PDAC cohort, Strickler et al. NEJM
            2023) ORR 21%, PFS 4 mo in pretreated G12C PDAC. Adagrasib
            (KRYSTAL-1 GI cohort) ORR 33%. NCCN recommends in 2L+.
        """,
        fda=["sotorasib — accelerated approval considered, NCCN 2L recommendation"],
        ema=[],
        combos=["sotorasib monotherapy", "adagrasib monotherapy"],
        contraindicated=[],
        sources=["SRC-NCCN-PANCREATIC-2025", "SRC-ESMO-PANCREATIC-2024"],
        notes="ESCAT IIB. OncoKB Level 3A. Reflex KRAS sequencing in metastatic PDAC because G12C and G12D are now actionable.",
    ))
    KRAS_CELLS.append(yaml_cell(
        cell_id="BMA-KRAS-G12C-OVARIAN",
        biomarker_id="BIO-KRAS-G12C",
        variant_qualifier="G12C",
        disease_id="DIS-OVARIAN",
        escat_tier="IIIA", oncokb_level="3A",
        summary="""
            KRAS G12C in ovarian (mostly low-grade serous) is rare. Tissue-
            agnostic basket data (CodeBreaK 100 multi-tumor cohort) show
            modest activity. NCCN supports off-label use after standard
            therapy in G12C+ advanced ovarian.
        """,
        sources=["SRC-NCCN-OVARIAN-2025"],
        combos=["sotorasib (off-label tissue-agnostic rationale)"],
        notes="ESCAT IIIA. OncoKB Level 3A. LGSOC may also harbor BRAF V600E (preferred target where co-occurring).",
    ))
    KRAS_CELLS.append(yaml_cell(
        cell_id="BMA-KRAS-G12C-ENDOMETRIAL",
        biomarker_id="BIO-KRAS-G12C",
        variant_qualifier="G12C",
        disease_id="DIS-ENDOMETRIAL",
        escat_tier="IIIA", oncokb_level="3B",
        summary="""
            KRAS mutations occur in ~15-25% of endometrioid endometrial
            cancers; G12C is a minority subset. Tissue-agnostic
            rationale with sotorasib/adagrasib supported by NCCN as
            off-label option in pretreated G12C+ disease.
        """,
        sources=["SRC-NCCN-UTERINE-2025"],
        combos=["sotorasib (off-label)", "adagrasib (off-label)"],
        notes="ESCAT IIIA. Limited prospective endometrial-specific data.",
    ))
    # Other KRAS variants — use BIO-RAS-MUTATION
    for variant, dis, tier, level, summary, sources in [
        ("G12D", "DIS-PDAC", "IIB", "3A",
         "KRAS G12D is the most common PDAC driver (~35-40%). MRTX1133 (Mirati/Bristol) and RMC-9805 are in clinical development; ASTX295 / BI-2865 also active. No FDA approval yet (2026); NCCN flags clinical trial.",
         ["SRC-NCCN-PANCREATIC-2025"]),
        ("G12D", "DIS-CRC", "IV", "4",
         "KRAS G12D in mCRC predicts anti-EGFR resistance. No approved targeted therapy 2026; trial-only (MRTX1133, RMC-9805 + cetuximab combos).",
         ["SRC-NCCN-COLON-2025"]),
        ("G12V", "DIS-PDAC", "IV", "4",
         "KRAS G12V in PDAC — second-most common driver. No approved drug 2026; pan-KRAS inhibitors and TCR therapies in trial.",
         ["SRC-NCCN-PANCREATIC-2025"]),
        ("G12V", "DIS-CRC", "IV", "4",
         "KRAS G12V in mCRC — anti-EGFR contraindication marker, no targeted therapy. Standard chemo ± anti-VEGF.",
         ["SRC-NCCN-COLON-2025"]),
        ("G12D", "DIS-NSCLC", "IV", "4",
         "KRAS G12D in NSCLC (~5%) — pan-KRAS / G12D-selective inhibitors in early trials. ICI-based regimens preferred per usual NSCLC algorithm.",
         ["SRC-NCCN-NSCLC-2025"]),
        ("G13D", "DIS-CRC", "IV", "4",
         "KRAS G13D in mCRC — historical signal of partial cetuximab response (De Roock 2010) was not confirmed prospectively. Treat as RAS-mut, anti-EGFR contraindicated.",
         ["SRC-NCCN-COLON-2025"]),
        ("Q61X", "DIS-CRC", "IV", "4",
         "KRAS Q61 in mCRC — RAS-mutant, anti-EGFR contraindicated. Standard chemo.",
         ["SRC-NCCN-COLON-2025"]),
        ("Q61X", "DIS-MELANOMA", "IIB", "3A",
         "KRAS Q61 (rare in melanoma; NRAS Q61 is more common) — MEKi monotherapy modest activity (binimetinib in NRAS-mut melanoma NEMO trial; KRAS Q61 cells extrapolated).",
         ["SRC-NCCN-MELANOMA-2025"]),
        ("A146T", "DIS-CRC", "IV", "4",
         "KRAS A146T — rare, anti-EGFR contraindication marker. No targeted therapy.",
         ["SRC-NCCN-COLON-2025"]),
        ("G12V", "DIS-ENDOMETRIAL", "IV", "4",
         "KRAS G12V in endometrial — no targeted approval. POLE/MMR/p53 molecular subtyping drives 1L choice.",
         ["SRC-NCCN-UTERINE-2025"]),
    ]:
        slug = f"BMA-KRAS-{variant.upper().replace('Q61X','Q61')}-{dis.removeprefix('DIS-')}"
        KRAS_CELLS.append(yaml_cell(
            cell_id=slug,
            biomarker_id="BIO-RAS-MUTATION",
            variant_qualifier=f"KRAS {variant}",
            disease_id=dis,
            escat_tier=tier, oncokb_level=level,
            summary=summary,
            sources=sources,
            notes=f"ESCAT {tier}. Encoded under BIO-RAS-MUTATION (no variant-specific BIO for KRAS {variant} yet). FLAG: dedicated BIO-KRAS-{variant} would improve granularity.",
        ))


add_kras()

# ───────────────────────── NRAS ─────────────────────────────────────────────
NRAS_CELLS = []


def add_nras():
    for variant, dis, tier, level, summary, sources, combos, contra in [
        ("Q61R", "DIS-MELANOMA", "IB", "2",
         "NRAS Q61R is the most common NRAS hotspot in melanoma (~20% of cutaneous melanomas). Binimetinib (MEKi) monotherapy improved PFS vs dacarbazine in NEMO (Dummer et al. Lancet Oncol 2017) — modest benefit; not FDA-approved as monotherapy. ICI (anti-PD1 ± anti-CTLA4) is the standard 1L for NRAS-mut metastatic melanoma. MEKi+CDK4/6i combos under investigation.",
         ["SRC-NCCN-MELANOMA-2025", "SRC-ESMO-MELANOMA-2024"],
         ["nivolumab + ipilimumab (1L preferred)", "binimetinib (NEMO; investigational/off-label)"],
         []),
        ("Q61K", "DIS-MELANOMA", "IB", "2",
         "NRAS Q61K — same therapeutic rationale as Q61R. ICI 1L; binimetinib NEMO subgroup.",
         ["SRC-NCCN-MELANOMA-2025"],
         ["anti-PD1-based ICI", "binimetinib (off-label)"],
         []),
        ("G12", "DIS-MELANOMA", "IIIA", "3B",
         "NRAS G12/G13 — rarer than Q61 mutations in melanoma. Same MEKi/ICI rationale extrapolated.",
         ["SRC-NCCN-MELANOMA-2025"],
         ["anti-PD1-based ICI"],
         []),
        ("G13", "DIS-MELANOMA", "IIIA", "3B",
         "NRAS G13 in melanoma — limited data; treat per NRAS-mut algorithm.",
         ["SRC-NCCN-MELANOMA-2025"],
         ["anti-PD1-based ICI"],
         []),
        ("Q61R", "DIS-AML", "IIIA", "4",
         "NRAS mutations in AML (~10-15%) — adverse prognostic in some contexts; not directly targeted. Trametinib + venetoclax / azacitidine combos in trial.",
         ["SRC-NCCN-AML-2025", "SRC-ELN-AML-2022"],
         ["clinical trial enrollment"],
         []),
        ("Q61K", "DIS-AML", "IIIA", "4",
         "NRAS Q61K in AML — same as Q61R; no approved targeted agent.",
         ["SRC-NCCN-AML-2025"],
         [],
         []),
        ("G12", "DIS-AML", "IIIA", "4",
         "NRAS G12/G13 in AML — common in pediatric AML and JMML; not directly targeted.",
         ["SRC-NCCN-AML-2025"],
         [],
         []),
        ("G13", "DIS-AML", "IIIA", "4",
         "NRAS G13 in AML — same rationale.",
         ["SRC-NCCN-AML-2025"],
         [],
         []),
        ("Q61R", "DIS-MDS-LR", "IIIB", "4",
         "NRAS in MDS — typically signals progression risk to AML. No targeted therapy in MDS-LR; HMA still standard.",
         ["SRC-ESMO-MDS-2021"],
         [],
         []),
        ("Q61R", "DIS-MDS-HR", "IIIB", "4",
         "NRAS in higher-risk MDS — adverse marker; HMA + venetoclax considered, alloSCT preferred.",
         ["SRC-ESMO-MDS-2021"],
         [],
         []),
    ]:
        slug = f"BMA-NRAS-{variant}-{dis.removeprefix('DIS-')}"
        NRAS_CELLS.append(yaml_cell(
            cell_id=slug,
            biomarker_id="BIO-RAS-MUTATION",
            variant_qualifier=f"NRAS {variant}",
            disease_id=dis,
            escat_tier=tier, oncokb_level=level,
            summary=summary,
            combos=combos,
            contraindicated=contra,
            sources=sources,
            notes=f"ESCAT {tier}. Under BIO-RAS-MUTATION (no dedicated BIO-NRAS-{variant} yet — flag for BIO authoring).",
        ))


add_nras()

# ───────────────────────── PIK3CA ───────────────────────────────────────────
PIK3CA_CELLS = []


def add_pik3ca():
    breast_summary = """
        PIK3CA hotspot mutations (~40% of HR+/HER2- metastatic breast cancer):
        alpelisib + fulvestrant improves PFS vs fulvestrant alone (SOLAR-1,
        André et al. NEJM 2019) in PIK3CA-mut after AI failure. Inavolisib +
        palbociclib + fulvestrant (INAVO120, Turner et al. NEJM 2024) improves
        PFS in 1L PIK3CA-mut HR+/HER2- with ET-resistance — FDA-approved 2024.
        Capivasertib + fulvestrant (CAPItello-291, Turner et al. NEJM 2023)
        also active in PIK3CA-mut.
    """
    breast_combos = ["alpelisib + fulvestrant", "inavolisib + palbociclib + fulvestrant", "capivasertib + fulvestrant"]
    for variant in ["H1047R", "H1047L", "E545K", "E542K"]:
        PIK3CA_CELLS.append(yaml_cell(
            cell_id=f"BMA-PIK3CA-{variant}-BREAST",
            biomarker_id="BIO-PIK3CA-MUTATION",
            variant_qualifier=variant,
            disease_id="DIS-BREAST",
            escat_tier="IA", oncokb_level="1",
            summary=breast_summary,
            fda=["alpelisib + fulvestrant — HR+/HER2- PIK3CA-mut after AI (FDA 2019)",
                 "inavolisib + palbociclib + fulvestrant — 1L HR+/HER2- PIK3CA-mut endocrine-resistant (FDA 2024)",
                 "capivasertib + fulvestrant — HR+/HER2- with PIK3CA / AKT1 / PTEN alteration (FDA 2023)"],
            ema=["alpelisib + fulvestrant — PIK3CA-mut HR+/HER2- (EMA 2020)",
                 "capivasertib + fulvestrant — HR+/HER2- (EMA 2024)"],
            combos=breast_combos,
            sources=["SRC-NCCN-BREAST-2025", "SRC-ESMO-BREAST-METASTATIC-2024"],
            notes=f"ESCAT IA. OncoKB Level 1. {variant} is a {'kinase-domain (exon 20)' if variant.startswith('H') else 'helical-domain (exon 9)'} hotspot. Companion diagnostic: therascreen PIK3CA + Guardant360 CDx + FoundationOne Liquid CDx. Hyperglycemia is class-effect AE for alpelisib.",
        ))
    PIK3CA_CELLS.append(yaml_cell(
        cell_id="BMA-PIK3CA-EXON9-BREAST",
        biomarker_id="BIO-PIK3CA-MUTATION",
        variant_qualifier="exon 9 (helical domain) any pathogenic",
        disease_id="DIS-BREAST",
        escat_tier="IA", oncokb_level="1",
        summary=breast_summary,
        combos=breast_combos,
        sources=["SRC-NCCN-BREAST-2025", "SRC-ESMO-BREAST-METASTATIC-2024"],
        notes="ESCAT IA. Catch-all for non-canonical exon 9 PIK3CA hotspots covered by SOLAR-1 / CAPItello inclusion criteria.",
    ))
    PIK3CA_CELLS.append(yaml_cell(
        cell_id="BMA-PIK3CA-EXON20-BREAST",
        biomarker_id="BIO-PIK3CA-MUTATION",
        variant_qualifier="exon 20 (kinase domain) any pathogenic",
        disease_id="DIS-BREAST",
        escat_tier="IA", oncokb_level="1",
        summary=breast_summary,
        combos=breast_combos,
        sources=["SRC-NCCN-BREAST-2025", "SRC-ESMO-BREAST-METASTATIC-2024"],
        notes="ESCAT IA. Catch-all for non-canonical exon 20 PIK3CA hotspots.",
    ))
    PIK3CA_CELLS.append(yaml_cell(
        cell_id="BMA-PIK3CA-HOTSPOT-CERVICAL",
        biomarker_id="BIO-PIK3CA-MUTATION",
        variant_qualifier="hotspot (E545K / E542K / H1047R)",
        disease_id="DIS-CERVICAL",
        escat_tier="IIIA", oncokb_level="3B",
        summary="""
            PIK3CA mutations occur in ~30% of squamous cervical cancers.
            No PI3Ki/AKTi approval in cervical (2026); investigational
            in tissue-agnostic basket trials. ICI (pembrolizumab,
            cemiplimab) remains the targeted-therapy backbone.
        """,
        sources=["SRC-NCCN-CERVICAL-2025", "SRC-ESMO-CERVICAL-2024"],
        notes="ESCAT IIIA. Off-label/trial-only in cervical.",
    ))
    PIK3CA_CELLS.append(yaml_cell(
        cell_id="BMA-PIK3CA-HOTSPOT-ENDOMETRIAL",
        biomarker_id="BIO-PIK3CA-MUTATION",
        variant_qualifier="hotspot (E545K / E542K / H1047R)",
        disease_id="DIS-ENDOMETRIAL",
        escat_tier="IIIA", oncokb_level="3B",
        summary="""
            PIK3CA mutations occur in ~30-50% of endometrioid endometrial
            cancers, often co-occurring with PTEN loss. PI3Ki/AKTi/mTORi
            monotherapy modest activity (everolimus + letrozole
            recommended). Tissue-agnostic capivasertib not formally
            approved in endometrial.
        """,
        combos=["everolimus + letrozole", "capivasertib (off-label tissue-agnostic rationale)"],
        sources=["SRC-NCCN-UTERINE-2025", "SRC-ESGO-ENDOMETRIAL-2025"],
        notes="ESCAT IIIA. POLE/MMR/p53 molecular subtype guides primary 1L choice (dostarlimab/pembrolizumab + carbo/pacli).",
    ))
    # No HNSCC disease in KB → skip


add_pik3ca()


# ───────────────────────── IDH1 / IDH2 ──────────────────────────────────────
IDH_CELLS = []


def add_idh():
    # IDH1 R132 hotspots × AML
    for variant, dis, tier, level, summary, fda, combos, sources in [
        ("R132H", "DIS-AML", "IA", "1",
         "IDH1 R132 mutations (~6-10% of AML). Ivosidenib monotherapy (AGILE, Montesinos et al. NEJM 2022 — combo with azacitidine; AG120-C-001 — monotherapy in R/R) FDA-approved. Ivosidenib + azacitidine (1L unfit, AGILE) doubles OS vs azacitidine alone.",
         ["ivosidenib — IDH1-mut R/R AML (FDA 2018); ivosidenib + azacitidine 1L unfit (FDA 2022)",
          "olutasidenib — IDH1-mut R/R AML (FDA 2022)"],
         ["ivosidenib monotherapy", "ivosidenib + azacitidine (1L unfit)", "olutasidenib monotherapy", "ivosidenib + 7+3 (frontline fit, in trials)"],
         ["SRC-NCCN-AML-2025", "SRC-ELN-AML-2022", "SRC-ESMO-AML-2020"]),
        ("R132C", "DIS-AML", "IA", "1",
         "IDH1 R132C — same therapeutic implications as R132H; ivosidenib targets all R132 variants.",
         ["ivosidenib — IDH1-mut R/R AML (FDA 2018)"],
         ["ivosidenib", "olutasidenib", "ivosidenib + azacitidine"],
         ["SRC-NCCN-AML-2025", "SRC-ELN-AML-2022"]),
        ("R132G", "DIS-AML", "IA", "1",
         "IDH1 R132G — covered by IDH1-mut label (any R132).",
         ["ivosidenib — IDH1-mut R/R AML"],
         ["ivosidenib", "olutasidenib"],
         ["SRC-NCCN-AML-2025"]),
        ("R132L", "DIS-AML", "IA", "1",
         "IDH1 R132L — covered by IDH1-mut label.",
         ["ivosidenib — IDH1-mut R/R AML"],
         ["ivosidenib", "olutasidenib"],
         ["SRC-NCCN-AML-2025"]),
        ("R132S", "DIS-AML", "IA", "1",
         "IDH1 R132S — covered by IDH1-mut label.",
         ["ivosidenib — IDH1-mut R/R AML"],
         ["ivosidenib", "olutasidenib"],
         ["SRC-NCCN-AML-2025"]),
    ]:
        IDH_CELLS.append(yaml_cell(
            cell_id=f"BMA-IDH1-{variant}-AML",
            biomarker_id="BIO-IDH-MUTATION",
            variant_qualifier=f"IDH1 {variant}",
            disease_id=dis,
            escat_tier=tier, oncokb_level=level,
            summary=summary,
            fda=fda,
            combos=combos,
            sources=sources,
            notes=f"ESCAT {tier}. Differentiation syndrome class AE — prophylactic dexamethasone protocol per ELN. Companion dx: Abbott RealTime IDH1.",
        ))
    # IDH1 R132 × GBM (vorasidenib for low-grade — but only DIS-GBM exists)
    IDH_CELLS.append(yaml_cell(
        cell_id="BMA-IDH1-R132H-GBM",
        biomarker_id="BIO-IDH-MUTATION",
        variant_qualifier="IDH1 R132H",
        disease_id="DIS-GBM",
        escat_tier="IIA", oncokb_level="2",
        summary="""
            IDH1 R132H — defines IDH-mutant astrocytoma (WHO 2021 grade 2-4)
            and oligodendroglioma (with 1p/19q codeletion). Vorasidenib
            improved PFS in residual/recurrent grade 2 IDH-mut glioma post-
            resection (INDIGO, Mellinghoff et al. NEJM 2023) — FDA-approved
            2024. For grade 4 (IDH-mut GBM equivalent) — standard of care
            still RT + TMZ; ivosidenib explored.
        """,
        fda=["vorasidenib — grade 2 IDH-mut astrocytoma/oligodendroglioma post-resection (FDA 2024)"],
        ema=["vorasidenib — grade 2 IDH-mut glioma (EMA 2024)"],
        combos=["vorasidenib monotherapy (low-grade IDH-mut)", "ivosidenib (high-grade IDH-mut, off-label/trial)"],
        sources=["SRC-NCCN-CNS-2025", "SRC-EANO-GBM-2024"],
        notes="ESCAT IIA. OncoKB Level 2. IDH-mut GBM is a distinct entity from IDH-WT GBM and has better prognosis. R132H IHC is the standard screening test; non-canonical R132 require sequencing.",
    ))
    IDH_CELLS.append(yaml_cell(
        cell_id="BMA-IDH1-R132C-GBM",
        biomarker_id="BIO-IDH-MUTATION",
        variant_qualifier="IDH1 R132C",
        disease_id="DIS-GBM",
        escat_tier="IIA", oncokb_level="2",
        summary="IDH1 R132C in glioma — non-canonical; same therapeutic implications as R132H (vorasidenib).",
        fda=["vorasidenib — grade 2 IDH-mut glioma (FDA 2024)"],
        combos=["vorasidenib"],
        sources=["SRC-NCCN-CNS-2025", "SRC-EANO-GBM-2024"],
        notes="ESCAT IIA. Non-R132H variants missed by IHC — require sequencing.",
    ))
    IDH_CELLS.append(yaml_cell(
        cell_id="BMA-IDH1-R132G-GBM",
        biomarker_id="BIO-IDH-MUTATION",
        variant_qualifier="IDH1 R132G",
        disease_id="DIS-GBM",
        escat_tier="IIA", oncokb_level="2",
        summary="IDH1 R132G — covered by IDH-mut glioma vorasidenib label.",
        combos=["vorasidenib"],
        sources=["SRC-NCCN-CNS-2025"],
        notes="ESCAT IIA.",
    ))
    IDH_CELLS.append(yaml_cell(
        cell_id="BMA-IDH1-R132L-GBM",
        biomarker_id="BIO-IDH-MUTATION",
        variant_qualifier="IDH1 R132L",
        disease_id="DIS-GBM",
        escat_tier="IIA", oncokb_level="2",
        summary="IDH1 R132L — covered by vorasidenib.",
        combos=["vorasidenib"],
        sources=["SRC-NCCN-CNS-2025"],
        notes="ESCAT IIA.",
    ))
    IDH_CELLS.append(yaml_cell(
        cell_id="BMA-IDH1-R132S-GBM",
        biomarker_id="BIO-IDH-MUTATION",
        variant_qualifier="IDH1 R132S",
        disease_id="DIS-GBM",
        escat_tier="IIA", oncokb_level="2",
        summary="IDH1 R132S — covered by vorasidenib.",
        combos=["vorasidenib"],
        sources=["SRC-NCCN-CNS-2025"],
        notes="ESCAT IIA.",
    ))
    # IDH2 × AML
    for variant, summary in [
        ("R140Q", "IDH2 R140Q (~5-9% of AML). Enasidenib (IDHIFA, AG221-C-001 Stein et al. Blood 2017) FDA-approved 2017 for R/R IDH2-mut AML. IDHENTIFY (Ph3) confirmed OS benefit late-line. Combos with azacitidine (Ph2) promising 1L unfit."),
        ("R172K", "IDH2 R172K — slightly different metabolic profile but same enasidenib indication."),
    ]:
        IDH_CELLS.append(yaml_cell(
            cell_id=f"BMA-IDH2-{variant}-AML",
            biomarker_id="BIO-IDH-MUTATION",
            variant_qualifier=f"IDH2 {variant}",
            disease_id="DIS-AML",
            escat_tier="IA", oncokb_level="1",
            summary=summary,
            fda=["enasidenib — IDH2-mut R/R AML (FDA 2017)"],
            combos=["enasidenib monotherapy", "enasidenib + azacitidine (1L unfit, off-label/trial)"],
            sources=["SRC-NCCN-AML-2025", "SRC-ELN-AML-2022"],
            notes="ESCAT IA. OncoKB Level 1. Differentiation syndrome AE class effect.",
        ))
    # IDH2 × MDS (MDS-HR / MDS-LR)
    for dis in ["DIS-MDS-HR", "DIS-MDS-LR"]:
        IDH_CELLS.append(yaml_cell(
            cell_id=f"BMA-IDH2-R140Q-{dis.removeprefix('DIS-')}",
            biomarker_id="BIO-IDH-MUTATION",
            variant_qualifier="IDH2 R140Q",
            disease_id=dis,
            escat_tier="IIA", oncokb_level="2",
            summary="""
                IDH2 R140Q in MDS — enasidenib monotherapy active in MDS
                (NCT01915498, DiNardo et al. Blood 2018). IDH-mut MDS often
                progresses to AML; IDH2i can delay transformation. Not
                yet on full FDA MDS label (off-label use NCCN-supported).
            """,
            combos=["enasidenib (off-label MDS)"],
            sources=["SRC-ESMO-MDS-2021", "SRC-IPSS-M-BERNARD-2022"],
            notes="ESCAT IIA. Off-label in MDS pending Ph3 readout. Frontline MDS-LR luspatercept / HMA; MDS-HR HMA ± venetoclax.",
        ))
        IDH_CELLS.append(yaml_cell(
            cell_id=f"BMA-IDH2-R172K-{dis.removeprefix('DIS-')}",
            biomarker_id="BIO-IDH-MUTATION",
            variant_qualifier="IDH2 R172K",
            disease_id=dis,
            escat_tier="IIA", oncokb_level="2",
            summary="IDH2 R172K in MDS — same enasidenib rationale as R140Q.",
            combos=["enasidenib (off-label MDS)"],
            sources=["SRC-ESMO-MDS-2021"],
            notes="ESCAT IIA. Off-label in MDS.",
        ))
    # IDH1 × MDS
    for dis in ["DIS-MDS-HR", "DIS-MDS-LR"]:
        IDH_CELLS.append(yaml_cell(
            cell_id=f"BMA-IDH1-R132H-{dis.removeprefix('DIS-')}",
            biomarker_id="BIO-IDH-MUTATION",
            variant_qualifier="IDH1 R132H",
            disease_id=dis,
            escat_tier="IIA", oncokb_level="2",
            summary="""
                IDH1 R132 in MDS — ivosidenib monotherapy active (DiNardo
                et al. JCO 2021 — ORR 75% MDS, CR 38%). Ivosidenib +
                azacitidine combos in trial. Off-label NCCN-supported.
            """,
            combos=["ivosidenib (off-label MDS)", "ivosidenib + azacitidine (trial)"],
            sources=["SRC-ESMO-MDS-2021"],
            notes="ESCAT IIA.",
        ))
    # IDH2 × AITL (T-cell lymphoma)
    IDH_CELLS.append(yaml_cell(
        cell_id="BMA-IDH2-R172K-AITL",
        biomarker_id="BIO-IDH-MUTATION",
        variant_qualifier="IDH2 R172K (or R172 hotspot)",
        disease_id="DIS-AITL",
        escat_tier="IIIA", oncokb_level="3B",
        summary="""
            IDH2 R172 mutations occur in ~30% of AITL (TFH-derived PTCL).
            Enasidenib monotherapy active in IDH2-mut AITL (small case
            series; Lemonnier et al. Blood 2016 / 2021). NCCN supports
            off-label use in R/R IDH2-mut AITL.
        """,
        combos=["enasidenib (off-label R/R AITL)"],
        sources=["SRC-ESMO-PTCL-2024", "SRC-NCCN-BCELL-2025"],
        notes="ESCAT IIIA. AITL frontline still CHOP/CHOEP; brentuximab + CHP for CD30+ disease (ECHELON-2).",
    ))
    IDH_CELLS.append(yaml_cell(
        cell_id="BMA-IDH2-R140Q-AITL",
        biomarker_id="BIO-IDH-MUTATION",
        variant_qualifier="IDH2 R140Q",
        disease_id="DIS-AITL",
        escat_tier="IIIB", oncokb_level="4",
        summary="IDH2 R140Q in AITL — much less common than R172 in T-cell lymphoma (myeloid pattern). Enasidenib rationale extrapolated; case-report level.",
        combos=["enasidenib (off-label, exploratory)"],
        sources=["SRC-ESMO-PTCL-2024"],
        notes="ESCAT IIIB. R172 dominant in AITL.",
    ))
    # No DIS-CHOLANGIOCARCINOMA / DIS-CHONDROSARCOMA → skip + flag


add_idh()


# ───────────────────────── TP53 ─────────────────────────────────────────────
TP53_CELLS = []


def add_tp53():
    # Hotspot variants × diseases — predominantly prognostic, not directly actionable
    hotspot_variants = ["R175H", "R248Q", "R273H", "R282W"]
    diseases = [
        ("DIS-MDS-HR", "IIIB", "4",
         "TP53-mut higher-risk MDS — dismal prognosis with HMA monotherapy (median OS ~6-10 mo). Eprenetapopt (APR-246) Ph3 missed primary endpoint and was retired (2021). AlloSCT remains the only potentially curative option but outcomes inferior to TP53-WT. Magrolimab + azacitidine Ph3 (ENHANCE) negative.",
         ["clinical trial enrollment", "alloSCT consideration (preferred curative path despite poor outcomes)", "azacitidine + venetoclax (palliative; modest CR but non-durable)"],
         ["SRC-ESMO-MDS-2021", "SRC-IPSS-M-BERNARD-2022"]),
        ("DIS-AML", "IIIB", "4",
         "TP53-mut AML — chemo-resistant, dismal outcomes (CR ~20% with 7+3, OS ~6 mo). Decitabine 10-day or azacitidine + venetoclax (CR ~50% but non-durable in TP53-mut). AlloSCT outcomes poor but still preferred when feasible.",
         ["azacitidine + venetoclax (palliative, R/R)", "decitabine 10-day", "alloSCT consideration", "clinical trial"],
         ["SRC-NCCN-AML-2025", "SRC-ELN-AML-2022"]),
        ("DIS-CLL", "IIIA", "3A",
         "TP53-mut CLL contraindicates chemoimmunotherapy (FCR/BR). BTKi (acalabrutinib, zanubrutinib, ibrutinib) or BCL2i (venetoclax + obinutuzumab; CLL14) preferred. Some guidelines favor venetoclax-based fixed-duration over continuous BTKi for high-risk; data evolving.",
         ["acalabrutinib monotherapy", "zanubrutinib monotherapy", "venetoclax + obinutuzumab (CLL14)", "BTKi + venetoclax (CAPTIVATE / GLOW)"],
         ["SRC-NCCN-BCELL-2025", "SRC-ESMO-CLL-2024"]),
        ("DIS-MM", "IIA", "3A",
         "TP53-mut / del(17p) myeloma — high-risk cytogenetics composite; quadruplet (D-VRd; PERSEUS) preferred over triplet. Maintenance with daratumumab/lenalidomide. CAR-T (ide-cel, cilta-cel) effective regardless of TP53 status.",
         ["D-VRd (1L transplant-eligible)", "Dara-Rd (1L transplant-ineligible)", "ide-cel / cilta-cel (R/R)", "alloSCT consideration in young high-risk"],
         ["SRC-NCCN-MM-2025", "SRC-ESMO-MM-2023", "SRC-EHA-EMN-MM-2025"]),
        ("DIS-MCL", "IIA", "3A",
         "TP53-mut MCL — predicts chemoimmuno failure. Acalabrutinib + rituximab (TRIANGLE / ECHO) preferred over R-CHOP/R-DHAP+autoSCT regardless of fitness.",
         ["acalabrutinib + rituximab (1L)", "ibrutinib + rituximab + venetoclax (R/R)", "CAR-T brexu-cel (R/R)"],
         ["SRC-NCCN-BCELL-2025", "SRC-ESMO-MCL-2024"]),
        ("DIS-DLBCL-NOS", "IIIB", "4",
         "TP53-mut DLBCL — predicts R-CHOP failure; flag for early CAR-T pathway consideration at 2L+. Not yet driving 1L algorithm; pola-R-CHP (POLARIX) considered but TP53 not in selection criteria.",
         ["pola-R-CHP (1L; not TP53-selected)", "CAR-T axi-cel / liso-cel (2L+)"],
         ["SRC-NCCN-BCELL-2025", "SRC-ESMO-DLBCL-2024"]),
        ("DIS-OVARIAN", "IIIA", "4",
         "TP53 mutation is near-universal in high-grade serous ovarian (~96%). Not actionable per se; defines the disease phenotype. Niraparib/olaparib (HRD-positive) and bevacizumab combos drive 1L choices instead.",
         ["bevacizumab + carbo/pacli (1L HGSOC)", "niraparib maintenance (BRCA-WT/HRD-test)"],
         ["SRC-NCCN-OVARIAN-2025", "SRC-ESMO-OVARIAN-2024"]),
        ("DIS-NSCLC", "IIIB", "4",
         "TP53 mutations in NSCLC (~50%) — adverse prognostic; modulate ICI response (TP53+KRAS may have higher TMB/ORR; TP53+EGFR may have shorter OS). Not directly targeted.",
         ["per usual NSCLC algorithm based on driver"],
         ["SRC-NCCN-NSCLC-2025"]),
        ("DIS-BREAST", "IIIB", "4",
         "TP53 mutations in breast — common in TNBC and basal-like; adverse prognostic. Not directly targeted; chemo / pembrolizumab (KEYNOTE-522) per usual TNBC algorithm.",
         ["per usual TNBC algorithm (KEYNOTE-522)"],
         ["SRC-NCCN-BREAST-2025", "SRC-ESMO-BREAST-EARLY-2024"]),
    ]
    # Gene-level cell per disease
    for dis, tier, level, summary, combos, sources in diseases:
        TP53_CELLS.append(yaml_cell(
            cell_id=f"BMA-TP53-MUT-{dis.removeprefix('DIS-')}",
            biomarker_id="BIO-TP53-MUTATION",
            variant_qualifier="any pathogenic mutation OR del(17p)",
            disease_id=dis,
            escat_tier=tier, oncokb_level=level,
            summary=summary,
            combos=combos,
            sources=sources,
            notes=f"ESCAT {tier}. Gene-level cell — biallelic vs monoallelic distinction matters in MDS/AML (biallelic = TP53-multihit per IPSS-M / ICC 2022, far worse). Per-hotspot cells provided for the most common variants.",
        ))
    # A handful of hotspot-specific cells in CLL + MM where biallelic state matters
    for variant in hotspot_variants:
        TP53_CELLS.append(yaml_cell(
            cell_id=f"BMA-TP53-{variant}-CLL",
            biomarker_id="BIO-TP53-MUTATION",
            variant_qualifier=variant,
            disease_id="DIS-CLL",
            escat_tier="IIIA", oncokb_level="3A",
            summary=f"TP53 hotspot {variant} in CLL — DNA-binding domain dominant-negative variant. Same therapeutic implications as gene-level TP53-mut: BTKi or BCL2i, avoid chemoimmuno.",
            combos=["acalabrutinib", "venetoclax + obinutuzumab"],
            sources=["SRC-NCCN-BCELL-2025", "SRC-ESMO-CLL-2024"],
            notes=f"ESCAT IIIA. {variant} is among the most common TP53 hotspots in CLL.",
        ))
        TP53_CELLS.append(yaml_cell(
            cell_id=f"BMA-TP53-{variant}-MDS-HR",
            biomarker_id="BIO-TP53-MUTATION",
            variant_qualifier=variant,
            disease_id="DIS-MDS-HR",
            escat_tier="IIIB", oncokb_level="4",
            summary=f"TP53 hotspot {variant} in higher-risk MDS — dismal prognosis. Biallelic vs monoallelic per IPSS-M scoring critical.",
            combos=["azacitidine + venetoclax", "alloSCT consideration", "clinical trial"],
            sources=["SRC-ESMO-MDS-2021", "SRC-IPSS-M-BERNARD-2022"],
            notes=f"ESCAT IIIB. {variant} hotspot — score per IPSS-M biallelic algorithm.",
        ))


add_tp53()


# ───────────────────────── MYD88 ────────────────────────────────────────────
MYD88_CELLS = []


def add_myd88():
    MYD88_CELLS.append(yaml_cell(
        cell_id="BMA-MYD88-L265P-WM",
        biomarker_id="BIO-MYD88-L265P",
        variant_qualifier="L265P",
        disease_id="DIS-WM",
        escat_tier="IA", oncokb_level="1",
        summary="""
            MYD88 L265P present in >90% of WM. Activates NF-κB via
            BTK/IRAK signaling — rationale for BTKi. Ibrutinib monotherapy
            (iNNOVATE substudy 2 / arm A — Treon et al. NEJM 2015 R/R;
            iNNOVATE — Dimopoulos et al. NEJM 2018 1L+R/R with rituximab)
            and zanubrutinib (ASPEN — Tam et al. Blood 2020) FDA-approved.
            CXCR4 WHIM-like co-mutation reduces but does not abolish
            response.
        """,
        fda=["ibrutinib monotherapy and ibrutinib + rituximab — WM (FDA 2015 / 2018)",
             "zanubrutinib monotherapy — WM (FDA 2021)"],
        ema=["ibrutinib — WM (EMA 2015)", "zanubrutinib — WM (EMA 2021)"],
        combos=["zanubrutinib (preferred per ASPEN — fewer cardiac AE vs ibrutinib)",
                "ibrutinib monotherapy", "ibrutinib + rituximab", "BR (chemo-immuno alternative)"],
        contraindicated=[],
        sources=["SRC-NCCN-BCELL-2025", "SRC-ESMO-WM-2024"],
        notes="ESCAT IA. OncoKB Level 1. CXCR4 WHIM-like mutation testing recommended as it modulates BTKi response. MYD88-WT WM (~10%) responds less well to BTKi.",
    ))
    MYD88_CELLS.append(yaml_cell(
        cell_id="BMA-MYD88-L265P-DLBCL-NOS",
        biomarker_id="BIO-MYD88-L265P",
        variant_qualifier="L265P (often with CD79B mutation — MCD/C5 cluster)",
        disease_id="DIS-DLBCL-NOS",
        escat_tier="IIB", oncokb_level="3A",
        summary="""
            MYD88 L265P in DLBCL marks the ABC/MCD molecular subtype
            (Schmitz et al. NEJM 2018; Wright Cancer Cell 2020). Ibrutinib
            improves OS specifically in MCD/N1/A53 subtypes when added to
            R-CHOP (PHOENIX subgroup analysis, Wilson et al. Cancer Cell
            2021). Not formally approved as biomarker-selected indication
            in DLBCL; basket trials ongoing.
        """,
        combos=["R-CHOP + ibrutinib (off-label, MCD/genetically-selected)",
                "pola-R-CHP (1L; POLARIX — not MYD88-selected but consider)",
                "CAR-T axi-cel / liso-cel (R/R)"],
        sources=["SRC-NCCN-BCELL-2025", "SRC-ESMO-DLBCL-2024"],
        notes="ESCAT IIB. OncoKB Level 3A. MYD88+CD79B co-mutation defines MCD subtype with strongest BTKi rationale. Not on FDA DLBCL label.",
    ))
    for dis in ["DIS-NODAL-MZL", "DIS-SPLENIC-MZL", "DIS-HCV-MZL"]:
        MYD88_CELLS.append(yaml_cell(
            cell_id=f"BMA-MYD88-L265P-{dis.removeprefix('DIS-')}",
            biomarker_id="BIO-MYD88-L265P",
            variant_qualifier="L265P",
            disease_id=dis,
            escat_tier="IIIA", oncokb_level="3B",
            summary="""
                MYD88 L265P found in ~5-10% of MZL (more in lymphoplasmacytoid
                variants; rare in classic SMZL/NMZL). Suggests overlap with WM
                biology and supports BTKi consideration in R/R disease (off-label).
            """,
            combos=["ibrutinib (off-label R/R MZL)", "zanubrutinib (FDA-approved R/R MZL — not MYD88-selected)"],
            sources=["SRC-NCCN-BCELL-2025", "SRC-ESMO-MZL-2024", "SRC-BSH-MZL-2024"],
            notes="ESCAT IIIA. Zanubrutinib has tissue-agnostic MZL approval (MAGNOLIA) regardless of MYD88 status.",
        ))


add_myd88()


# ───────────────────────── NOTCH1 ───────────────────────────────────────────
NOTCH1_CELLS = []


def add_notch1():
    NOTCH1_CELLS.append(yaml_cell(
        cell_id="BMA-NOTCH1-ACTIVATING-T-ALL",
        biomarker_id="BIO-NOTCH1-MUTATION",
        variant_qualifier="activating (HD or PEST domain)",
        disease_id="DIS-T-ALL",
        escat_tier="IIIA", oncokb_level="4",
        summary="""
            NOTCH1 activating mutations occur in >50% of T-ALL (HD and PEST
            domains). Gamma-secretase inhibitors (GSI) showed activity but
            were limited by GI toxicity. No GSI is FDA-approved in T-ALL.
            Standard 1L remains pediatric-inspired regimens (BFM,
            CALGB-10403). MRD-directed nelarabine/PEG-asparaginase per protocol.
        """,
        combos=["per CALGB-10403 / GMALL / BFM-inspired regimen (1L)",
                "nelarabine (R/R T-ALL)",
                "venetoclax + navitoclax (early-phase trials)"],
        sources=["SRC-CALGB-10403-STOCK-2019", "SRC-BLAST-GOKBUGET-2018"],
        notes="ESCAT IIIA. OncoKB Level 4. Favorable prognostic in some pediatric-T-ALL series when isolated; adverse with PTEN co-loss.",
    ))
    NOTCH1_CELLS.append(yaml_cell(
        cell_id="BMA-NOTCH1-ACTIVATING-CLL",
        biomarker_id="BIO-NOTCH1-MUTATION",
        variant_qualifier="activating (PEST domain truncating, c.7541_7542delCT canonical)",
        disease_id="DIS-CLL",
        escat_tier="IIIA", oncokb_level="3B",
        summary="""
            NOTCH1 activating mutations (~10-15% of CLL) — adverse
            prognostic; reduced response to anti-CD20 mAb (rituximab,
            obinutuzumab) in some studies. Venetoclax-based fixed-duration
            (CLL14) and BTKi continuous remain effective. Not directly
            targeted; selects venetoclax-based therapy when present.
        """,
        combos=["venetoclax + obinutuzumab (CLL14)", "acalabrutinib monotherapy", "zanubrutinib monotherapy"],
        contraindicated=["chlorambucil + obinutuzumab (relatively reduced anti-CD20 benefit per NOTCH1-mut subgroup)"],
        sources=["SRC-NCCN-BCELL-2025", "SRC-ESMO-CLL-2024"],
        notes="ESCAT IIIA. NOTCH1 mutation identifies a subgroup that may be especially well-served by venetoclax-based regimens vs anti-CD20-based chemoimmuno.",
    ))


add_notch1()


# ───────────────────────── MYC + BCL2 + CCND1 (heme rearrangements) ─────────
HEME_REARR_CELLS = []


def add_heme_rearr():
    # MYC rearrangement
    HEME_REARR_CELLS.append(yaml_cell(
        cell_id="BMA-MYC-REARRANGEMENT-BURKITT",
        biomarker_id="BIO-MYC-REARRANGEMENT",
        variant_qualifier="t(8;14) IGH/MYC (or t(2;8), t(8;22) — variant)",
        disease_id="DIS-BURKITT",
        escat_tier="IA", oncokb_level="1",
        summary="""
            MYC rearrangement (t(8;14) most common) is the defining genetic
            lesion of Burkitt lymphoma. Diagnosis requires MYC-R + appropriate
            morphology/IHC + absence of BCL2/BCL6 rearrangements (else HGBL-
            DH/TH). Treatment is intensive chemoimmunotherapy: DA-EPOCH-R
            (CALGB 50402, Roschewski et al. JCO 2020 / Blood 2021) for low/
            intermediate risk; CODOX-M/IVAC + R for high-risk/CNS+. Cure
            rates >85% with appropriate intensity.
        """,
        combos=["DA-EPOCH-R (low/intermediate-risk Burkitt)",
                "CODOX-M/IVAC + rituximab (high-risk/CNS+)",
                "R-hyperCVAD (alternative)"],
        sources=["SRC-NCCN-BCELL-2025", "SRC-ESMO-BURKITT-2024"],
        notes="ESCAT IA — defines the disease + drives intensive regimen choice. CNS prophylaxis mandatory. Avoid R-CHOP — undercure.",
    ))
    HEME_REARR_CELLS.append(yaml_cell(
        cell_id="BMA-MYC-REARRANGEMENT-HGBL-DH",
        biomarker_id="BIO-DOUBLE-HIT",
        variant_qualifier="MYC + BCL2 (DH) or MYC + BCL2 + BCL6 (TH)",
        disease_id="DIS-HGBL-DH",
        escat_tier="IIA", oncokb_level="3A",
        summary="""
            HGBL with MYC + BCL2 (and/or BCL6) rearrangements ('double-hit' /
            'triple-hit') has aggressive course with R-CHOP undercure. DA-
            EPOCH-R (Petrich JCO 2014; Dunleavy Blood 2018) shows superior
            CR/PFS in single-arm series. Pola-R-CHP (POLARIX, Tilly NEJM
            2022) approved for DLBCL — DH subgroup analysis numerically
            favorable. CAR-T (axi-cel, liso-cel) effective at 2L+.
        """,
        combos=["DA-EPOCH-R (1L preferred)",
                "pola-R-CHP (1L alternative)",
                "axi-cel / liso-cel (2L+)"],
        contraindicated=["R-CHOP alone (undercure in DH/TH per retrospective series)"],
        sources=["SRC-NCCN-BCELL-2025", "SRC-ESMO-DLBCL-2024"],
        notes="ESCAT IIA. CNS prophylaxis recommended. MYC-only rearrangement (single-hit) treated as DLBCL-NOS.",
    ))
    HEME_REARR_CELLS.append(yaml_cell(
        cell_id="BMA-MYC-REARRANGEMENT-DLBCL-NOS",
        biomarker_id="BIO-MYC-REARRANGEMENT",
        variant_qualifier="MYC rearrangement isolated (single-hit; no BCL2/BCL6)",
        disease_id="DIS-DLBCL-NOS",
        escat_tier="IIIA", oncokb_level="4",
        summary="""
            Isolated MYC rearrangement in DLBCL (without BCL2/BCL6) —
            adverse prognostic but not equivalent to DH/TH. Treat per
            DLBCL-NOS algorithm (R-CHOP or pola-R-CHP). Some experts
            consider DA-EPOCH-R intensification in young fit patients.
        """,
        combos=["R-CHOP (1L standard)", "pola-R-CHP (POLARIX)", "DA-EPOCH-R (intensification consideration)"],
        sources=["SRC-NCCN-BCELL-2025", "SRC-ESMO-DLBCL-2024"],
        notes="ESCAT IIIA. CNS-IPI scoring essential due to elevated CNS relapse risk.",
    ))
    # BCL2 rearrangement
    HEME_REARR_CELLS.append(yaml_cell(
        cell_id="BMA-BCL2-REARRANGEMENT-FL",
        biomarker_id="BIO-BCL2-REARRANGEMENT",
        variant_qualifier="t(14;18) IGH/BCL2",
        disease_id="DIS-FL",
        escat_tier="IIIA", oncokb_level="3B",
        summary="""
            t(14;18) IGH/BCL2 is the defining genetic lesion of follicular
            lymphoma (~85%). Drives constitutive BCL2 overexpression.
            Venetoclax monotherapy modest activity in FL (Davids JCO 2017
            ORR ~38%); combos with R-CHOP (CONTRALTO) and obinutuzumab in
            trial. Standard 1L (BR, R-CHOP, obinutuzumab + chemo) effective
            regardless of BCL2-R presence.
        """,
        combos=["BR or R-CHOP or O-CHOP/O-Benda (1L per FLIPI/burden)",
                "venetoclax + obinutuzumab (R/R, off-label)",
                "tazemetostat (EZH2-mut R/R)",
                "mosunetuzumab / axi-cel (R/R 3L+)"],
        sources=["SRC-NCCN-BCELL-2025", "SRC-ESMO-FL-2024"],
        notes="ESCAT IIIA. BCL2-R does not currently select frontline regimen — diagnostic/lineage marker.",
    ))
    HEME_REARR_CELLS.append(yaml_cell(
        cell_id="BMA-BCL2-REARRANGEMENT-DLBCL-NOS",
        biomarker_id="BIO-BCL2-REARRANGEMENT",
        variant_qualifier="t(14;18) IGH/BCL2 isolated (single-hit)",
        disease_id="DIS-DLBCL-NOS",
        escat_tier="IIIB", oncokb_level="4",
        summary="""
            Isolated BCL2 rearrangement in DLBCL (no MYC partner) — common
            in GCB-DLBCL transformed from FL. Not equivalent to DH lymphoma.
            Treat per DLBCL-NOS algorithm; venetoclax investigational.
        """,
        combos=["R-CHOP / pola-R-CHP per usual DLBCL algorithm"],
        sources=["SRC-NCCN-BCELL-2025"],
        notes="ESCAT IIIB. Distinct entity from HGBL-DH (which requires concurrent MYC-R).",
    ))
    HEME_REARR_CELLS.append(yaml_cell(
        cell_id="BMA-BCL2-EXPRESSION-CLL",
        biomarker_id="BIO-BCL2-EXPRESSION-IHC",
        variant_qualifier="BCL2 high expression (universal in CLL)",
        disease_id="DIS-CLL",
        escat_tier="IA", oncokb_level="1",
        summary="""
            CLL universally expresses BCL2 (no rearrangement needed; driven
            by miR-15/16 deletion at 13q14). Venetoclax-based fixed-duration
            (CLL14: VenO 1L; MURANO: VenR R/R) is FDA/EMA-approved and
            disease-defining as a target. Not biomarker-selected per se —
            BCL2 is a CLL-class marker.
        """,
        fda=["venetoclax + obinutuzumab — 1L CLL/SLL (FDA 2019)",
             "venetoclax + rituximab — R/R CLL (FDA 2018, MURANO)",
             "venetoclax monotherapy — R/R 17p-del CLL (FDA 2016)"],
        ema=["venetoclax + obinutuzumab — 1L CLL (EMA 2019)",
             "venetoclax + rituximab — R/R CLL (EMA 2018)"],
        combos=["venetoclax + obinutuzumab (1L)", "venetoclax + rituximab (R/R)", "venetoclax + ibrutinib (CAPTIVATE / GLOW)"],
        sources=["SRC-NCCN-BCELL-2025", "SRC-ESMO-CLL-2024"],
        notes="ESCAT IA. OncoKB Level 1. TLS prophylaxis mandatory at venetoclax ramp-up.",
    ))
    HEME_REARR_CELLS.append(yaml_cell(
        cell_id="BMA-BCL2-REARRANGEMENT-HGBL-DH",
        biomarker_id="BIO-BCL2-REARRANGEMENT",
        variant_qualifier="BCL2-R (component of double-hit; partner of MYC-R)",
        disease_id="DIS-HGBL-DH",
        escat_tier="IIA", oncokb_level="3A",
        summary="""
            BCL2-R as the partner of MYC-R defines HGBL-DH. Same management
            as MYC-R cell: DA-EPOCH-R 1L preferred per most series.
        """,
        combos=["DA-EPOCH-R", "pola-R-CHP", "CAR-T (R/R)"],
        sources=["SRC-NCCN-BCELL-2025"],
        notes="ESCAT IIA — paired with MYC-R cell BMA-MYC-REARRANGEMENT-HGBL-DH.",
    ))
    # CCND1 t(11;14)
    HEME_REARR_CELLS.append(yaml_cell(
        cell_id="BMA-CCND1-T1114-MCL",
        biomarker_id="BIO-T11-14-IGH-CCND1",
        variant_qualifier="t(11;14)(q13;q32) IGH/CCND1",
        disease_id="DIS-MCL",
        escat_tier="IA", oncokb_level="1",
        summary="""
            t(11;14) IGH/CCND1 is the defining genetic lesion of MCL — drives
            cyclin D1 overexpression. BTKi (acalabrutinib + rituximab — TRIANGLE,
            Dreyling Lancet 2024; ECHO — Wang NEJM 2024) is the new 1L standard
            regardless of fitness for TP53-mut; high-dose AraC + autoSCT
            historically (LyMa, MCL Younger). Venetoclax (CCND1 → BCL2-mediated
            anti-apoptosis rationale) active R/R.
        """,
        fda=["acalabrutinib + bendamustine + rituximab — 1L MCL (FDA 2024 ECHO)",
             "acalabrutinib monotherapy — R/R MCL (FDA 2017)",
             "zanubrutinib — R/R MCL (FDA 2019)",
             "ibrutinib — R/R MCL (FDA 2013, withdrawn 2023)",
             "brexucabtagene autoleucel — R/R MCL (FDA 2020 ZUMA-2)"],
        ema=["acalabrutinib — R/R MCL (EMA 2020)", "brexu-cel — R/R MCL (EMA 2020)"],
        combos=["acalabrutinib + bendamustine + rituximab (1L)",
                "BR or R-CHOP/R-DHAP + autoSCT (1L fit, TP53-WT)",
                "venetoclax + ibrutinib (R/R)",
                "brexu-cel (R/R 2L+)"],
        sources=["SRC-NCCN-BCELL-2025", "SRC-ESMO-MCL-2024"],
        notes="ESCAT IA. Disease-defining; doesn't 'select' BTKi but the DIS-MCL algorithm is BTKi-centric.",
    ))
    HEME_REARR_CELLS.append(yaml_cell(
        cell_id="BMA-CCND1-T1114-MM",
        biomarker_id="BIO-T11-14-IGH-CCND1",
        variant_qualifier="t(11;14)(q13;q32) IGH/CCND1",
        disease_id="DIS-MM",
        escat_tier="IIA", oncokb_level="3A",
        summary="""
            t(11;14) myeloma (~15-20%) — distinct biology with high BCL2/MCL1
            ratio. Venetoclax monotherapy (M14-032; Kumar Blood 2017 ORR ~40%)
            and venetoclax + dexamethasone (BELLINI subgroup; Kumar Lancet
            Oncol 2020) active. BELLINI raised mortality signal in non-t(11;14)
            arm — venetoclax is now t(11;14)-selected in MM. CANOVA Ph3
            (venetoclax + dex vs pomalidomide + dex in t(11;14) R/R MM) read
            out 2024.
        """,
        combos=["venetoclax + dexamethasone (R/R t(11;14)-selected, off-label NCCN-supported)",
                "venetoclax + carfilzomib + dex (NCT trials)"],
        contraindicated=["venetoclax in non-t(11;14) MM (BELLINI mortality signal)"],
        sources=["SRC-NCCN-MM-2025", "SRC-ESMO-MM-2023"],
        notes="ESCAT IIA. OncoKB Level 3A. FISH t(11;14) reflex testing should be standard at MM workup. NCCN listed as preferred R/R option in t(11;14)+ patients.",
    ))


add_heme_rearr()


def write_all(cells):
    for body in cells:
        # parse first line
        first = body.splitlines()[0]
        cid = first.split(":", 1)[1].strip()
        emit(cid, body)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    write_all(KRAS_CELLS)
    write_all(NRAS_CELLS)
    write_all(PIK3CA_CELLS)
    write_all(IDH_CELLS)
    write_all(TP53_CELLS)
    write_all(MYD88_CELLS)
    write_all(NOTCH1_CELLS)
    write_all(HEME_REARR_CELLS)
    print(
        f"wrote KRAS={len(KRAS_CELLS)} NRAS={len(NRAS_CELLS)} "
        f"PIK3CA={len(PIK3CA_CELLS)} IDH={len(IDH_CELLS)} "
        f"TP53={len(TP53_CELLS)} MYD88={len(MYD88_CELLS)} "
        f"NOTCH1={len(NOTCH1_CELLS)} HEME-REARR={len(HEME_REARR_CELLS)}"
    )
