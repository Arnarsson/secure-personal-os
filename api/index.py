#!/usr/bin/env python3
"""
Vercel serverless entry for Secure Personal OS web app.

Exposes the FastAPI `app` from webapp.app so Vercel's Python runtime
(@vercel/python) can serve it as an ASGI application.
"""

from webapp.app import app  # FastAPI instance

