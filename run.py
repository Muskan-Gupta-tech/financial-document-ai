import os
import sys
import socket
import uvicorn

# Ensure the project root directory is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex((host, port)) == 0


def get_available_port(start_port: int = 8000, host: str = "127.0.0.1") -> int:
    port = start_port
    while is_port_in_use(port, host):
        print(f"Notice: Port {port} is currently in use, trying {port + 1}...")
        port += 1
    return port


if __name__ == "__main__":
    port = get_available_port(8000)
    print("=" * 65)
    print("Starting FinEdge AI - Financial Document Intelligence Studio")
    print(f"Project Directory: {PROJECT_ROOT}")
    print(f"Access Web Dashboard at : http://127.0.0.1:{port}")
    print(f"Access Swagger Docs at   : http://127.0.0.1:{port}/docs")
    print(f"Access Health Check at   : http://127.0.0.1:{port}/api/v1/health")
    print("=" * 65)
    uvicorn.run("backend.app.main:app", host="127.0.0.1", port=port, reload=False)
