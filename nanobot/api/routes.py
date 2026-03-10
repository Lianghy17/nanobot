"""API routes for ChatBI service."""
import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from nanobot.agent.core import Agent
from nanobot.agent.skills.registry import SkillRegistry
from nanobot.api.skill_loader import SkillLoader
from nanobot.config.settings import Settings, get_settings
from nanobot.scene.manager import SceneManager
from nanobot.session.manager import Session, SessionManager

router = APIRouter()


class ChatRequest(BaseModel):
    """Chat request model."""
    message: str = Field(..., description="User message")
    scene_code: str = Field(..., description="Scene code")
    session_id: str | None = Field(None, description="Session ID (auto-generated if None)")
    user_id: str = Field(default="default", description="User identifier")
    stream: bool = Field(default=True, description="Enable streaming response")


class ChatResponse(BaseModel):
    """Chat response model."""
    session_id: str
    response: str
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)


async def get_skill_registry() -> SkillRegistry:
    """Get skill registry instance."""
    return SkillLoader.get_registry()


async def get_session_manager(settings: Settings = Depends(get_settings)) -> SessionManager:
    """Get session manager instance."""
    from pathlib import Path
    return SessionManager(Path(settings.session_storage_path))


async def get_agent(
    skill_registry: SkillRegistry = Depends(get_skill_registry),
    settings: Settings = Depends(get_settings),
) -> Agent:
    """Get agent instance."""
    return Agent(
        skill_registry=skill_registry,
        model=settings.llm_model,
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
    )


async def get_scene_manager() -> SceneManager:
    """Get scene manager instance."""
    return SceneManager()


@router.get("/scenes")
async def list_scenes(scene_manager: SceneManager = Depends(get_scene_manager)):
    """List all available scenes."""
    return scene_manager.list_scenes()


@router.get("/scenes/{scene_code}")
async def get_scene(
    scene_code: str,
    scene_manager: SceneManager = Depends(get_scene_manager),
):
    """Get scene configuration."""
    scene = scene_manager.get_scene(scene_code)
    if not scene:
        raise HTTPException(status_code=404, detail=f"Scene '{scene_code}' not found")
    return {
        "scene_code": scene.scene_code,
        "scene_name": scene.scene_name,
        "description": scene.description,
        "enabled_skills": scene.enabled_skills,
    }


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    session_manager: SessionManager = Depends(get_session_manager),
    agent: Agent = Depends(get_agent),
    scene_manager: SceneManager = Depends(get_scene_manager),
):
    """Send a message and get a response (non-streaming)."""
    scene = scene_manager.get_scene(request.scene_code)
    if not scene:
        raise HTTPException(status_code=404, detail=f"Scene '{request.scene_code}' not found")

    session_key = request.session_id or f"{request.user_id}:{request.scene_code}"
    session = await session_manager.get_or_create(key=session_key, user_id=request.user_id)

    response_content = ""
    tool_calls = []

    async for event in agent.process_message(session, request.message, scene):
        if event["type"] == "tool_call":
            tool_calls.append(event)
        elif event["type"] == "content":
            response_content = event["content"]

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
    scene_manager: SceneManager = Depends(get_scene_manager),
):
    """Send a message and get a streaming response."""

    async def event_generator():
        scene = scene_manager.get_scene(request.scene_code)
        if not scene:
            error_msg = f"Scene '{request.scene_code}' not found"
            yield f"data: {json.dumps({'type': 'error', 'message': error_msg}, ensure_ascii=False)}\n\n"
            return

        session_key = request.session_id or f"{request.user_id}:{request.scene_code}"
        session = await session_manager.get_or_create(key=session_key, user_id=request.user_id)

        try:
            async for event in agent.process_message(session, request.message, scene):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"
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


@router.get("/skills")
async def list_skills(skill_registry: SkillRegistry = Depends(get_skill_registry)):
    """List all available skills."""
    skills = []
    for name in skill_registry.list_skills():
        skill = skill_registry.get(name)
        if skill:
            skills.append({
                "name": skill.name,
                "description": skill.description,
                "category": skill.category,
                "parameters": skill.parameters,
            })
    return skills
