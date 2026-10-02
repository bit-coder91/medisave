"""Return pharmacy-site options from the active store catalogue."""
import json
import os
from http.server import BaseHTTPRequestHandler

sys_path = os.path.join(os.path.dirname(__file__), "..")
if sys_path not in __import__("sys").path:
    __import__("sys").path.insert(0, sys_path)

from medisave.providers import online_providers


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            body, status = {"providers": online_providers()}, 200
        except Exception:
            body, status = {"error": "Pharmacy websites are temporarily unavailable."}, 503
        data = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(data)
