"""Authenticated community medicine-request board backed by Firestore."""
import json
import os
from http.server import BaseHTTPRequestHandler

sys_path = os.path.join(os.path.dirname(__file__), "..")
if sys_path not in __import__("sys").path:
    __import__("sys").path.insert(0, sys_path)

from medisave.firebase import firebase_ready, firestore_client, verify_id_token


def _json(handler, body, code=200):
    data = json.dumps(body).encode("utf-8")
    handler.send_response(code)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("X-Content-Type-Options", "nosniff")
    handler.end_headers()
    handler.wfile.write(data)


def _user(handler):
    if not firebase_ready():
        return None
    header = handler.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return None
    try:
        return verify_id_token(header[7:].strip())
    except Exception:
        return None


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if not firebase_ready():
            return _json(self, {"error": "Community requests need Firebase Auth and Firestore configured."}, 503)
        if not _user(self):
            return _json(self, {"error": "Sign in to view community requests."}, 401)
        try:
            docs = firestore_client().collection("medicine_requests").where("status", "==", "open").limit(100).stream()
            items = [
                {"id": doc.id, **doc.to_dict()}
                for doc in docs
            ]
            items.sort(key=lambda item: int(item.get("created_at", 0)), reverse=True)
            safe = [{key: item.get(key, "") for key in ("id", "medicine", "strength", "city", "notes", "display_name", "created_at")} for item in items[:30]]
            return _json(self, {"requests": safe})
        except Exception:
            return _json(self, {"error": "Community requests are temporarily unavailable."}, 503)

    def do_POST(self):
        if not firebase_ready():
            return _json(self, {"error": "Posting requests needs Firebase Auth and Firestore configured."}, 503)
        user = _user(self)
        if not user:
            return _json(self, {"error": "Sign in to post a medicine request."}, 401)
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length < 1 or length > 4096:
                raise ValueError("Request body must be under 4 KB.")
            payload = json.loads(self.rfile.read(length))
            if not isinstance(payload, dict):
                raise ValueError("Request body must be a JSON object.")
            medicine = str(payload.get("medicine", "")).strip()[:100]
            strength = str(payload.get("strength", "")).strip()[:40]
            city = str(payload.get("city", "")).strip()[:80]
            notes = str(payload.get("notes", "")).strip()[:500]
            if len(medicine) < 2:
                raise ValueError("Enter the medicine or active ingredient you need.")
            if not city:
                raise ValueError("Enter your city.")
            doc = {
                "uid": user["uid"],
                "display_name": str(user.get("name") or "MediSave member")[:80],
                "medicine": medicine,
                "strength": strength,
                "city": city,
                "notes": notes,
                "status": "open",
                "created_at": __import__("time").time_ns() // 1_000_000,
            }
            ref, _ = firestore_client().collection("medicine_requests").add(doc)
            return _json(self, {"request": {"id": ref.id, **doc}}, 201)
        except (ValueError, json.JSONDecodeError) as exc:
            return _json(self, {"error": str(exc)}, 400)
        except Exception:
            return _json(self, {"error": "We could not post your request. Please try again."}, 503)

    def log_message(self, format, *args):
        pass
