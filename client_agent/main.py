"""
SLMS Client Agent - Interactive CLI Entry Point.

Clean, thin entry point responsible solely for:
- CLI startup
- Initializing and starting the AgentRuntime
- Top-level exception and keyboard interrupt handling
"""

from __future__ import annotations

import sys

from core.logger import logger
from core.runtime import AgentRuntime


def main() -> None:
    """Launch the SLMS Client Agent in interactive CLI or Service mode."""
    # Dispatch to service controller if invoked with SCM or service management arguments
    if len(sys.argv) > 1 and sys.argv[1].lower() in (
        "run", "--service", "--startup", "service", "install", "uninstall", "start", "stop", "status", "debug", "enroll", "configure-acl", "verify-credentials", "--help", "-h", "help"
    ):
        if sys.argv[1].lower() == "service":
            sys.argv.pop(1)
        from service.service import main as service_main
        service_main()
        return

    logger.info("Initializing SLMS Client Agent (Interactive Mode)...")
    runtime = AgentRuntime(is_service=False)
    try:
        runtime.start()
    except KeyboardInterrupt:
        logger.info("Client agent stopped by user.")
    except Exception as e:
        logger.exception(f"Fatal client agent error: {e}")
        sys.exit(1)
    finally:
        runtime.stop()


if __name__ == "__main__":
    main()
