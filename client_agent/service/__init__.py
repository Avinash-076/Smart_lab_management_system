"""
SLMS Windows Service Package.

Provides Windows Service host, lifecycle state management, and SCM integration
for the SLMS Client Agent.
"""

from service.lifecycle import ServiceLifecycle, ServiceState

__all__ = [
    "ServiceLifecycle",
    "ServiceState",
]
