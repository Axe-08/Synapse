# synapse/workers/__init__.py
"""
synapse.workers — pipeline worker package.

Exports all worker functions so callers can use:
    from synapse.workers import ingestion_worker, analysis_worker, ...

This is a pure structural refactor; all logic lives in the submodules.
"""
from .ingestion import ingestion_worker
from .calibration import calibration_worker
from .analysis import analysis_worker
from .implementation import implementation_worker
from .vjs import vjs_worker
from .assembly import data_assembly_worker

__all__ = [
    "ingestion_worker",
    "calibration_worker",
    "analysis_worker",
    "implementation_worker",
    "vjs_worker",
    "data_assembly_worker",
]
