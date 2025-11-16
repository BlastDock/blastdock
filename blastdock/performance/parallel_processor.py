"""Parallel processing module

QUAL-009 WARNING: This module returns placeholder data only.
Real parallel processing is not implemented. Templates are NOT processed in parallel.
"""

import warnings
from ..utils.logging import get_logger

logger = get_logger(__name__)


class ParallelProcessor:
    """Handles parallel processing (QUAL-009 FIX: Stub implementation - no actual parallelization)"""

    def process_templates_parallel(self, templates):
        """Process templates in parallel

        QUAL-009 WARNING: This method returns PLACEHOLDER DATA ONLY.
        No actual parallel processing occurs. Templates are NOT processed.

        Args:
            templates: List of templates (not actually processed)

        Returns:
            dict: Placeholder processing metrics (NOT REAL DATA)
        """
        # QUAL-009 FIX: Add warning that this doesn't actually process anything
        warnings.warn(
            "ParallelProcessor.process_templates_parallel() returns placeholder data only. "
            "No actual parallel processing is implemented. Templates are NOT processed.",
            category=UserWarning,
            stacklevel=2,
        )
        logger.warning(
            f"QUAL-009: Returning placeholder parallel processing stats for {len(templates)} templates (not real data)"
        )

        return {
            "processed": len(templates),
            "time_taken": 2.5,
            "parallel_jobs": 4,
            "efficiency": 85.2,
            "_warning": "PLACEHOLDER DATA - NO ACTUAL PARALLEL PROCESSING OCCURRED",
        }


_parallel_processor = None


def get_parallel_processor():
    """Get parallel processor instance"""
    global _parallel_processor
    if _parallel_processor is None:
        _parallel_processor = ParallelProcessor()
    return _parallel_processor
