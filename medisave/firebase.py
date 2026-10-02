"""Firebase Admin helpers shared by the Vercel functions and local server."""
import json
import os
from functools import lru_cache
from pathlib import Path


def _load_local_env():
    root = Path(__file__).resolve().parents[1]
    for filename in (".env.local", ".env"):
        path = root / filename
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            os.environ.setdefault(key.strip(), value)


_load_local_env()


PUBLIC_FIREBASE_KEYS = (
    "FIREBASE_API_KEY",
    "FIREBASE_AUTH_DOMAIN",
    "FIREBASE_PROJECT_ID",
    "FIREBASE_APP_ID",
)


def _service_account_json():
    return os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON") or os.environ.get("FIREBASE_CREDENTIALS_JSON")


def firebase_ready():
    return all(os.environ.get(key) for key in PUBLIC_FIREBASE_KEYS) and bool(_service_account_json())


def public_config():
    missing = [key for key in PUBLIC_FIREBASE_KEYS if not os.environ.get(key)]
    return {
        "enabled": not missing,
        "missing": missing,
        "community_enabled": not missing and bool(_service_account_json()),
        "config": {key.removeprefix("FIREBASE_").lower(): os.environ.get(key, "")
                   for key in PUBLIC_FIREBASE_KEYS},
    }


@lru_cache(maxsize=1)
def _admin_services():
    import firebase_admin
    from firebase_admin import credentials, firestore

    if firebase_admin._apps:
        app = firebase_admin.get_app()
    else:
        raw = _service_account_json()
        if not raw:
            raise RuntimeError("Firebase service account is not configured")
        account = json.loads(raw)
        app = firebase_admin.initialize_app(
            credentials.Certificate(account),
            {"projectId": os.environ.get("FIREBASE_PROJECT_ID") or account.get("project_id")},
        )
    return app, firestore.client(app=app)


def firestore_client():
    return _admin_services()[1]


def verify_id_token(token):
    import firebase_admin.auth

    app, _ = _admin_services()
    return firebase_admin.auth.verify_id_token(token, app=app)
