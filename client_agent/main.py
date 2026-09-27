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
    """Launch the SLMS Client Agent in interactive CLI mode."""
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
