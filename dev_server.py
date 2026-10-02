"""Local dev server: static UI from public/ + /api/v1/compare (same handler Vercel runs). Usage: python dev_server.py [port]"""
import os, sys, threading, webbrowser
import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
ROOT = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, ROOT)
os.environ.setdefault("MEDISAVE_LOCAL_COMMUNITY", "1")
from api.compare import handler as Api
from api.config import handler as Config
from api.providers import handler as Providers
from api.requests import handler as Requests
from medisave.firebase import firebase_ready
from medisave.local_requests import add_request, list_requests

class H(SimpleHTTPRequestHandler):
    def __init__(self, *a, **k): super().__init__(*a, directory=os.path.join(ROOT, "public"), **k)
    def end_headers(self):
        # Local development should always reflect the latest HTML, CSS, and JS edits.
        self.send_header("Cache-Control", "no-store, max-age=0")
        super().end_headers()
    def _send(self, body, code):
        return Api._send(self, body, code)
    def _send_local_json(self, body, code=200):
        data = json.dumps(body).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(data)
    def _local_user_signed_in(self):
        return self.headers.get("Authorization", "").startswith("Bearer ")
    def do_GET(self):
        if self.path.startswith("/api/v1/compare"): return Api.do_GET(self)
        if self.path.startswith("/api/config"): return Config.do_GET(self)
        if self.path.startswith("/api/v1/providers"): return Providers.do_GET(self)
        if self.path.startswith("/api/v1/requests"):
            if firebase_ready(): return Requests.do_GET(self)
            if not self._local_user_signed_in():
                return self._send_local_json({"error": "Sign in to view community requests."}, 401)
            try:
                return self._send_local_json({"requests": list_requests()})
            except Exception:
                return self._send_local_json({"error": "Local community requests are unavailable."}, 503)
        super().do_GET()
    def do_POST(self):
        if self.path.startswith("/api/v1/requests"):
            if firebase_ready(): return Requests.do_POST(self)
            if not self._local_user_signed_in():
                return self._send_local_json({"error": "Sign in to post a medicine request."}, 401)
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length < 1 or length > 4096:
                    raise ValueError("Request body must be under 4 KB.")
                payload = json.loads(self.rfile.read(length))
                request = add_request(payload)
                return self._send_local_json({"request": request}, 201)
            except (ValueError, json.JSONDecodeError) as exc:
                return self._send_local_json({"error": str(exc)}, 400)
            except Exception:
                return self._send_local_json({"error": "We could not save the local medicine request."}, 503)
        self.send_error(501, "Unsupported method")

if __name__ == "__main__":
    p = int(sys.argv[1]) if len(sys.argv) > 1 else 8787
    url = f"http://127.0.0.1:{p}"
    print(f"MediSave on {url}")
    server = ThreadingHTTPServer(("127.0.0.1", p), H)
    threading.Timer(0.4, lambda: webbrowser.open(url)).start()
    server.serve_forever()
