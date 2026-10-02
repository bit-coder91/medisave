"""Expose only public Firebase web config; server credentials stay server-side."""
import json
import os
from http.server import BaseHTTPRequestHandler

sys_path = os.path.join(os.path.dirname(__file__), "..")
if sys_path not in __import__("sys").path:
    __import__("sys").path.insert(0, sys_path)

from medisave.firebase import public_config


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        result = public_config()
        local_community = (
            os.environ.get("MEDISAVE_LOCAL_COMMUNITY") == "1"
            and result["enabled"]
            and not result["community_enabled"]
        )
        config = result["config"]
        config["projectId"] = config.pop("project_id", "")
        config["authDomain"] = config.pop("auth_domain", "")
        config["apiKey"] = config.pop("api_key", "")
        config["appId"] = config.pop("app_id", "")
        body = json.dumps({
            "enabled": result["enabled"],
            "communityEnabled": result["community_enabled"] or local_community,
            "localCommunity": local_community,
            "missing": result["missing"],
            "config": config,
        }).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)
