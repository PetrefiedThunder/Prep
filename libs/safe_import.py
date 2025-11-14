"""Safe dynamic module import with clear error messages.

Use this wrapper instead of importlib.import_module directly to get:
- Clear error messages with troubleshooting hints
- PYTHONPATH information in errors
- Logging of import failures
- Consistent error handling across the codebase
"""

import importlib
import logging
import os
import sys
from typing import Any

logger = logging.getLogger(__name__)


def safe_import(module_str: str, *, optional: bool = False) -> Any:
    """Import a module by string name with defensive error handling.

    Args:
        module_str: Module path to import (e.g., "api.routes.city_fees")
        optional: If True, return None instead of raising on import failure

    Returns:
        The imported module object, or None if optional=True and import fails

    Raises:
        RuntimeError: If module cannot be imported and optional=False

    Example:
        >>> module = safe_import("api.routes.city_fees")
        >>> router = getattr(module, "router")

        >>> module = safe_import("plugins.optional", optional=True)
        >>> if module is None:
        >>>     logger.warning("Optional plugin not available")
    """
    try:
        return importlib.import_module(module_str)
    except ModuleNotFoundError as e:
        pythonpath = os.environ.get("PYTHONPATH", "<not set>")
        sys_path = sys.path

        error_msg = (
            f"Module '{module_str}' not found.\n"
            f"  Original error: {e}\n"
            f"  PYTHONPATH: {pythonpath}\n"
            f"  sys.path: {sys_path[:3]}...\n"
            f"\n"
            f"Troubleshooting:\n"
            f"  1. Verify the module exists in the codebase\n"
            f"  2. Ensure the package is installed: pip install -e .\n"
            f"  3. Check __init__.py files exist in parent packages\n"
            f"  4. Set PYTHONPATH if running outside the container:\n"
            f"     export PYTHONPATH=.\n"
        )

        logger.error("Failed to import %s: %s", module_str, error_msg, exc_info=True)

        if optional:
            logger.info("Module %s is optional, continuing without it", module_str)
            return None

        raise RuntimeError(error_msg) from e

    except ImportError as e:
        # Different from ModuleNotFoundError - module exists but has import errors
        error_msg = (
            f"Module '{module_str}' has import errors.\n"
            f"  Error: {e}\n"
            f"\n"
            f"Troubleshooting:\n"
            f"  1. Check the module's dependencies are installed\n"
            f"  2. Look for circular import issues\n"
            f"  3. Verify required environment variables are set\n"
        )

        logger.error("Import error in %s: %s", module_str, error_msg, exc_info=True)

        if optional:
            logger.info("Module %s is optional, continuing without it", module_str)
            return None

        raise RuntimeError(error_msg) from e

    except Exception as e:
        # Catch-all for other errors during import (AttributeError, etc.)
        error_msg = f"Unexpected error importing '{module_str}': {e}"
        logger.error(error_msg, exc_info=True)

        if optional:
            logger.info("Module %s is optional, continuing without it", module_str)
            return None

        raise RuntimeError(error_msg) from e


def safe_import_attr(module_str: str, attr_name: str, *, optional: bool = False) -> Any:
    """Import a module and get a specific attribute with error handling.

    Args:
        module_str: Module path to import
        attr_name: Attribute name to get from the module
        optional: If True, return None instead of raising on failure

    Returns:
        The attribute value, or None if optional=True and import/attr fails

    Raises:
        RuntimeError: If module or attribute not found and optional=False

    Example:
        >>> router = safe_import_attr("api.routes.city_fees", "router")
        >>> handler = safe_import_attr("plugins.optional", "handler", optional=True)
    """
    module = safe_import(module_str, optional=optional)
    if module is None:
        return None

    try:
        return getattr(module, attr_name)
    except AttributeError as e:
        error_msg = (
            f"Module '{module_str}' has no attribute '{attr_name}'.\n"
            f"  Available attributes: {dir(module)}\n"
        )
        logger.error(error_msg)

        if optional:
            return None

        raise RuntimeError(error_msg) from e
