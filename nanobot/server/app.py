"""Flask server for nanobot REST API."""

import asyncio
import threading
from flask import Flask, request, jsonify
from loguru import logger

from nanobot import __logo__, __version__
from nanobot.config.loader import load_config, get_config_path, save_config
from nanobot.bus.queue import MessageBus
from nanobot.agent.loop import AgentLoop
from nanobot.agent.memory import MemoryManager
from nanobot.session.manager import SessionManager
from nanobot.cron.service import CronService
from nanobot.cron.types import CronSchedule, CronPayload, CronJob
from nanobot.channels.manager import ChannelManager
from nanobot.utils.helpers import get_workspace_path, get_data_path

# Global state
_app = None
_agent: AgentLoop | None = None
_session_manager: SessionManager | None = None
_memory_manager: MemoryManager | None = None
_cron_service: CronService | None = None
_channel_manager: ChannelManager | None = None
_bus: MessageBus | None = None
_async_loop: asyncio.AbstractEventLoop | None = None


def _run_background_tasks():
    """Run agent and channels in background thread with its own event loop."""
    global _async_loop
    _async_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(_async_loop)

    async def _background():
        # Start cron service
        await _cron_service.start()

        # Start agent message processing loop
        agent_task = asyncio.create_task(_agent.run())

        # Start all channels (dingtalk, telegram, etc.)
        channel_task = asyncio.create_task(_channel_manager.start_all())

        # Wait for both to complete (they should run forever)
        await asyncio.gather(agent_task, channel_task)

    try:
        _async_loop.run_until_complete(_background())
    except Exception as e:
        logger.error(f"Background task error: {e}")


def create_app() -> Flask:
    """Create and configure the Flask application."""
    global _agent, _session_manager, _memory_manager, _cron_service, _channel_manager, _bus

    app = Flask(__name__)
    app.config["JSON_SORT_KEYS"] = False

    # Initialize components
    config = load_config()
    workspace = get_workspace_path()
    data_dir = get_data_path()
    cron_store_path = data_dir / "cron" / "jobs.json"

    # Create shared message bus
    _bus = MessageBus()
    # Create session manager
    _session_manager = SessionManager(workspace)
    # Create memory manager
    _memory_manager = MemoryManager(workspace)
    # Create cron service
    _cron_service = CronService(cron_store_path)

    # Create provider ，创建了一个提供者 (Provider)
    provider = _make_provider(config)

    # Create agent loop
    _agent = AgentLoop(
        bus=_bus,
        provider=provider,
        workspace=workspace,
        model=config.agents.defaults.model,
        temperature=config.agents.defaults.temperature,
        max_tokens=config.agents.defaults.max_tokens,
        max_iterations=config.agents.defaults.max_tool_iterations,
        memory_window=config.agents.defaults.memory_window,
        exa_api_key=config.tools.web.search.api_key or None,
        exec_config=config.tools.exec,
        cron_service=_cron_service,
        restrict_to_workspace=config.tools.restrict_to_workspace,
        session_manager=_session_manager,
        mcp_servers=config.tools.mcp_servers,
    )

    # Set cron callback
    async def on_cron_job(job: CronJob) -> str | None:
        response = await _agent.process_direct(
            job.payload.message,
            session_key=f"cron:{job.id}",
            channel=job.payload.channel or "api",
            chat_id=job.payload.to or "direct",
        )
        if job.payload.deliver and job.payload.to:
            from nanobot.bus.events import OutboundMessage
            await _bus.publish_outbound(OutboundMessage(
                channel=job.payload.channel or "api",
                chat_id=job.payload.to,
                content=response or ""
            ))
        return response
    _cron_service.on_job = on_cron_job

    # Create channel manager (handles dingtalk, telegram, etc.)
    _channel_manager = ChannelManager(config, _bus)

    if _channel_manager.enabled_channels:
        logger.info(f"Channels enabled: {', '.join(_channel_manager.enabled_channels)}")
    else:
        logger.warning("No channels enabled")

    # Start background tasks in separate thread
    bg_thread = threading.Thread(target=_run_background_tasks, daemon=True)
    bg_thread.start()

    logger.info(f"{__logo__} nanobot server initialized")

    # ========== Routes ==========

    @app.route("/")
    def index():
        """Root endpoint."""
        return jsonify({
            "name": "nanobot",
            "version": __version__,
            "logo": __logo__,
            "endpoints": {
                "agent": {
                    "chat": "POST /api/agent/chat",
                },
                "sessions": {
                    "list": "GET /api/sessions",
                    "channels": "GET /api/sessions/channels",
                    "channel_users": "GET /api/sessions/channels/<channel>/users",
                    "get": "GET /api/sessions/<session_id>",
                    "delete": "DELETE /api/sessions/<session_id>",
                    "clear": "POST /api/sessions/<session_id>/clear",
                },
                "memory": {
                    "stats": "GET /api/memory/stats",
                    "global": "GET/PUT /api/memory/global",
                    "users": "GET /api/memory/users",
                    "user": "GET/PUT/DELETE /api/memory/users/<user_id>/<channel>",
                    "combined": "GET /api/memory/combined?user_id=xxx&channel=xxx",
                },
                "config": {
                    "get": "GET /api/config",
                    "update": "PUT /api/config",
                },
                "cron": {
                    "list": "GET /api/cron",
                    "add": "POST /api/cron",
                    "delete": "DELETE /api/cron/<job_id>",
                    "toggle": "POST /api/cron/<job_id>/toggle",
                },
                "channels": "GET /api/channels",
            }
        })

    # ========== Agent Routes ==========

    @app.route("/api/agent/chat", methods=["POST"])
    def agent_chat():
        """Send a message to the agent."""
        data = request.get_json()
        if not data or "message" not in data:
            return jsonify({"error": "Missing 'message' field"}), 400

        message = data["message"]
        session_id = data.get("session_id", "api:default")

        # Run async in background thread's event loop
        async def _run():
            return await _agent.process_direct(
                content=message,
                session_key=session_id,
                channel="api",
                chat_id="default",
            )

        if _async_loop is None:
            return jsonify({"error": "Server not initialized"}), 500

        future = asyncio.run_coroutine_threadsafe(_run(), _async_loop)
        response = future.result(timeout=120)  # 2 min timeout
        return jsonify({
            "response": response,
            "session_id": session_id,
        })

    # ========== Config Routes ==========

    @app.route("/api/config", methods=["GET"])
    def get_config():
        """Get current configuration."""
        config = load_config()
        return jsonify(config.model_dump(by_alias=True))

    @app.route("/api/config", methods=["PUT"])
    def update_config():
        """Update configuration."""
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        from nanobot.config.schema import Config
        try:
            config = Config.model_validate(data)
            save_config(config)
            return jsonify({"message": "Config updated successfully"})
        except Exception as e:
            return jsonify({"error": str(e)}), 400

    # ========== Cron Routes ==========

    @app.route("/api/cron", methods=["GET"])
    def list_cron_jobs():
        """List cron jobs with owner isolation support."""
        if _cron_service is None:
            return jsonify({"error": "Cron service not initialized"}), 500

        # Support owner filtering via query params
        owner_channel = request.args.get("channel")
        owner_user = request.args.get("user")
        include_disabled = request.args.get("all", "false").lower() == "true"

        jobs = _cron_service.list_jobs(
            include_disabled=include_disabled,
            owner_channel=owner_channel,
            owner_user=owner_user,
        )
        return jsonify({
            "jobs": [
                {
                    "id": job.id,
                    "name": job.name,
                    "enabled": job.enabled,
                    "schedule": {
                        "kind": job.schedule.kind,
                        "expr": job.schedule.expr,
                        "every_ms": job.schedule.every_ms,
                        "tz": job.schedule.tz,
                    },
                    "state": {
                        "next_run_at_ms": job.state.next_run_at_ms,
                        "last_run_at_ms": job.state.last_run_at_ms,
                    },
                    "owner": {
                        "channel": job.owner_channel,
                        "user": job.owner_user,
                    },
                    "payload": {
                        "deliver": job.payload.deliver,
                        "channel": job.payload.channel,
                        "to": job.payload.to,
                    },
                }
                for job in jobs
            ]
        })

    @app.route("/api/cron", methods=["POST"])
    def add_cron_job():
        """Add a new cron job with owner isolation."""
        if _cron_service is None:
            return jsonify({"error": "Cron service not initialized"}), 500

        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        required = ["name", "message"]
        for field in required:
            if field not in data:
                return jsonify({"error": f"Missing '{field}' field"}), 400

        # Build schedule
        schedule_kwargs = {}
        if "every" in data:
            schedule_kwargs["kind"] = "every"
            schedule_kwargs["every_ms"] = data["every"] * 1000
        elif "cron" in data:
            schedule_kwargs["kind"] = "cron"
            schedule_kwargs["expr"] = data["cron"]
            schedule_kwargs["tz"] = data.get("tz")
        else:
            return jsonify({"error": "Must specify 'every' or 'cron'"}), 400

        schedule = CronSchedule(**schedule_kwargs)

        # Owner isolation: use channel/user from request or defaults
        owner_channel = data.get("owner_channel", "api")
        owner_user = data.get("owner_user", "default")

        job = _cron_service.add_job(
            name=data["name"],
            schedule=schedule,
            message=data["message"],
            deliver=data.get("deliver", False),
            channel=data.get("channel"),
            to=data.get("to"),
            owner_channel=owner_channel,
            owner_user=owner_user,
        )

        return jsonify({
            "message": f"Job '{job.name}' created",
            "job_id": job.id,
            "owner": {
                "channel": job.owner_channel,
                "user": job.owner_user,
            },
        })

    @app.route("/api/cron/<job_id>", methods=["DELETE"])
    def delete_cron_job(job_id):
        """Delete a cron job with owner verification."""
        if _cron_service is None:
            return jsonify({"error": "Cron service not initialized"}), 500

        # Support owner verification via query params
        owner_channel = request.args.get("channel")
        owner_user = request.args.get("user")

        success = _cron_service.remove_job(
            job_id,
            owner_channel=owner_channel,
            owner_user=owner_user,
        )
        if success:
            return jsonify({"message": f"Job '{job_id}' removed"})
        else:
            return jsonify({"error": f"Job '{job_id}' not found or access denied"}), 404

    @app.route("/api/cron/<job_id>/toggle", methods=["POST"])
    def toggle_cron_job(job_id):
        """Toggle a cron job enabled/disabled with owner verification."""
        if _cron_service is None:
            return jsonify({"error": "Cron service not initialized"}), 500

        data = request.get_json() or {}
        enabled = data.get("enabled", True)

        # Support owner verification
        owner_channel = data.get("channel") or request.args.get("channel")
        owner_user = data.get("user") or request.args.get("user")

        job = _cron_service.enable_job(
            job_id,
            enabled=enabled,
            owner_channel=owner_channel,
            owner_user=owner_user,
        )
        if job:
            return jsonify({
                "message": f"Job '{job.name}' {'enabled' if enabled else 'disabled'}",
                "enabled": job.enabled,
            })
        else:
            return jsonify({"error": f"Job '{job_id}' not found or access denied"}), 404

    @app.route("/api/cron/<job_id>/run", methods=["POST"])
    def run_cron_job(job_id):
        """Manually trigger a cron job."""
        if _cron_service is None:
            return jsonify({"error": "Cron service not initialized"}), 500

        data = request.get_json() or {}
        force = data.get("force", False)

        # Support owner verification
        owner_channel = data.get("channel") or request.args.get("channel")
        owner_user = data.get("user") or request.args.get("user")

        if _async_loop is None:
            return jsonify({"error": "Server not initialized"}), 500

        async def _run():
            return await _cron_service.run_job(
                job_id,
                force=force,
                owner_channel=owner_channel,
                owner_user=owner_user,
            )

        future = asyncio.run_coroutine_threadsafe(_run(), _async_loop)
        success = future.result(timeout=60)

        if success:
            return jsonify({"message": f"Job '{job_id}' triggered"})
        else:
            return jsonify({"error": f"Job '{job_id}' not found, disabled, or access denied"}), 404

    # ========== Session Routes ==========

    @app.route("/api/sessions", methods=["GET"])
    def list_sessions():
        """List all sessions with optional channel filter."""
        if _session_manager is None:
            return jsonify({"error": "Session manager not initialized"}), 500

        channel = request.args.get("channel")
        limit = int(request.args.get("limit", 100))
        offset = int(request.args.get("offset", 0))

        sessions = _session_manager.list_sessions(channel=channel, limit=limit, offset=offset)
        stats = _session_manager.get_stats()

        return jsonify({
            "sessions": sessions,
            "stats": stats,
        })

    @app.route("/api/sessions/channels", methods=["GET"])
    def list_session_channels():
        """List all channels with sessions."""
        if _session_manager is None:
            return jsonify({"error": "Session manager not initialized"}), 500

        channels = _session_manager.list_channels()
        return jsonify({"channels": channels})

    @app.route("/api/sessions/channels/<channel>/users", methods=["GET"])
    def list_channel_users(channel):
        """List all users for a specific channel."""
        if _session_manager is None:
            return jsonify({"error": "Session manager not initialized"}), 500

        users = _session_manager.get_channel_users(channel)
        return jsonify({
            "channel": channel,
            "users": users,
        })

    @app.route("/api/sessions/<path:session_id>", methods=["GET"])
    def get_session(session_id):
        """Get session history."""
        if _session_manager is None:
            return jsonify({"error": "Session manager not initialized"}), 500

        # Replace underscores back to colons
        key = session_id.replace("_", ":", 1)
        session = _session_manager.get_or_create(key)

        return jsonify({
            "key": session.key,
            "channel": session.channel,
            "chat_id": session.chat_id,
            "messages": session.get_history(),
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
        })

    @app.route("/api/sessions/<path:session_id>", methods=["DELETE"])
    def delete_session(session_id):
        """Delete a session."""
        if _session_manager is None:
            return jsonify({"error": "Session manager not initialized"}), 500

        key = session_id.replace("_", ":", 1)
        success = _session_manager.delete(key)

        if success:
            return jsonify({"message": f"Session '{key}' deleted"})
        else:
            return jsonify({"error": f"Session '{key}' not found"}), 404

    @app.route("/api/sessions/<path:session_id>/clear", methods=["POST"])
    def clear_session(session_id):
        """Clear a session's messages."""
        if _session_manager is None:
            return jsonify({"error": "Session manager not initialized"}), 500

        key = session_id.replace("_", ":", 1)
        session = _session_manager.get_or_create(key)
        session.clear()
        _session_manager.save(session)

        return jsonify({"message": f"Session '{key}' cleared"})

    # ========== Memory Routes ==========

    @app.route("/api/memory/stats", methods=["GET"])
    def get_memory_stats():
        """Get memory statistics."""
        if _memory_manager is None:
            return jsonify({"error": "Memory manager not initialized"}), 500

        stats = _memory_manager.get_stats()
        return jsonify(stats)

    @app.route("/api/memory/global", methods=["GET"])
    def get_global_memory():
        """Get global memory."""
        if _memory_manager is None:
            return jsonify({"error": "Memory manager not initialized"}), 500

        return jsonify(_memory_manager.get_global_memory())

    @app.route("/api/memory/global", methods=["PUT"])
    def set_global_memory():
        """Set global memory."""
        if _memory_manager is None:
            return jsonify({"error": "Memory manager not initialized"}), 500

        data = request.get_json()
        if not data or "memory" not in data:
            return jsonify({"error": "Missing 'memory' field"}), 400

        _memory_manager.set_global_memory(data["memory"])
        return jsonify({"message": "Global memory updated"})

    @app.route("/api/memory/users", methods=["GET"])
    def list_memory_users():
        """List all users with memory."""
        if _memory_manager is None:
            return jsonify({"error": "Memory manager not initialized"}), 500

        users = _memory_manager.list_users()
        return jsonify({"users": users})

    @app.route("/api/memory/users/<user_id>/<channel>", methods=["GET"])
    def get_user_memory(user_id, channel):
        """Get user-level memory."""
        if _memory_manager is None:
            return jsonify({"error": "Memory manager not initialized"}), 500

        return jsonify(_memory_manager.get_user_memory(user_id, channel))

    @app.route("/api/memory/users/<user_id>/<channel>", methods=["PUT"])
    def set_user_memory(user_id, channel):
        """Set user-level memory."""
        if _memory_manager is None:
            return jsonify({"error": "Memory manager not initialized"}), 500

        data = request.get_json()
        if not data or "memory" not in data:
            return jsonify({"error": "Missing 'memory' field"}), 400

        _memory_manager.set_user_memory(user_id, channel, data["memory"])
        return jsonify({"message": f"User '{user_id}:{channel}' memory updated"})

    @app.route("/api/memory/users/<user_id>/<channel>", methods=["DELETE"])
    def delete_user_memory(user_id, channel):
        """Delete user-level memory."""
        if _memory_manager is None:
            return jsonify({"error": "Memory manager not initialized"}), 500

        success = _memory_manager.delete_user_memory(user_id, channel)
        if success:
            return jsonify({"message": f"User '{user_id}:{channel}' memory deleted"})
        else:
            return jsonify({"error": f"User '{user_id}:{channel}' memory not found"}), 404

    @app.route("/api/memory/combined", methods=["GET"])
    def get_combined_memory():
        """Get combined memory for a specific context."""
        if _memory_manager is None:
            return jsonify({"error": "Memory manager not initialized"}), 500

        user_id = request.args.get("user_id")
        channel = request.args.get("channel")

        combined = _memory_manager.get_combined_memory(user_id=user_id, channel=channel)
        return jsonify({
            "user_id": user_id,
            "channel": channel,
            "memory": combined,
        })

    # ========== Channel Routes ==========

    @app.route("/api/channels", methods=["GET"])
    def get_channels():
        """Get channel status."""
        config = load_config()

        channels = {
            "whatsapp": {
                "enabled": config.channels.whatsapp.enabled,
                "bridge_url": config.channels.whatsapp.bridge_url,
            },
            "telegram": {
                "enabled": config.channels.telegram.enabled,
                "configured": bool(config.channels.telegram.token),
            },
            "discord": {
                "enabled": config.channels.discord.enabled,
                "gateway_url": config.channels.discord.gateway_url,
            },
            "feishu": {
                "enabled": config.channels.feishu.enabled,
                "configured": bool(config.channels.feishu.app_id),
            },
            "slack": {
                "enabled": config.channels.slack.enabled,
                "configured": bool(config.channels.slack.app_token),
            },
            "dingtalk": {
                "enabled": config.channels.dingtalk.enabled,
                "configured": bool(config.channels.dingtalk.client_id),
            },
        }

        return jsonify({"channels": channels})

    return app


def _make_provider(config):
    """Create the appropriate LLM provider from config."""
    from nanobot.providers.litellm_provider import LiteLLMProvider
    from nanobot.providers.openai_codex_provider import OpenAICodexProvider
    from nanobot.providers.custom_provider import CustomProvider

    model = config.agents.defaults.model
    provider_name = config.get_provider_name(model)
    p = config.get_provider(model)

    # OpenAI Codex (OAuth)
    if provider_name == "openai_codex" or model.startswith("openai-codex/"):
        return OpenAICodexProvider(default_model=model)

    # Custom: direct OpenAI-compatible endpoint, bypasses LiteLLM
    if provider_name == "custom":
        return CustomProvider(
            api_key=p.api_key if p else "no-key",
            api_base=config.get_api_base(model) or "http://localhost:8000/v1",
            default_model=model,
        )

    from nanobot.providers.registry import find_by_name
    spec = find_by_name(provider_name)
    if not model.startswith("bedrock/") and not (p and p.api_key) and not (spec and spec.is_oauth):
        raise ValueError("No API key configured. Set one in config.json under providers section")

    return LiteLLMProvider(
        api_key=p.api_key if p else None,
        api_base=config.get_api_base(model),
        default_model=model,
        extra_headers=p.extra_headers if p else None,
        provider_name=provider_name,
    )


def run_server(host: str = "0.0.0.0", port: int = 5088, debug: bool = False):
    """Run the Flask server."""
    global _app
    _app = create_app()
    
    try:
        _app.run(host=host, port=port, debug=debug, threaded=True)
    finally:
        # Cleanup on shutdown
        if _async_loop and _channel_manager:
            future = asyncio.run_coroutine_threadsafe(
                _channel_manager.stop_all(), _async_loop
            )
            future.result(timeout=5)
        if _async_loop:
            _async_loop.stop()
        if _agent:
            # MCP cleanup needs async
            if _async_loop:
                future = asyncio.run_coroutine_threadsafe(
                    _agent.close_mcp(), _async_loop
                )
                future.result(timeout=5)
        logger.info("Server shutdown complete")


if __name__ == "__main__":
    run_server()
