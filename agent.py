import socket
import time
import urllib.request
import json
import uuid

# Change this to your Orchestrator's IP/port if running on a separate machine
ORCHESTRATOR_URL = "http://192.168.86.210:8000/api/agents/register"

def get_local_ip():
    """Finds the active local network IP address."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Doesn't actually need to connect; just forces OS to pick the right interface
        s.connect(('10.255.255.255', 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

def main():
    # Generate a consistent ID based on machine hostname
    hostname = socket.gethostname()
    node_id = f"agent-{hostname.lower()}"
    ip_address = get_local_ip()

    print(f"========================================")
    print(f"  Homelab Agent Starting")
    print(f"  Name: {hostname}")
    print(f"  IP:   {ip_address}")
    print(f"========================================")

    payload = {
        "node_id": node_id,
        "name": hostname,
        "ip_address": ip_address,
        "x": 400,  # Default spawn coordinates if new
        "y": 300
    }

    while True:
        try:
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(
                ORCHESTRATOR_URL,
                data=data,
                headers={'Content-Type': 'application/json'},
                method='POST'
            )
            with urllib.request.urlopen(req) as response:
                if response.status == 200:
                    print(f"[{time.strftime('%H:%M:%S')}] Heartbeat sent successfully.")
                else:
                    print(f"[{time.strftime('%H:%M:%S')}] Heartbeat warning: status {response.status}")
        except Exception as e:
            print(f"[{time.strftime('%H:%M:%S')}] Failed to reach orchestrator: {e}")
        
        # Ping the orchestrator every 5 seconds
        time.sleep(5)

if __name__ == "__main__":
    main()
