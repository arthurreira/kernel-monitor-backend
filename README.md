# 🧠 Kernel Monitor Backend

> Real-time Linux kernel monitor using eBPF + local AI. Ask your kernel what it's doing.

An eBPF-powered filesystem watcher that intercepts every `openat` syscall on a Linux machine, stores events in SQLite, and exposes a FastAPI endpoint that lets you query kernel activity in plain English via a local Ollama model.

![Python](https://img.shields.io/badge/Python-3.12-blue?style=flat-square)
![FastAPI](https://img.shields.io/badge/FastAPI-latest-009688?style=flat-square)
![eBPF](https://img.shields.io/badge/eBPF-kernel%206.17-orange?style=flat-square)
![Ollama](https://img.shields.io/badge/Ollama-phi3:mini-purple?style=flat-square)

## What it does

- **eBPF hook** — attaches to `sys_enter_openat` tracepoint, captures every file open event (PID, process name, filename)
- **SQLite storage** — persists all events locally, queryable with SQL
- **Local AI** — phi3:mini via Ollama answers natural language questions about kernel activity
- **FastAPI** — exposes `/ask` endpoint for the chat UI

## Architecture

```
Linux Kernel (eBPF tracepoint)
    → file_watcher.py (BCC/Python)
        → SQLite (events.db)
            → api.py (FastAPI)
                → Ollama phi3:mini (local AI)
                    → chat UI answer
```

## Stack

- **eBPF** via BCC (Python bindings)
- **FastAPI** + uvicorn
- **SQLite** — local event storage
- **Ollama** — local LLM inference (phi3:mini)
- Tested on kernel **6.17**, Ubuntu 24

## Getting started

### Prerequisites

```bash
sudo apt install -y bpfcc-tools linux-headers-$(uname -r) python3-bpfcc bpftrace
pip install fastapi uvicorn httpx pydantic --break-system-packages
```

Install Ollama + model:
```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull phi3:mini
```

### Run

Terminal 1 — start eBPF watcher:
```bash
sudo python3 file_watcher.py
```

Terminal 2 — start API:
```bash
uvicorn api:app --host 0.0.0.0 --port 8000
```

### Query

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "what is the most active process?"}'
```

## Example questions

- *"What is the most active process?"*
- *"What is Docker doing?"*
- *"Is there anything suspicious?"*
- *"Which processes are monitoring memory?"*

## Related

- [kernel-monitor-ui](https://github.com/arthurreira/kernel-monitor-ui) — Next.js chat interface
