import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional

import jwt
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.broker import RedisPubSubManager

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("pulse.hub")

# Configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379").split("#")[0].strip()
JWT_SECRET = os.getenv("JWT_SECRET", "pulse_enterprise_secret_key_2026").split("#")[0].strip()
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256").split("#")[0].strip()

# API Keys mapped to tenant_id
API_KEYS = {
    "sk_live_1234": "org_apple",
    "sk_live_apple": "org_apple",
    "sk_live_google": "org_google",
    "sk_live_microsoft": "org_microsoft",
}

broker = RedisPubSubManager(redis_url=REDIS_URL)

@asynccontextmanager
async def lifespan(app: FastAPI):
    await broker.connect()
    yield
    await broker.disconnect()

app = FastAPI(title="Pulse", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


async def authenticate_ws(websocket: WebSocket) -> Optional[Dict[str, str]]:
    """Authenticates agent via 'x-api-key' header or browser via 'token' query param."""
    api_key = websocket.headers.get("x-api-key")
    if api_key and api_key in API_KEYS:
        return {"tenant_id": API_KEYS[api_key], "client_type": "agent"}

    token = websocket.query_params.get("token")
    if token:
        if token == "mock_jwt_here":
            return {"tenant_id": "org_apple", "client_type": "browser"}
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            return {"tenant_id": payload.get("tenant_id", "org_apple"), "client_type": "browser"}
        except jwt.PyJWTError:
            return None

    return None


@app.websocket("/ws")
async def websocket_hub(websocket: WebSocket):
    """Multi-tenant WebSocket endpoint for edge agents and browser clients."""
    auth = await authenticate_ws(websocket)
    if not auth:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    tenant_id, client_type = auth["tenant_id"], auth["client_type"]
    await websocket.accept()

    try:
        if client_type == "agent":
            while True:
                data = await websocket.receive_json()
                data["tenant_id"] = tenant_id
                await broker.publish(tenant_id, data)

        elif client_type == "browser":
            async def forward_metrics():
                async for message in broker.subscribe(tenant_id):
                    await websocket.send_json(message)

            task = asyncio.create_task(forward_metrics())
            try:
                while True:
                    await websocket.receive_text()  # Keep connection open / detect disconnect
            finally:
                task.cancel()

    except WebSocketDisconnect:
        logger.info(f"{client_type.capitalize()} disconnected ({tenant_id})")
    except Exception as e:
        logger.error(f"WebSocket error for {tenant_id}: {e}")


@app.get("/api/token")
async def generate_token(tenant_id: str = "org_apple", user_id: str = "demo_user"):
    """Generates signed JWT for testing."""
    token = jwt.encode({"sub": user_id, "tenant_id": tenant_id}, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return JSONResponse({"token": token, "tenant_id": tenant_id})


@app.get("/health")
async def health_check():
    return {"status": "ok"}


# Serve static frontend dashboard
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

    @app.get("/")
    async def serve_dashboard():
        return FileResponse(os.path.join(frontend_dir, "index.html"))
