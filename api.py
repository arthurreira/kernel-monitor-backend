from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
import httpx
from pydantic import BaseModel
import subprocess
import psutil

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
class Question(BaseModel):
    question: str
def get_context(question: str) -> str:
    conn = sqlite3.connect('/home/naroshh/ebpf-lab/events.db')
    
    # Get process activity summary
    rows = conn.execute('''
        SELECT process, COUNT(*) as total, 
        MAX(timestamp) as last_seen
        FROM events 
        GROUP BY process 
        ORDER BY total DESC 
        LIMIT 20
    ''').fetchall()
    
    context = "Recent file system activity:\n"
    for row in rows:
        context += f"- {row[0]}: {row[1]} events, last seen {row[2]}\n"
    
    conn.close()
    return context
@app.post("/ask")
async def ask(q: Question):
    context = get_context(q.question)
    
    prompt = f"""You are a Linux system monitor AI.
Here is current file system activity data from eBPF kernel monitoring:
{context}
User question: {q.question}
Answer concisely based on the data above."""
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "phi3:mini",
                "prompt": prompt,
                "stream": False
            }
        )
    
    return {"answer": response.json()["response"]}

@app.get("/events")
async def get_events():
    conn = sqlite3.connect('/home/naroshh/ebpf-lab/events.db')
    rows = conn.execute('''
        SELECT timestamp, pid, process, filename 
        FROM events 
        ORDER BY id DESC 
        LIMIT 50
    ''').fetchall()
    conn.close()
    return {"events": [
        {"timestamp": r[0], "pid": r[1], "process": r[2], "filename": r[3]}
        for r in rows
    ]}

@app.get("/stats")
async def get_stats():
    conn = sqlite3.connect('/home/naroshh/ebpf-lab/events.db')
    total = conn.execute("SELECT COUNT() FROM events").fetchone()[0]
    top = conn.execute("SELECT process, COUNT() as c FROM events GROUP BY process ORDER BY c DESC LIMIT 1").fetchone()
    suspicious = conn.execute("SELECT COUNT(*) FROM events WHERE filename LIKE '%/etc/passwd%' OR filename LIKE '%/etc/shadow%'").fetchone()[0]

    conn.close()
    
    uptime = subprocess.check_output(['uptime','-p']).decode().strip()

    return {"total": total, "top_process": top[0], "suspicious": suspicious, "uptime": uptime}


@app.get("/health")
async def health():
    return {
        "cpu": psutil.cpu_percent(interval=0.1),
        "ram_used": round(psutil.virtual_memory().used / 1e9, 1),
        "ram_total": round(psutil.virtual_memory().total / 1e9, 1),
        "model": "phi3:mini",
        "backend": "172.20.10.2:8000"
    }