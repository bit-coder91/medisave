"""Public pharmacy-site options derived from the active catalogue store records."""
from urllib.parse import urlparse

from . import _catalog


def online_providers():
    _, stores, _ = _catalog()
    providers = []
    seen = set()
    for store in stores:
        if str(store.get("kind", "")).lower() != "online":
            continue
        url = str(store.get("url", "")).strip()
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            continue
        store_id = str(store.get("id", ""))
        key = store_id or parsed.hostname.lower()
        if key in seen:
            continue
        seen.add(key)
        providers.append({
            "id": store_id,
            "name": str(store.get("name", "Pharmacy website"))[:100],
            "area": str(store.get("area", ""))[:100],
            "url": url,
            "domain": parsed.hostname.lower().removeprefix("www."),
        })
    return sorted(providers, key=lambda provider: provider["name"].casefold())
