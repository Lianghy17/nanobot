"""API routes for the nanobot service."""
import asyncio
import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from nanobot.agent.core import Agent
from nanobot.agent.tools.registry import ToolRegistry
from nanobot.config.settings import Settings, get_settings
from nanobot.session.manager import Session, SessionManager, SessionState

router = APIRouter()


# === Request/Response Models ===


class ChatRequest(BaseModel):
    """Chat request model."""

    message: str = Field(..., description="User message")
    session_id: str | None = Field(None, description="Session ID (auto-generated if None)")
    user_id: str = Field(..., description="User identifier")
    stream: bool = Field(default=True, description="Enable streaming response")


class ChatResponse(BaseModel):
    """Chat response model."""

    session_id: str
    response: str
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)


class SessionInfo(BaseModel):
    """Session information model."""

    session_id: str
    user_id: str | None
    state: str
    message_count: int
    created_at: float
    updated_at: float


class SessionAction(BaseModel):
    """Session action request model."""

    action: str = Field(..., description="Action: pause, resume, clear, delete")


class ToolInfo(BaseModel):
    """Tool information model."""

    name: str
    description: str
    parameters: dict[str, Any]


# === Dependencies ===


async def get_session_manager(
    settings: Settings = Depends(get_settings),
) -> SessionManager:
    """Get session manager instance."""
    storage_path = Path(settings.session_storage_path)
    return SessionManager(storage_path)


async def get_agent(
    tool_registry: ToolRegistry = Depends(lambda: ToolRegistry()),
    settings: Settings = Depends(get_settings),
) -> Agent:
    """Get agent instance."""
    return Agent(
        tool_registry=tool_registry,
        model=settings.llm_model,
    )


# === Chat Endpoints ===


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    session_manager: SessionManager = Depends(get_session_manager),
    agent: Agent = Depends(get_agent),
):
    """Send a message and get a response (non-streaming)."""
    # Get or create session
    session_key = request.session_id or f"{request.user_id}:default"
    session = await session_manager.get_or_create(
        key=session_key, user_id=request.user_id
    )

    # Check if session is paused
    if session.is_paused():
        raise HTTPException(
            status_code=409, detail="Session is paused. Resume it first."
        )

    # Process message
    response_content = ""
    tool_calls = []

    async for event in agent.process_message(session, request.message):
        if event["type"] == "tool_call":
            tool_calls.append(event)
        elif event["type"] == "content":
            response_content = event["content"]

    # Save session
    await session_manager.save(session)

    return ChatResponse(
        session_id=session.key,
        response=response_content,
        tool_calls=tool_calls,
    )


@router.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    session_manager: SessionManager = Depends(get_session_manager),
    agent: Agent = Depends(get_agent),
):
    """Send a message and get a streaming response."""

    async def event_generator():
        # Get or create session
        session_key = request.session_id or f"{request.user_id}:default"
        session = await session_manager.get_or_create(
            key=session_key, user_id=request.user_id
        )

        if session.is_paused():
            yield f"data: {json.dumps({'type': 'error', 'message': 'Session is paused'})}\n\n"
            return

        try:
            async for event in agent.process_message(session, request.message):
                yield f"data: {json.dumps(event)}\n\n"
        except asyncio.CancelledError:
            # User disconnected
            session.add_message("system", "User interrupted the response")
            await session_manager.save(session)
            yield f"data: {json.dumps({'type': 'error', 'message': 'Stream interrupted'})}\n\n"
        finally:
            await session_manager.save(session)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# === Session Endpoints ===


@router.get("/sessions", response_model=list[SessionInfo])
async def list_sessions(
    user_id: str | None = Query(None, description="Filter by user ID"),
    session_manager: SessionManager = Depends(get_session_manager),
):
    """List all sessions, optionally filtered by user."""
    sessions_info = []

    for key in session_manager.get_all_keys():
        session = await session_manager.get_or_create(key)
        if user_id is None or session.metadata.get("user_id") == user_id:
            sessions_info.append(
                SessionInfo(
                    session_id=session.key,
                    user_id=session.metadata.get("user_id"),
                    state=session.state.value,
                    message_count=len(session.messages),
                    created_at=session.created_at,
                    updated_at=session.updated_at,
                )
            )

    return sessions_info


@router.get("/sessions/{session_id}", response_model=SessionInfo)
async def get_session(
    session_id: str,
    session_manager: SessionManager = Depends(get_session_manager),
):
    """Get session information."""
    session = await session_manager.get_or_create(session_id)

    return SessionInfo(
        session_id=session.key,
        user_id=session.metadata.get("user_id"),
        state=session.state.value,
        message_count=len(session.messages),
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


@router.post("/sessions/{session_id}/action")
async def session_action(
    session_id: str,
    action_request: SessionAction,
    session_manager: SessionManager = Depends(get_session_manager),
):
    """Perform an action on a session (pause, resume, clear, delete)."""
    session = await session_manager.get_or_create(session_id)

    action = action_request.action.lower()

    if action == "pause":
        session.pause()
        await session_manager.save(session)
        return {"status": "success", "message": f"Session {session_id} paused"}

    elif action == "resume":
        session.resume()
        await session_manager.save(session)
        return {"status": "success", "message": f"Session {session_id} resumed"}

    elif action == "clear":
        session.clear()
        await session_manager.save(session)
        return {"status": "success", "message": f"Session {session_id} cleared"}

    elif action == "delete":
        await session_manager.delete(session_id)
        return {"status": "success", "message": f"Session {session_id} deleted"}

    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown action: {action}. Valid actions: pause, resume, clear, delete",
        )


@router.get("/sessions/{session_id}/history")
async def get_session_history(
    session_id: str,
    max_messages: int = Query(50, description="Maximum messages to return"),
    session_manager: SessionManager = Depends(get_session_manager),
):
    """Get session message history."""
    session = await session_manager.get_or_create(session_id)
    return {"session_id": session_id, "messages": session.get_history(max_messages)}


# === Tool Endpoints ===


@router.get("/tools", response_model=list[ToolInfo])
async def list_tools(
    tool_registry: ToolRegistry = Depends(lambda: ToolRegistry()),
):
    """List all available tools."""
    # Register default tools
    from nanobot.agent.tools.rag_tool import RAGTool
    from nanobot.agent.tools.sql_tool import SQLTool
    from nanobot.agent.tools.time_series_tool import TimeSeriesForecastTool

    if not tool_registry.get("rag_search"):
        tool_registry.register(RAGTool())
    if not tool_registry.get("sql_execute"):
        tool_registry.register(SQLTool())
    if not tool_registry.get("time_series_forecast"):
        tool_registry.register(TimeSeriesForecastTool())

    tools = []
    for name in tool_registry.list_tools():
        tool = tool_registry.get(name)
        if tool:
            tools.append(
                ToolInfo(
                    name=tool.name,
                    description=tool.description,
                    parameters=tool.parameters,
                )
            )

    return tools


@router.post("/tools/{tool_name}/execute")
async def execute_tool(
    tool_name: str,
    params: dict[str, Any],
    tool_registry: ToolRegistry = Depends(lambda: ToolRegistry()),
):
    """Execute a specific tool with given parameters."""
    # Register default tools
    from nanobot.agent.tools.rag_tool import RAGTool
    from nanobot.agent.tools.sql_tool import SQLTool
    from nanobot.agent.tools.time_series_tool import TimeSeriesForecastTool

    if not tool_registry.get("rag_search"):
        tool_registry.register(RAGTool())
    if not tool_registry.get("sql_execute"):
        tool_registry.register(SQLTool())
    if not tool_registry.get("time_series_forecast"):
        tool_registry.register(TimeSeriesForecastTool())

    result = await tool_registry.execute(tool_name, params)
    return {"tool": tool_name, "params": params, "result": result}
