"""TaskOrchestrator main application."""

import logging
import sys

import uvicorn

from task_orchestrator.factory import create_app, get_config

# Create app instance for uvicorn
app = create_app()


def main() -> int:
    """Run the application."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    config = get_config()

    # Run server with app from module level
    uvicorn.run(
        app,
        host=config.host,
        port=config.port,
        log_level="info",
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
