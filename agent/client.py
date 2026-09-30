import asyncio
import datetime
import inspect
import json
import logging
import os
import socket
import sys
import psutil
import websockets
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [Pulse-Agent]: %(message)s")
logger = logging.getLogger("pulse.agent")

# Configuration
SERVER_URL = os.getenv("PULSE_SERVER_URL", "ws://localhost:8000/ws").split("#")[0].strip()
API_KEY = os.getenv("PULSE_API_KEY", "sk_live_1234").split("#")[0].strip()
REPORT_INTERVAL = float(os.getenv("PULSE_INTERVAL", "0.2").split("#")[0].strip() or 0.2)
RECONNECT_DELAY = float(os.getenv("PULSE_RECONNECT_DELAY", "3.0").split("#")[0].strip() or 3.0)


def collect_metrics() -> dict:
    """Collects host CPU and RAM telemetry."""
    mem = psutil.virtual_memory()
    return {
        "hostname": socket.gethostname(),
        "cpu": round(psutil.cpu_percent(interval=None), 1),
        "ram": round(mem.percent, 1),
        "ram_used_gb": round(mem.used / (1024 ** 3), 2),
        "ram_total_gb": round(mem.total / (1024 ** 3), 2),
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }


async def run_agent():
    """Continuously streams hardware telemetry over WebSocket with auto-reconnect."""
    headers = {"x-api-key": API_KEY}
    logger.info(f"Starting Pulse Agent on '{socket.gethostname()}' -> {SERVER_URL} (Interval: {REPORT_INTERVAL}s)")

    # Establish psutil baseline
    psutil.cpu_percent(interval=None)

    # Determine header parameter for websockets compatibility
    kwarg_name = "additional_headers" if "additional_headers" in inspect.signature(websockets.connect).parameters else "extra_headers"
    connect_kwargs = {kwarg_name: headers}

    while True:
        try:
            async with websockets.connect(SERVER_URL, **connect_kwargs) as ws:
                logger.info("Connected to Pulse Hub. Streaming metrics...")
                while True:
                    await ws.send(json.dumps(collect_metrics()))
                    await asyncio.sleep(REPORT_INTERVAL)

        except (websockets.exceptions.ConnectionClosed, ConnectionRefusedError, OSError) as e:
            logger.warning(f"Connection lost ({e}). Retrying in {RECONNECT_DELAY}s...")
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error: {e}. Retrying in {RECONNECT_DELAY}s...")

        await asyncio.sleep(RECONNECT_DELAY)


if __name__ == "__main__":
    try:
        asyncio.run(run_agent())
    except KeyboardInterrupt:
        logger.info("Agent stopped by user.")
        sys.exit(0)
