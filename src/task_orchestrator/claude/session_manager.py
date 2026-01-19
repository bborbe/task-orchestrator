"""Session manager for Claude SDK clients."""

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
