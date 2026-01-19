"""TaskOrchestrator main application."""

import logging
import sys

import uvicorn

from task_orchestrator.api.tasks import set_session_manager
from task_orchestrator.claude.session_manager import SessionManager
from task_orchestrator.factory import create_app, get_config

# Create session manager
session_manager = SessionManager()

# Create app instance for uvicorn
app = create_app()

# Inject session manager into API routes
set_session_manager(session_manager)


def main() -> int:
    """Run the application."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s [%(name)s:%(lineno)d] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
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
