#!/usr/bin/env python3
"""
FastAPI Web App for Secure Personal OS

Exposes a simple web API and minimal UI to initialize a session,
authenticate services, perform actions (gmail/calendar/whatsapp/system),
and fetch status/briefing. Uses existing orchestrator and security layers.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Request, Depends, Response
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from personal_os import config as pos_config

# Import orchestrator from core
from core.secure_personal_os import SecurePersonalOS
import secrets
import subprocess
import atexit


# Configure logging early (skip FS writes in demo environments like Vercel)
if not pos_config.is_demo_mode():
    pos_config.ensure_dirs()
log = logging.getLogger("PersonalOS_Web")
log.setLevel(logging.INFO)
if not any(isinstance(h, logging.StreamHandler) for h in log.handlers):
    sh = logging.StreamHandler()
    sh.setLevel(logging.INFO)
    log.addHandler(sh)


security = HTTPBearer(auto_error=False)


def create_app() -> FastAPI:
    app = FastAPI(title="Secure Personal OS", version="1.0")

    # CORS for local development
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

    # Security token (simple bearer token auth)
    configured_token = os.getenv("PERSONAL_OS_WEB_TOKEN")
    if not configured_token:
        configured_token = secrets.token_hex(16)
        log.warning(
            "Generated development token for web API (PERSONAL_OS_WEB_TOKEN not set): %s",
            configured_token,
        )
    app.state.web_token = configured_token

    # Demo mode disables stateful or long-running features (enabled on Vercel)
    app.state.demo = pos_config.is_demo_mode()

    def _require_token(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
        """Simple bearer token check via Authorization header (Bearer)."""
        expected = app.state.web_token
        token_ok = False
        if credentials and credentials.scheme and credentials.scheme.lower() == "bearer":
            token_ok = (credentials.credentials == expected)
        if not token_ok:
            raise HTTPException(status_code=401, detail="unauthorized")
        return True

    def _maybe_require_token(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
        """Skip token requirement in demo mode for read-only endpoints."""
        if app.state.demo:
            return True
        return _require_token(credentials)

    # Single orchestrator instance per process
    app.state.secure_os = SecurePersonalOS()

    # Optional Playwright MCP background process
    app.state.playwright_proc = None

    def _playwright_running() -> bool:
        p = app.state.playwright_proc
        return p is not None and (p.poll() is None)

    def _start_playwright() -> Dict[str, Any]:
        if _playwright_running():
            return {"ok": True, "message": "Playwright MCP already running"}
        try:
            # Use npx to launch the server-playwright MCP server
            cmd = ["npx", "@modelcontextprotocol/server-playwright"]
            app.state.playwright_proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            return {"ok": True, "message": "Playwright MCP started", "pid": app.state.playwright_proc.pid}
        except FileNotFoundError:
            return {"ok": False, "message": "npx not found. Install Node.js 18+ and ensure npx is on PATH."}
        except Exception as e:
            return {"ok": False, "message": f"Failed to start Playwright MCP: {e}"}

    def _stop_playwright() -> Dict[str, Any]:
        if not _playwright_running():
            app.state.playwright_proc = None
            return {"ok": True, "message": "Playwright MCP not running"}
        try:
            app.state.playwright_proc.terminate()
            app.state.playwright_proc.wait(timeout=5)
            app.state.playwright_proc = None
            return {"ok": True, "message": "Playwright MCP stopped"}
        except Exception as e:
            return {"ok": False, "message": f"Failed to stop Playwright MCP: {e}"}

    # Startup/shutdown hooks
    @app.on_event("startup")
    async def _maybe_autostart_playwright():
        if app.state.demo:
            # Never autostart processes in demo
            return
        if os.getenv("PERSONAL_OS_AUTOSTART_PLAYWRIGHT", "").lower() in {"1", "true", "yes"}:
            res = _start_playwright()
            if not res.get("ok"):
                log.warning("Playwright MCP autostart failed: %s", res.get("message"))

    @app.on_event("shutdown")
    async def _cleanup():
        _stop_playwright()

    atexit.register(lambda: _stop_playwright())

    @app.get("/health")
    async def health() -> Dict[str, Any]:
        return {"status": "ok"}

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request):
        return templates.TemplateResponse(
            "index.html",
            {"request": request, "demo": app.state.demo},
        )

    @app.get("/api/info")
    async def info() -> Dict[str, Any]:
        return {
            "demo": app.state.demo,
            "tokenConfigured": bool(os.getenv("PERSONAL_OS_WEB_TOKEN")),
            "version": app.version if hasattr(app, "version") else "1.0",
        }

    @app.post("/api/login")
    async def login(payload: Dict[str, Any]):
        token = payload.get("token")
        if not token:
            raise HTTPException(status_code=400, detail="token required")
        if token != app.state.web_token:
            raise HTTPException(status_code=401, detail="invalid token")
        return {"ok": True}

    @app.get("/api/token")
    async def token_hint():
        # Development helper to reveal expected token when env not set
        env_set = bool(os.getenv("PERSONAL_OS_WEB_TOKEN"))
        return {"configured": env_set, "token": None if env_set else app.state.web_token}

    @app.get("/api/status")
    async def status(_: bool = Depends(_maybe_require_token)):
        try:
            return app.state.secure_os.get_system_status()
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/session/init")
    async def session_init(payload: Dict[str, Any], _: bool = Depends(_require_token)):
        if app.state.demo:
            raise HTTPException(status_code=503, detail="session/init disabled in demo mode")
        master_password = payload.get("master_password")
        if not master_password:
            raise HTTPException(status_code=400, detail="master_password required")
        ok, msg = await app.state.secure_os.initialize_session(master_password)
        return {"ok": ok, "message": msg}

    @app.post("/api/session/close")
    async def session_close(_: bool = Depends(_require_token)):
        if app.state.demo:
            raise HTTPException(status_code=503, detail="session/close disabled in demo mode")
        ok, msg = await app.state.secure_os.close_session()
        return {"ok": ok, "message": msg}

    @app.post("/api/auth")
    async def auth(payload: Dict[str, Any], _: bool = Depends(_require_token)):
        if app.state.demo:
            raise HTTPException(status_code=503, detail="auth disabled in demo mode")
        # payload example: {"gmail": {...}, "calendar": {...}, "whatsapp": {...}}
        results = await app.state.secure_os.authenticate_services(payload or {})
        return results

    @app.get("/api/briefing")
    async def briefing(_: bool = Depends(_maybe_require_token)):
        if app.state.demo:
            # Return a static, safe demo response
            return {
                "summary": "Demo daily briefing",
                "gmail_unread": 0,
                "calendar_today": [],
                "notes": [
                    "This is a read-only demo running on Vercel.",
                    "Authentication and browser automation are disabled.",
                ],
            }
        return await app.state.secure_os.get_daily_briefing()

    @app.post("/api/action")
    async def action(payload: Dict[str, Any], _: bool = Depends(_require_token)):
        if app.state.demo:
            raise HTTPException(status_code=503, detail="actions disabled in demo mode")
        action = payload.get("action")
        if not action:
            raise HTTPException(status_code=400, detail="action required")
        kwargs = payload.get("params", {})
        ok, msg, data = await app.state.secure_os.execute_action(action, **kwargs)
        return {"ok": ok, "message": msg, "data": data}

    @app.get("/api/logs")
    async def logs(tail: int = 200, _: bool = Depends(_maybe_require_token)):
        """Return the last N lines of the main log file."""
        if app.state.demo:
            return PlainTextResponse("(demo mode — logs disabled)")
        log_file = Path(pos_config.logs_dir()) / "personal_os.log"
        if not log_file.exists():
            return PlainTextResponse("(no logs)")
        try:
            lines = log_file.read_text(encoding="utf-8", errors="ignore").splitlines()
            return PlainTextResponse("\n".join(lines[-tail:]))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    # Playwright MCP control endpoints
    @app.get("/api/playwright/status")
    async def playwright_status(_: bool = Depends(_maybe_require_token)):
        if app.state.demo:
            return {"running": False, "pid": None, "demo": True}
        running = _playwright_running()
        pid = app.state.playwright_proc.pid if running else None
        return {"running": running, "pid": pid}

    @app.post("/api/playwright/start")
    async def playwright_start(_: bool = Depends(_require_token)):
        if app.state.demo:
            return {"ok": False, "message": "playwright disabled in demo mode"}
        return _start_playwright()

    @app.post("/api/playwright/stop")
    async def playwright_stop(_: bool = Depends(_require_token)):
        if app.state.demo:
            return {"ok": True, "message": "playwright not running (demo)"}
        return _stop_playwright()

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("PERSONAL_OS_WEB_HOST", "127.0.0.1")
    port = int(os.getenv("PERSONAL_OS_WEB_PORT", "8000"))
    uvicorn.run("webapp.app:app", host=host, port=port, reload=False)
