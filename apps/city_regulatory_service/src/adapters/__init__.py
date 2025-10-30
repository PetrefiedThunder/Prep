"""City-specific ingestion adapters."""

from .new_york_adapter import NewYorkCityAdapter
from .san_francisco_adapter import SanFranciscoAdapter

__all__ = ["SanFranciscoAdapter", "NewYorkCityAdapter"]
