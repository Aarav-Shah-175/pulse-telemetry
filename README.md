<div align="center">

# Pulse — Real-Time System Telemetry & Monitoring

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![WebSockets](https://img.shields.io/badge/WebSockets-010101?style=for-the-badge&logo=socketdotio&logoColor=white)](https://websockets.readthedocs.io/)
[![Redis](https://img.shields.io/badge/Redis-DC382D?style=for-the-badge&logo=redis&logoColor=white)](https://redis.io/)
[![Chart.js](https://img.shields.io/badge/Chart.js-FF6384?style=for-the-badge&logo=chartdotjs&logoColor=white)](https://www.chartjs.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg?style=for-the-badge)](LICENSE)

**A lightweight, multi-tenant real-time hardware telemetry pipeline built over a weekend.**

</div>

---

## 💡 Overview

**Pulse** is an enterprise-grade, multi-tenant system monitoring tool. Edge machine agents capture hardware metrics (CPU, RAM, load) at high frequency and stream them through a **FastAPI WebSocket hub**. 

Data is dynamically routed through a **Redis Pub/Sub broker** into tenant-isolated channels (`metrics:<tenant_id>`) and pushed live to browser dashboards with zero-lag Chart.js visualization.

> **Zero-Setup Dev Mode:** Pulse includes an automatic in-memory broadcast fallback, so you can run and test everything locally without needing Docker or a live Redis instance.

---

## 🏗️ Architecture

```
┌─────────────────────────────────┐
│        Edge Agent (Python)      │
│  - Captures psutil CPU & RAM    │
│  - Streams via WebSocket        │
│  - Auth: 'x-api-key' Header     │
└────────────────┬────────────────┘
                 │
                 ▼ ws://localhost:8000/ws
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI WebSocket Hub                    │
│  - Authenticates Edge Agents & Browser Clients (JWT)        │
│  - Directs streams to Redis Pub/Sub Manager                 │
└──────────────────────────────┬──────────────────────────────┘
                               │
            ┌──────────────────┴──────────────────┐
            ▼                                     ▼
   [Redis Available]                     [Redis Offline]
   Redis Channel: metrics:tenant_id      In-Memory asyncio.Queue
            │                                     │
            └──────────────────┬──────────────────┘
                               │
                               ▼ ws://localhost:8000/ws?token=...
┌─────────────────────────────────────────────────────────────┐
│             Real-Time Dashboard (HTML5 / Chart.js)          │
│  - Authenticated via JWT query token                        │
│  - 50-point smooth rolling time-series visualizer           │
│  - Distraction-free, dark-mode flat interface               │
└─────────────────────────────────────────────────────────────┘
```

---

## ✨ Key Features

- **Multi-Tenant Channel Routing:** Dynamically namespaces telemetry streams per organization (`metrics:org_apple`, `metrics:org_google`).
- **Dual Authentication Handshake:**
  - **Edge Agents:** Authenticated via `x-api-key` header.
  - **Browser Dashboards:** Authenticated via signed HMAC-SHA256 JWT tokens (`?token=...`).
  - **Policy Violation Rejection:** Automatically terminates unauthorized connections with WebSocket code `1008`.
- **Auto-Reconnecting Edge Daemon:** Edge client automatically reconnects with backoff if network drops or server restarts.
- **Ultra-Low Latency:** High-frequency (200ms / 5 Hz) sub-second telemetry streams.
- **Zero AI-Slop UI:** Clean, flat, distraction-free dashboard with solid contrast, no heavy gradients, and smooth rolling time-series buffers.

---

## 📁 Project Structure

```text
Pulse/
├── backend/
│   ├── broker.py      # Async Redis Pub/Sub manager + in-memory fallback
│   └── main.py        # FastAPI server, WebSocket hub, and static file host
├── agent/
│   └── client.py      # Edge hardware agent using psutil
├── frontend/
│   └── index.html     # Minimalistic real-time Chart.js dashboard
├── .env.example       # Template environment configuration
├── requirements.txt   # Python project dependencies
└── README.md          # Documentation
```

---

## 🚀 Quickstart Guide

### 1. Clone & Setup Environment

```bash
git clone https://github.com/<your-username>/pulse-telemetry.git
cd pulse-telemetry

# Create & activate virtual environment
python -m venv .venv
# On Windows:
.venv\Scripts\Activate.ps1
# On Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

Copy the template config to `.env`:

```bash
cp .env.example .env
```

### 3. Start the FastAPI Server

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```
The server will boot up and host both the WebSocket hub and the dashboard at `http://localhost:8000`.

### 4. Run the Edge Telemetry Agent

In a separate terminal tab:

```bash
python agent/client.py
```

### 5. Open the Dashboard

Open your browser to [http://localhost:8000](http://localhost:8000). The dashboard will connect, authenticate, and begin graphing real-time hardware telemetry immediately.

---

## ⚙️ Configuration (`.env`)

| Variable | Default | Description |
|---|---|---|
| `PORT` | `8000` | Server listening port |
| `HOST` | `0.0.0.0` | Server listening host |
| `REDIS_URL` | `redis://localhost:6379` | Redis broker connection URI |
| `JWT_SECRET` | `pulse_enterprise_secret_key_2026` | Secret key used to sign browser JWTs |
| `PULSE_SERVER_URL` | `ws://localhost:8000/ws` | Hub WebSocket endpoint URL |
| `PULSE_API_KEY` | `sk_live_1234` | Edge agent authentication key |
| `PULSE_INTERVAL` | `0.2` | Telemetry polling frequency (seconds) |
| `PULSE_RECONNECT_DELAY` | `3.0` | Agent backoff delay on disconnect |

---

## 🔐 Authentication Specs

1. **Edge Agent Connection:**
   - **Header:** `x-api-key: sk_live_1234`
   - **Assigned Tenant:** `org_apple`

2. **Browser Connection:**
   - **URL:** `ws://localhost:8000/ws?token=mock_jwt_here`
   - Alternatively, generate real signed JWTs via `/api/token?tenant_id=org_apple`.

---

## 📄 License

MIT License © 2026 Pulse Contributors. Built with ❤️ over a weekend.
