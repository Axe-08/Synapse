# synapse/workers/__init__.py
"""
synapse.workers — pipeline worker package.

Exports all worker functions so callers can use:
    from synapse.workers import ingestion_worker, analysis_worker, ...

ingestion_worker is imported lazily when DISABLE_INGESTION=false (laptop mode)
because it depends on undetected_chromedriver which is not installed on DGX.
"""
import os

from .calibration import calibration_worker
from .analysis import analysis_worker
from .implementation import implementation_worker
from .vjs import vjs_worker
from .assembly import data_assembly_worker

# Only import ingestion on the laptop (DISABLE_INGESTION not set, or false)
_disable_ingestion = os.getenv('DISABLE_INGESTION', 'false').lower() == 'true'
if not _disable_ingestion:
    from .ingestion import ingestion_worker
else:
    # Placeholder so `from synapse.workers import ingestion_worker` doesn't break
    # callers that import it unconditionally (e.g. main.py before the guard)
    def ingestion_worker(*args, **kwargs):  # type: ignore[misc]
        raise RuntimeError("ingestion_worker is disabled on this node (DISABLE_INGESTION=true)")

__all__ = [
    "ingestion_worker",
    "calibration_worker",
    "analysis_worker",
    "implementation_worker",
    "vjs_worker",
    "data_assembly_worker",
]
