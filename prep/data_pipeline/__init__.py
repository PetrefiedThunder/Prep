"""High throughput data streaming utilities for Prep analytics."""

from .cdc import CDCStreamManager, build_cdc_stream

__all__ = ["CDCStreamManager", "build_cdc_stream"]
