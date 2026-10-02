import json, math, os, sys
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from medisave import search
from medisave.firebase import firebase_ready, verify_id_token
from medisave.symptoms import symptom_guidance

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        qs = parse_qs(urlparse(self.path).query)
        try:
            query = qs.get("q", [""])[0].strip()
            if len(query) < 2:
                raise ValueError("q must be at least 2 characters")
            guide = symptom_guidance(query)
            if guide:
                return self._send({"intent": "symptom", "guide": guide, "results": []}, 200)
            if firebase_ready():
                auth = self.headers.get("Authorization", "")
                if not auth.startswith("Bearer "):
                    return self._send({"error": "Sign in to search the medicine catalog."}, 401)
                try:
                    verify_id_token(auth[7:].strip())
                except Exception:
                    return self._send({"error": "Your sign-in expired. Please sign in again."}, 401)
            source = qs.get("source", ["both"])[0].strip().lower()
            if source not in ("nearby", "online", "both"):
                raise ValueError("source must be nearby, online, or both")
            has_lat, has_lng = "lat" in qs, "lng" in qs
            if has_lat != has_lng:
                raise ValueError("lat and lng must be supplied together")
            lat = float(qs["lat"][0]) if has_lat else None
            lng = float(qs["lng"][0]) if has_lng else None
            if lat is not None and (not math.isfinite(lat) or not math.isfinite(lng) or not -90 <= lat <= 90 or not -180 <= lng <= 180):
                raise ValueError("lat/lng must be valid coordinates")
            body, code = {"intent": "medicine", "results": search(query, lat, lng, source)}, 200
        except ValueError as exc:
            body, code = {"error": str(exc)}, 400
        except Exception:
            body, code = {"error": "The medicine catalog is temporarily unavailable."}, 503
        self._send(body, code)

    def _send(self, body, code):
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)
