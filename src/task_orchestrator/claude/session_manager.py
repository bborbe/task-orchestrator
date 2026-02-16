"""Session manager for Claude SDK clients."""

import asyncio
import logging

from claude_code_sdk import ClaudeCodeOptions, ClaudeSDKClient

logger = logging.getLogger(__name__)


class Session:
    """Holds a Claude SDK client and its conversation state."""

    def __init__(self, client: ClaudeSDKClient) -> None:
        """Initialize session with a Claude SDK client."""
        self.client = client
        self.messages: list[dict[str, str]] = []

    async def start(self) -> None:
        """Initialize the Claude client session."""
        await self.client.__aenter__()

    async def close(self) -> None:
        """Close the Claude client session."""
        await self.client.__aexit__(None, None, None)


class SessionManager:
    """Manages Claude SDK sessions."""

    def __init__(self) -> None:
        """Initialize session manager with empty session dict."""
        self._sessions: dict[str, Session] = {}

    def get(self, session_id: str) -> Session | None:
        """Get session by ID."""
        return self._sessions.get(session_id)

    def set(self, session_id: str, session: Session) -> None:
        """Store session by ID."""
        self._sessions[session_id] = session

    def pop(self, session_id: str) -> Session | None:
        """Remove and return session by ID."""
        return self._sessions.pop(session_id, None)

    async def create_session(self, session_id: str, client: ClaudeSDKClient) -> Session:
        """Create and start a new session."""
        session = Session(client)
        await session.start()
        self.set(session_id, session)
        return session

    async def _consume_session_messages(
        self, client: ClaudeSDKClient, session_id: str, started_consuming: asyncio.Event
    ) -> None:
        """Consume remaining messages from a session to keep it alive.

        Args:
            client: The Claude SDK client
            session_id: Session ID for logging
            started_consuming: Event to set when consumption starts
        """
        try:
            started_consuming.set()
            logger.info(f"Background task consuming messages for session {session_id}")
            async for _message in client.receive_response():
                pass  # Just consume messages to keep connection alive
            logger.info(f"Background task finished for session {session_id}")
        except Exception as e:
            logger.error(f"Error in background message consumer for {session_id}: {e}")

    async def start_session(self, prompt: str, cwd: str | None = None) -> str:
        """Start a session and return session_id quickly while keeping connection alive.

        Returns session_id after first AssistantMessage, then spawns background task
        to consume remaining messages and keep session alive.

        Args:
            prompt: The prompt to send
            cwd: Working directory for the session

        Returns:
            session_id
        """
        from claude_code_sdk import AssistantMessage, SystemMessage

        options = (
            ClaudeCodeOptions(model="sonnet", permission_mode="acceptEdits", cwd=cwd)
            if cwd
            else ClaudeCodeOptions(model="sonnet", permission_mode="acceptEdits")
        )
        client = ClaudeSDKClient(options=options)
        session_id: str | None = None
        session_ready = False

        logger.info(f"Starting session: {prompt} (cwd={cwd})")

        # Enter async context but don't use 'with' - we'll manage cleanup manually
        await client.__aenter__()

        try:
            await client.query(prompt)
            logger.info("Query sent, waiting for session_id")

            async for message in client.receive_response():
                # Extract session_id from init message
                if isinstance(message, SystemMessage) and message.subtype == "init":
                    session_id = message.data.get("session_id")
                    logger.info(f"Got session_id from SystemMessage: {session_id}")

                # Wait for first AssistantMessage to ensure session is ready
                if isinstance(message, AssistantMessage):
                    logger.info("Session ready (received first AssistantMessage)")
                    session_ready = True

                    # Spawn background task to consume remaining messages
                    started_consuming = asyncio.Event()
                    asyncio.create_task(self._consume_session_messages(client, session_id, started_consuming))
                    # Wait briefly to ensure background task starts
                    await started_consuming.wait()

                    # Return immediately, background task will keep connection alive
                    return session_id

            # If we get here, something went wrong
            if not session_id:
                raise ValueError("Did not receive session_id from Claude")
            if not session_ready:
                raise ValueError("Session not ready (no AssistantMessage received)")

        except Exception:
            # On error, clean up properly
            await client.__aexit__(None, None, None)
            raise

        return session_id

    async def send_prompt(self, prompt: str, cwd: str | None = None) -> tuple[str, str]:
        """Send a prompt and get the session_id from Claude.

        Args:
            prompt: The prompt to send
            cwd: Working directory for the session

        Returns:
            Tuple of (session_id, response_text)
        """
        from claude_code_sdk import AssistantMessage, SystemMessage, TextBlock

        options = (
            ClaudeCodeOptions(model="sonnet", permission_mode="acceptEdits", cwd=cwd)
            if cwd
            else ClaudeCodeOptions(model="sonnet", permission_mode="acceptEdits")
        )
        client = ClaudeSDKClient(options=options)
        session_id: str | None = None
        response_text = ""

        logger.info(f"Sending query: {prompt} (cwd={cwd})")

        async with client:
            await client.query(prompt)
            logger.info("Query sent, waiting for response")

            async for message in client.receive_response():
                # Extract session_id from init message
                if isinstance(message, SystemMessage) and message.subtype == "init":
                    session_id = message.data.get("session_id")
                    logger.info(f"Got session_id from SystemMessage: {session_id}")

                # Collect text response
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            response_text += block.text

        if not session_id:
            raise ValueError("Did not receive session_id from Claude")

        logger.info(f"Session {session_id} created, response length: {len(response_text)} chars")
        return session_id, response_text
