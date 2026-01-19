"""Integration tests for Claude SDK session manager.

These tests make real API calls to Claude and require API credentials.
"""

import uuid

import pytest

from task_orchestrator.claude.session_manager import SessionManager
from task_orchestrator.factory import create_claude_client_factory


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_session_and_send_prompt() -> None:
    """Test creating a session and sending a simple prompt."""
    # Create session manager and client factory
    manager = SessionManager()
    factory = create_claude_client_factory()

    # Generate session ID
    session_id = str(uuid.uuid4())

    # Create session
    client = factory()
    session = await manager.create_session(session_id, client)

    assert session is not None
    assert manager.get(session_id) == session

    try:
        # Send a simple math prompt
        prompt = "What is 2+2? Answer with just the number."
        response = await manager.send_prompt(session_id, prompt)

        # Verify we got a response
        assert response is not None
        assert len(response) > 0
        assert "4" in response

        # Verify message history
        assert len(session.messages) == 2
        assert session.messages[0]["role"] == "user"
        assert session.messages[0]["content"] == prompt
        assert session.messages[1]["role"] == "assistant"
        assert session.messages[1]["content"] == response

    finally:
        # Cleanup: close session
        await session.close()
        manager.pop(session_id)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_session_not_found() -> None:
    """Test sending prompt to non-existent session raises error."""
    manager = SessionManager()

    with pytest.raises(ValueError, match="Session not found"):
        await manager.send_prompt("non-existent-id", "test prompt")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_multiple_prompts_in_session() -> None:
    """Test sending multiple prompts to the same session."""
    manager = SessionManager()
    factory = create_claude_client_factory()

    session_id = str(uuid.uuid4())
    client = factory()
    session = await manager.create_session(session_id, client)

    try:
        # First prompt
        response1 = await manager.send_prompt(session_id, "What is 5+3?")
        assert "8" in response1

        # Second prompt (should maintain context)
        response2 = await manager.send_prompt(session_id, "Add 2 to that number.")
        assert "10" in response2

        # Verify message history has 4 messages (2 user, 2 assistant)
        assert len(session.messages) == 4

    finally:
        await session.close()
        manager.pop(session_id)
