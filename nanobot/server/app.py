"""Flask server for nanobot REST API."""

import asyncio
import json
from datetime import datetime
from pathlib import Path
import threading
from flask import Flask, request, jsonify, send_file, send_from_directory
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
from nanobot.plot_server import PlotServer

# Global state
_app = None
_agent: AgentLoop | None = None
_session_manager: SessionManager | None = None
_memory_manager: MemoryManager | None = None
_cron_service: CronService | None = None
_channel_manager: ChannelManager | None = None
_bus: MessageBus | None = None
_async_loop: asyncio.AbstractEventLoop | None = None
_plot_server: PlotServer | None = None


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
    global _agent, _session_manager, _memory_manager, _cron_service, _channel_manager, _bus, _plot_server

    app = Flask(__name__)
    app.config["JSON_SORT_KEYS"] = False
    app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size

    # CORS support
    @app.after_request
    def after_request(response):
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
        return response

    @app.route("/<path:path>", methods=["OPTIONS"])
    def options_handler(path):
        return "", 200

    @app.route("/", methods=["OPTIONS"])
    def root_options():
        return "", 200

    # Initialize plot server
    workspace = get_workspace_path()
    _plot_server = PlotServer(workspace)

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
        """Root endpoint - serve the frontend."""
        try:
            # Try to serve the frontend HTML file
            from pathlib import Path
            frontend_path = Path(__file__).parent.parent.parent / "frontend" / "index.html"
            if frontend_path.exists():
                return frontend_path.read_text(encoding="utf-8"), 200, {"Content-Type": "text/html; charset=utf-8"}
        except Exception as e:
            logger.warning(f"Could not serve frontend: {e}")

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

    # ========== File Upload Routes ==========

    @app.route("/api/upload", methods=["POST"])
    def upload_file():
        """Upload a file for analysis."""
        if 'file' not in request.files:
            return jsonify({"error": "No file part"}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "No selected file"}), 400

        session_id = request.form.get('session_id', 'default')
        safe_session_id = session_id.replace(":", "_")

        # Create upload directory
        upload_dir = workspace / "uploads" / safe_session_id
        upload_dir.mkdir(parents=True, exist_ok=True)

        # Save file
        file_path = upload_dir / file.filename
        file.save(str(file_path))

        # Get file info
        file_size = file_path.stat().st_size
        size_str = f"{file_size} bytes"
        if file_size > 1024:
            size_str = f"{file_size / 1024:.1f} KB"
        if file_size > 1024 * 1024:
            size_str = f"{file_size / (1024 * 1024):.1f} MB"

        return jsonify({
            "success": True,
            "filename": file.filename,
            "path": str(file_path),
            "size": size_str,
            "session_id": session_id,
        })

    @app.route("/api/files/<path:session_id>", methods=["GET"])
    def list_uploaded_files(session_id):
        """List all uploaded files for a session."""
        safe_session_id = session_id.replace("_", ":", 1).replace(":", "_")
        upload_dir = workspace / "uploads" / safe_session_id

        if not upload_dir.exists():
            return jsonify({"files": []})

        files = []
        for f in upload_dir.iterdir():
            if f.is_file():
                stat = f.stat()
                files.append({
                    "name": f.name,
                    "path": str(f),
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                })

        return jsonify({"files": files})

    @app.route("/api/files/<path:session_id>/<path:filename>", methods=["GET"])
    def get_file(session_id, filename):
        """Get a file by session and filename."""
        safe_session_id = session_id.replace("_", ":", 1).replace(":", "_")
        file_path = workspace / "uploads" / safe_session_id / filename

        if not file_path.exists():
            return jsonify({"error": "File not found"}), 404

        from flask import send_file
        return send_file(str(file_path), as_attachment=False)

    @app.route("/api/notebooks/<path:session_id>", methods=["GET"])
    def get_notebook(session_id):
        """Get the Jupyter notebook for a session."""
        global _plot_server

        if _plot_server is None:
            return jsonify({"error": "Plot server not initialized"}), 500

        safe_session_id = session_id.replace(":", "_")
        notebook_path = _plot_server.notebooks_dir / safe_session_id / "analysis.ipynb"

        if not notebook_path.exists():
            return jsonify({"error": "Notebook not found"}), 404

        with open(notebook_path, 'r', encoding='utf-8') as f:
            notebook = json.load(f)

        return jsonify(notebook)

    # ========== Plot Server Routes ==========

    @app.route("/plots/<path:session_id>/<path:plot_name>", methods=["GET"])
    def serve_plot(session_id, plot_name):
        """Serve a plot image file."""
        global _plot_server

        if _plot_server is None:
            return jsonify({"error": "Plot server not initialized"}), 500

        plot_path = _plot_server.get_plot_path(session_id, plot_name)

        if plot_path is None:
            logger.warning(f"Plot not found: {session_id}/{plot_name}")
            return jsonify({"error": "Plot not found"}), 404

        response = send_file(
            str(plot_path),
            mimetype='image/png',
            as_attachment=False,
            etag=True,
            last_modified=datetime.fromtimestamp(plot_path.stat().st_mtime)
        )
        # Add CORS and caching headers
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Cache-Control', 'public, max-age=3600')
        return response

    @app.route("/api/plots/<path:session_id>", methods=["GET"])
    def list_plots(session_id):
        """List all plots for a session."""
        global _plot_server

        if _plot_server is None:
            return jsonify({"error": "Plot server not initialized"}), 500

        plots = _plot_server.list_session_plots(session_id)
        return jsonify({
            "session_id": session_id,
            "plots": plots,
            "count": len(plots)
        })

    @app.route("/api/python/exec", methods=["POST"])
    def execute_python_code():
        """Execute Python code and return results with plots."""
        global _plot_server, _async_loop

        if _plot_server is None:
            return jsonify({"error": "Plot server not initialized"}), 500

        data = request.get_json()
        if not data or "code" not in data:
            return jsonify({"error": "Missing 'code' field"}), 400

        code = data["code"]
        session_id = data.get("session_id", "default")

        async def _run():
            return await _plot_server.execute_python(code, session_id)

        if _async_loop is None:
            return jsonify({"error": "Server not initialized"}), 500

        try:
            future = asyncio.run_coroutine_threadsafe(_run(), _async_loop)
            result = future.result(timeout=120)

            return jsonify(result)
        except Exception as e:
            logger.error(f"Python execution failed: {e}")
            return jsonify({
                "success": False,
                "output": f"Execution failed: {str(e)}",
                "plots": [],
                "error": str(e)
            }), 500

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
    from nanobot.providers.requests_llm import RequestsLLMProvider
    from nanobot.providers.pingan_provider import PinganProvider

    model = config.agents.defaults.model
    provider_name = config.get_provider_name(model)
    p = config.get_provider(model)

    # OpenAI Codex (OAuth)
    if provider_name == "openai_codex" or model.startswith("openai-codex/"):
        return OpenAICodexProvider(default_model=model)

    # Requests: direct HTTP calls (like 本地服务.py)
    if provider_name == "requests":
        return RequestsLLMProvider(
            api_key=p.api_key if p else "",
            api_base=config.get_api_base(model) or "https://api.moonshot.cn/v1",
            default_model=model or "moonshot-v1-8k",
        )

    # Pingan: local service provider
    if provider_name == "pingan":
        return PinganProvider(
            api_key=p.api_key if p else "no-key",
            api_base=config.get_api_base(model) or "http://localhost:8000/v1",
            default_model=model,
        )

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
        raise ValueError("No API key configured. Set one in config_backup.json under providers section")

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
