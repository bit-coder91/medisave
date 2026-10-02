"""Import MediSave's CSV catalog into Firestore using the Firebase Admin SDK.

Set FIREBASE_SERVICE_ACCOUNT_JSON and FIREBASE_PROJECT_ID before running.
Existing documents with matching IDs are updated; unrelated documents are kept.
"""
import csv
import json
import os
import sys
from pathlib import Path

import firebase_admin
from firebase_admin import credentials, firestore

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from medisave.firebase import _load_local_env


def rows(filename):
    with (ROOT / "data" / filename).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def main():
    _load_local_env()
    raw = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON") or os.environ.get("FIREBASE_CREDENTIALS_JSON")
    if not raw:
        raise SystemExit("Set FIREBASE_SERVICE_ACCOUNT_JSON to the Firebase service account JSON.")
    account = json.loads(raw)
    project = os.environ.get("FIREBASE_PROJECT_ID") or account.get("project_id")
    if not project:
        raise SystemExit("Set FIREBASE_PROJECT_ID or include project_id in the service account JSON.")

    firebase_admin.initialize_app(credentials.Certificate(account), {"projectId": project})
    db = firestore.client()
    documents = []

    for medicine in rows("medicines.csv"):
        medicine["id"] = str(medicine["id"])
        medicine["who_gmp"] = medicine["who_gmp"].lower() == "yes"
        documents.append(("medicines", medicine["id"], medicine))

    stores = rows("pharmacies.csv") + rows("online_stores.csv")
    for store in stores:
        store["id"] = str(store["id"])
        store["kind"] = store.get("kind") or "nearby"
        for key in ("lat", "lng"):
            if store.get(key):
                store[key] = float(store[key])
        documents.append(("stores", store["id"], store))

    offers = rows("prices.csv") + rows("online_prices.csv")
    for offer in offers:
        offer["med_id"] = str(offer["med_id"])
        offer["store_id"] = str(offer.pop("store_id", offer.pop("pharmacy_id", "")))
        offer["kind"] = "online" if offer["store_id"].isdigit() and int(offer["store_id"]) >= 100 else "nearby"
        for key in ("brand_price", "generic_price"):
            offer[key] = float(offer[key])
        documents.append(("offers", f"{offer['med_id']}_{offer['store_id']}", offer))

    for start in range(0, len(documents), 450):
        batch = db.batch()
        for collection, doc_id, value in documents[start:start + 450]:
            batch.set(db.collection(collection).document(doc_id), value)
        batch.commit()
    print(f"Imported {len(documents)} catalog documents into project {project}.")


if __name__ == "__main__":
    main()
