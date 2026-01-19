"""TaskOrchestrator main application."""

import logging
import sys

import uvicorn

from task_orchestrator.api.tasks import set_session_manager
from task_orchestrator.api.websocket import set_connection_manager
from task_orchestrator.claude.session_manager import SessionManager
from task_orchestrator.factory import (
    create_app,
    get_config,
    get_connection_manager,
    start_task_watchers,
    stop_task_watchers,
)

# Create session manager
session_manager = SessionManager()

# Create app instance for uvicorn
app = create_app()

# Inject session manager into API routes
set_session_manager(session_manager)

# Inject connection manager into WebSocket routes
set_connection_manager(get_connection_manager())


# Lifecycle events
@app.on_event("startup")
async def startup_event() -> None:
    """Initialize watchers on application startup."""
    logging.info("[Main] Starting task watchers...")
    start_task_watchers()


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """Clean up watchers on application shutdown."""
    logging.info("[Main] Stopping task watchers...")
    stop_task_watchers()


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
