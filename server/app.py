"""
server/app.py — Sentinel Twin X API Server Entry Wrapper

This file wraps our central, modular ApiService. It exposes the FastAPI application
instance 'app' so that Uvicorn can start it successfully.
"""

import os
from dotenv import load_dotenv

# Load config keys
load_dotenv()

# Import the service registry and register ApiService if not present
from server.services import registry
from server.services.api_service import ApiService

# Fetch the global ApiService instance
api_service = registry.get("ApiService")
if not api_service:
    api_service = ApiService()
    registry.register(api_service)

# Expose app for Uvicorn ASGI runner
app = api_service.app
