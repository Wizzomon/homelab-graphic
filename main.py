import sys
import os
import sqlite3
import uvicorn
import traceback
from typing import Optional, Dict, Any
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from datetime import datetime
app = FastAPI(title="Homelab Orchestrator")

if getattr(sys, 'frozen', False):
    base_path = sys._MEIPASs
else:
    base_path = os.path.dirname(__file__)

folder_path = os.path.join(base_path, "static")

app.mount("/static", StaticFiles(directory=folder_path), name="static")

DB_FILE = "homelab.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS nodes (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            ip_address TEXT NOT NULL,
            node_type TEXT DEFAULT 'agent',
            x REAL DEFAULT 200,
            y REAL DEFAULT 200,
            last_seen TEXT DEFAULT 'Active'
        )
    """)

    conn.commit()
    conn.close()
init_db()



class LoginRequest(BaseModel):
    username: str
    password: str

class AgentRegistration(BaseModel):
    node_id: str
    name: str
    ip_address: str
    x: Optional[float] = 200
    y: Optional[float] = 200

class PositionUpdate(BaseModel):
    id: str
    x: float
    y: float

active_agents: Dict[str, Dict[str, Any]] = {}

@app.post("/api/login")
def login(creds: LoginRequest):
    if creds.username == "admin" and creds.password == "admin":
        return {"success": True}
    return {"success": False, "detail": "Invalid username or password"}

@app.post("/api/deploy-mount")
def deploy_mount(data: dict):
    return {"message": "Mount triggered successfully!"}


import traceback

@app.post("/api/agents/register")
def register_agent(agent: AgentRegistration):
    try:
        conn = sqlite3.connect("homelab.db")
        cursor = conn.cursor()
        
        # Ensure the status column exists (safe migration check)
        try:
            cursor.execute("ALTER TABLE nodes ADD COLUMN status TEXT DEFAULT 'Online'")
            conn.commit()
        except sqlite3.OperationalError:
            pass # Column already exists
	
# --- ADD THIS NEW MIGRATION CHECK RIGHT HERE ---
        try:
            cursor.execute("ALTER TABLE nodes ADD COLUMN last_seen TEXT")
            conn.commit()
        except sqlite3.OperationalError:
            pass # Column already exists
        
        node_id = getattr(agent, "node_id", getattr(agent, "id", "unknown-node"))
        name = getattr(agent, "name", "Unnamed Agent")
        ip_address = getattr(agent, "ip_address", "127.0.0.1")
        
        cursor.execute("SELECT x, y FROM nodes WHERE id = ?", (node_id,))
        existing = cursor.fetchone()
        
        x = existing[0] if existing else 400
        y = existing[1] if existing else 300
        
        cursor.execute("""
            INSERT OR REPLACE INTO nodes (id, name, ip_address, node_type, x, y, status, last_seen)
            VALUES (?, ?, ?, 'agent', ?, ?, 'Online', ?)
        """, (node_id, name, ip_address, x, y, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        
        return {"success": True, "message": "Node {name} registered."}
    except Exception as e:
        print("--- REGISTRATION ERROR ---")
        traceback.print_exc()
        return {"success": False, "error": str(e)}


@app.get("/api/nodes")
def get_nodes():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM nodes")
    rows = cursor.fetchall()
    conn.close()

    nodes = {}
    now = datetime.now() # Define 'now' for our time check
    
    for row in rows:
        keys = row.keys()
        
        # 1. Safely grab status and last_seen from the database row first
        status = row["status"] if "status" in keys else "Online"
        last_seen_str = row["last_seen"] if "last_seen" in keys else None
        
        # 2. Check if the 10-second timeout has passed
        if last_seen_str and status == "Online":
            try:
                last_seen_time = datetime.fromisoformat(last_seen_str)
                if (now - last_seen_time).total_seconds() > 10:
                    status = "Offline"
            except Exception:
                pass

        # 3. Build the dictionary to send to your frontend canvas
        nodes[row["id"]] = {
            "name": row["name"],
            "ip_address": row["ip_address"],
            "node_type": row["node_type"],
            "x": row["x"],
            "y": row["y"],
            "last_seen": last_seen_str,
            "status": status
        }
    return nodes

@app.post("/api/nodes/manual")
def create_manual_node(agent: AgentRegistration):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO nodes (id, name, ip_address, node_type, x, y, last_seen)
        VALUES (?, ?, ?, 'manual', 350, 200, 'Manual')
        ON CONFLICT(id) DO UPDATE SET
            name = excluded.name,
            ip_address = excluded.ip_address
    """, (agent.node_id, agent.name, agent.ip_address))
    conn.commit()
    conn.close()
    return {"success": True}

@app.delete("/api/nodes/{node_id}")
def delete_node(node_id: str):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM nodes WHERE id = ?", (node_id,))
    conn.commit()
    conn.close()
    return {"success": True}

@app.post("/api/nodes/position")
def update_position(pos: PositionUpdate):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("UPDATE nodes SET x = ?, y = ? WHERE id = ?", (pos.x, pos.y, pos.id))
    conn.commit()
    conn.close()
    return {"success": True}

@app.get("/api/agents")
def get_agents():
    return active_agents

@app.post("/api/login")
def login(creds: LoginRequest):
    if creds.username == "wizzo" and creds.password == "SteamedHams":
        return {"success": True}
    return {"success": False, "detail": "Invalid username or password"}

@app.post("/api/deploy-mount")
def deploy_mount(data: dict):
    return {"message": "Mount triggered successfully!"}

# --- Path Resolution for PyInstaller ---
if getattr(sys, 'frozen', False):
    base_dir = sys._MEIPASS
else:
    base_dir = os.path.dirname(__file__)

frontend_dir = os.path.join(base_dir, "static")

if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

    # Serve Login Page at Root
    @app.get("/")
    def serve_login():
        return FileResponse(os.path.join(frontend_dir, "login.html"))

    # Serve Dashboard Page
    @app.get("/dashboard")
    def serve_dashboard():
        return FileResponse(os.path.join(frontend_dir, "dashboard.html"))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
