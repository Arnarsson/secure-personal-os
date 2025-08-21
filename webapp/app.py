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

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates

from personal_os import config as pos_config

# Import orchestrator from core
from core.secure_personal_os import SecurePersonalOS


# Configure logging early
pos_config.ensure_dirs()
log = logging.getLogger("PersonalOS_Web")
log.setLevel(logging.INFO)
if not any(isinstance(h, logging.StreamHandler) for h in log.handlers):
    sh = logging.StreamHandler()
    sh.setLevel(logging.INFO)
    log.addHandler(sh)


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

    # Single orchestrator instance per process
    app.state.secure_os = SecurePersonalOS()

    @app.get("/health")
    async def health() -> Dict[str, Any]:
        return {"status": "ok"}

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request):
        return templates.TemplateResponse(
            "index.html",
            {"request": request},
        )

    @app.get("/api/status")
    async def status():
        try:
            return app.state.secure_os.get_system_status()
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/session/init")
    async def session_init(payload: Dict[str, Any]):
        master_password = payload.get("master_password")
        if not master_password:
            raise HTTPException(status_code=400, detail="master_password required")
        ok, msg = await app.state.secure_os.initialize_session(master_password)
        return {"ok": ok, "message": msg}

    @app.post("/api/session/close")
    async def session_close():
        ok, msg = await app.state.secure_os.close_session()
        return {"ok": ok, "message": msg}

    @app.post("/api/auth")
    async def auth(payload: Dict[str, Any]):
        # payload example: {"gmail": {...}, "calendar": {...}, "whatsapp": {...}}
        results = await app.state.secure_os.authenticate_services(payload or {})
        return results

    @app.get("/api/briefing")
    async def briefing():
        return await app.state.secure_os.get_daily_briefing()

    @app.post("/api/action")
    async def action(payload: Dict[str, Any]):
        action = payload.get("action")
        if not action:
            raise HTTPException(status_code=400, detail="action required")
        kwargs = payload.get("params", {})
        ok, msg, data = await app.state.secure_os.execute_action(action, **kwargs)
        return {"ok": ok, "message": msg, "data": data}

    @app.get("/api/logs")
    async def logs(tail: int = 200):
        """Return the last N lines of the main log file."""
        log_file = Path(pos_config.logs_dir()) / "personal_os.log"
        if not log_file.exists():
            return PlainTextResponse("(no logs)")
        try:
            lines = log_file.read_text(encoding="utf-8", errors="ignore").splitlines()
            return PlainTextResponse("\n".join(lines[-tail:]))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("PERSONAL_OS_WEB_HOST", "127.0.0.1")
    port = int(os.getenv("PERSONAL_OS_WEB_PORT", "8000"))
    uvicorn.run("webapp.app:app", host=host, port=port, reload=False)

