from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from core.logger import logger


@dataclass
class CollectorError:
    collector_name: str
    operation: str
    error_type: str
    message: str
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "collector_name": self.collector_name,
            "operation": self.operation,
            "error_type": self.error_type,
            "message": self.message,
            "timestamp": self.timestamp,
        }


@dataclass
class CollectionResult:
    status: str  # "success", "failed", "empty"
    data: Any = None
    error: Optional[CollectorError] = None
    collected_at: float = field(default_factory=time.time)

    @property
    def is_success(self) -> bool:
        return self.status == "success"

    @property
    def is_failed(self) -> bool:
        return self.status in ("failed", "error")

    @property
    def is_empty(self) -> bool:
        return self.status == "empty"

    def get(self, key: str, default: Any = None) -> Any:
        if isinstance(self.data, dict):
            return self.data.get(key, default)
        return default

    def __getitem__(self, key: str) -> Any:
        if isinstance(self.data, dict):
            return self.data[key]
        if isinstance(self.data, (list, tuple)) and isinstance(key, int):
            return self.data[key]
        raise KeyError(key)

    def __contains__(self, item: Any) -> bool:
        if self.data is not None:
            return item in self.data
        return False

    def __iter__(self):
        if self.data is not None:
            return iter(self.data)
        return iter(())

    def __len__(self) -> int:
        if self.data is not None:
            return len(self.data)
        return 0

    def __bool__(self) -> bool:
        if self.is_failed:
            return False
        if self.data is not None:
            if isinstance(self.data, (list, dict, set, str)):
                return len(self.data) > 0
            return True
        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "data": self.data,
            "error": self.error.to_dict() if self.error else None,
            "collected_at": self.collected_at,
        }


def safe_run(
    module_name: str,
    function: Callable[[], Any],
    operation: str = "collect",
) -> CollectionResult:
    """
    Safely execute a collector function with structured diagnostic context.
    Prevents silent failure conversion to 0.
    """
    now = time.time()
    try:
        raw_result = function()

        if isinstance(raw_result, CollectionResult):
            return raw_result

        # Determine status: distinguish genuine numeric 0 from empty/none
        if raw_result is None:
            status = "empty"
        elif isinstance(raw_result, (list, dict, set)) and len(raw_result) == 0:
            status = "empty"
        else:
            status = "success"

        logger.info(f"{module_name} collected successfully (status={status})")
        return CollectionResult(
            status=status,
            data=raw_result,
            error=None,
            collected_at=now,
        )

    except Exception as e:
        logger.error(f"{module_name} failed: {e}")
        err = CollectorError(
            collector_name=module_name,
            operation=operation,
            error_type=type(e).__name__,
            message=str(e),
            timestamp=now,
        )
        return CollectionResult(
            status="failed",
            data=None,
            error=err,
            collected_at=now,
        )
