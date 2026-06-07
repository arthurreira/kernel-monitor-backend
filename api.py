from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
import httpx
from pydantic import BaseModel
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
