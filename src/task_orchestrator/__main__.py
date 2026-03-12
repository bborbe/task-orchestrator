"""TaskOrchestrator main application."""

import logging
import sys

import uvicorn

from task_orchestrator.api.tasks import set_connection_manager as tasks_set_connection_manager
from task_orchestrator.api.websocket import set_connection_manager
from task_orchestrator.factory import (
    create_app,
    get_config,
    get_connection_manager,
)

# Create app instance at module level for uvicorn --reload (make watch)
app = create_app()


def main() -> int:
    """Run the application."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s [%(name)s:%(lineno)d] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    try:
        # Inject connection manager into WebSocket routes
        set_connection_manager(get_connection_manager())

        # Inject connection manager into task routes (for post-command broadcasts)
        tasks_set_connection_manager(get_connection_manager())

        config = get_config()
        uvicorn.run(
            app,
            host=config.host,
            port=config.port,
            log_level="info",
        )
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
