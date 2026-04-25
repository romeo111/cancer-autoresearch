"""OpenOnco Pydantic schemas for the knowledge base.

Every entity under `hosted/content/<type>/` validates against one of
these models on load. See `validation/loader.py`.
"""

from .algorithm import Algorithm
from .biomarker import Biomarker
from .contraindication import Contraindication
from .disease import Disease
from .drug import Drug
from .indication import Indication
from .monitoring import MonitoringSchedule
from .plan import FDAComplianceMetadata, Plan, PlanAnnotation, PlanTrack
from .red_flag import RedFlag
from .regimen import Regimen
from .source import Source
from .supportive_care import SupportiveCare
from .test import Test

# Map content directory name → entity class.
# Used by the loader to pick the right schema for each YAML file.
# Plan is NOT included — Plan instances live outside the public KB
# (in patient_plans/<patient_id>/v<N>.yaml, gitignored per CHARTER §9.3).
ENTITY_BY_DIR: dict[str, type] = {
    "diseases": Disease,
    "drugs": Drug,
    "regimens": Regimen,
    "indications": Indication,
    "biomarkers": Biomarker,
    "contraindications": Contraindication,
    "redflags": RedFlag,
    "algorithms": Algorithm,
    "tests": Test,
    "supportive_care": SupportiveCare,
    "monitoring": MonitoringSchedule,
    "sources": Source,
}

__all__ = [
    "Algorithm",
    "Biomarker",
    "Contraindication",
    "Disease",
    "Drug",
    "ENTITY_BY_DIR",
    "FDAComplianceMetadata",
    "Indication",
    "MonitoringSchedule",
    "Plan",
    "PlanAnnotation",
    "PlanTrack",
    "RedFlag",
    "Regimen",
    "Source",
    "SupportiveCare",
    "Test",
]
