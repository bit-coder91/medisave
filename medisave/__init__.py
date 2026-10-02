"""MediSave catalogue search with a local CSV demo and optional Firestore storage."""
import csv
import math
import os
import re
import time
from collections import Counter
from difflib import SequenceMatcher

from .firebase import firebase_ready, firestore_client

DATA = os.path.join(os.path.dirname(__file__), "..", "data")
_cached_catalog = None
_cached_at = 0
_nlp_model_signature = None
_nlp_model = None
_SEARCH_INTENT_WORDS = frozenset({
    "a", "an", "and", "best", "buy", "can", "cheapest", "compare", "cost", "could",
    "do", "find", "for", "get", "give", "good", "have", "i", "is", "it", "like",
    "looking", "lowest", "me",
    "medicine", "medicines", "near", "nearby", "of", "online", "please", "price",
    "prices", "search", "show", "some", "the", "to", "want", "what", "whats",
    "where", "which", "need", "would", "you", "tablet", "tablets", "tab", "tabs", "capsule",
    "capsules", "syrup", "injection", "injections", "drops",
})
_STRENGTH_RE = re.compile(r"\b(\d+(?:\.\d+)?)\s*(mcg|ug|mg|g|ml|iu|units?)\b", re.I)


def _rows(name):
    path = os.path.join(DATA, name)
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _local_catalog():
    meds = _rows("medicines.csv")
    stores = [{**s, "kind": "nearby"} for s in _rows("pharmacies.csv")]
    stores += [{**s, "kind": "online"} for s in _rows("online_stores.csv")]
    offers = [{**o, "kind": "nearby"} for o in _rows("prices.csv")]
    offers += [{**o, "kind": "online"} for o in _rows("online_prices.csv")]
    return meds, stores, offers


def _firestore_catalog():
    global _cached_catalog, _cached_at
    if _cached_catalog is not None and time.monotonic() - _cached_at < 30:
        return _cached_catalog
    db = firestore_client()
    meds = [doc.to_dict() for doc in db.collection("medicines").stream()]
    stores = [doc.to_dict() for doc in db.collection("stores").stream()]
    offers = [doc.to_dict() for doc in db.collection("offers").stream()]
    _cached_catalog = (meds, stores, offers)
    _cached_at = time.monotonic()
    return _cached_catalog


def _catalog():
    return _firestore_catalog() if firebase_ready() else _local_catalog()


def _km(a, b, c, d):
    p = math.pi / 180
    x = math.sin((c - a) * p / 2) ** 2 + math.cos(a * p) * math.cos(c * p) * math.sin((d - b) * p / 2) ** 2
    return 12742 * math.asin(math.sqrt(x))


def _norm(value):
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()


def _query_parts(value):
    """Reduce a free-text shopping query to medicine terms and optional strength."""
    text = str(value or "").lower()
    strength = _STRENGTH_RE.search(text)
    requested_strength = None
    if strength:
        amount = str(float(strength.group(1))).rstrip("0").rstrip(".")
        unit = strength.group(2).lower()
        requested_strength = (amount, "mcg" if unit == "ug" else unit)
        text = text[:strength.start()] + " " + text[strength.end():]
    normalized = _norm(text)
    tokens = [token for token in normalized.split() if token not in _SEARCH_INTENT_WORDS]
    return " ".join(tokens), requested_strength


def _strength_key(value):
    match = _STRENGTH_RE.search(str(value or ""))
    if not match:
        return None
    amount = str(float(match.group(1))).rstrip("0").rstrip(".")
    unit = match.group(2).lower()
    return amount, "mcg" if unit == "ug" else unit


def _nlp_features(value):
    """Build word, phrase, and character n-gram features for TF-IDF retrieval."""
    tokens = _norm(value).split()
    features = Counter()
    for token in tokens:
        features[f"word:{token}"] += 2
        padded = f"^{token}$"
        if len(padded) >= 3:
            for index in range(len(padded) - 2):
                features[f"char:{padded[index:index + 3]}"] += 1
    for left, right in zip(tokens, tokens[1:]):
        features[f"phrase:{left}_{right}"] += 2
    return features


def _medicine_text(medicine):
    fields = ("brand", "generic_name", "salt", "generic_label", "strength", "form")
    return " ".join(str(medicine.get(field, "")) for field in fields)


def _build_nlp_model(medicines):
    """Fit a small catalog-specific TF-IDF model and reuse it until the catalog changes."""
    global _nlp_model_signature, _nlp_model
    signature = tuple(
        tuple(str(medicine.get(field, "")) for field in ("id", "brand", "generic_name", "salt", "generic_label", "strength", "form"))
        for medicine in medicines
    )
    if signature == _nlp_model_signature and _nlp_model is not None:
        return _nlp_model

    documents = [_nlp_features(_medicine_text(medicine)) for medicine in medicines]
    document_frequency = Counter(feature for document in documents for feature in document)
    count = max(1, len(documents))
    idf = {feature: math.log((count + 1) / (frequency + 1)) + 1 for feature, frequency in document_frequency.items()}
    vectors = []
    norms = []
    for document in documents:
        vector = {feature: weight * idf[feature] for feature, weight in document.items()}
        vectors.append(vector)
        norms.append(math.sqrt(sum(weight * weight for weight in vector.values())))

    _nlp_model_signature = signature
    _nlp_model = (idf, vectors, norms)
    return _nlp_model


def _tfidf_scores(query, medicines):
    idf, vectors, norms = _build_nlp_model(medicines)
    query_features = _nlp_features(query)
    query_vector = {feature: weight * idf[feature] for feature, weight in query_features.items() if feature in idf}
    query_norm = math.sqrt(sum(weight * weight for weight in query_vector.values()))
    if not query_norm:
        return [0.0] * len(medicines)
    scores = []
    for vector, norm in zip(vectors, norms):
        dot = sum(weight * vector.get(feature, 0.0) for feature, weight in query_vector.items())
        scores.append(dot / (query_norm * norm) if norm else 0.0)
    return scores


def _fuzzy_score(query, medicine):
    names = [medicine.get(k, "") for k in ("brand", "generic_name", "salt", "generic_label")]
    candidates = [_norm(name) for name in names if name]
    if any(query in candidate for candidate in candidates):
        return 1.0
    query_tokens = query.split()
    scores = []
    for candidate in candidates:
        tokens = candidate.split()
        whole = SequenceMatcher(None, query, candidate).ratio()
        token_scores = [
            max((SequenceMatcher(None, word, token).ratio() for token in tokens), default=0.0)
            for word in query_tokens
        ]
        token_score = sum(token_scores) / len(token_scores) if token_scores else 0.0
        scores.append(max(whole, token_score))
    return max(scores, default=0.0)


def _direct_match(query, medicine):
    names = [medicine.get(k, "") for k in ("brand", "generic_name", "salt", "generic_label")]
    candidates = [_norm(name) for name in names if name]
    return any(query == candidate or query in candidate.split() for candidate in candidates)


def search(q, lat=None, lng=None, source="both"):
    """Return catalog matches for free-text medicine and price queries."""
    raw_query = _norm(q)
    if len(raw_query) < 2:
        return []
    query, requested_strength = _query_parts(q)
    if len(query) < 2:
        return []
    if source not in ("nearby", "online", "both"):
        raise ValueError("source must be nearby, online, or both")

    meds, stores, offers = _catalog()
    store_by_id = {str(s.get("id")): s for s in stores}
    model_scores = _tfidf_scores(query, meds)
    ranked = []
    for index, medicine in enumerate(meds):
        fuzzy_score = _fuzzy_score(query, medicine)
        model_score = model_scores[index]
        if model_score >= 0.58:
            ranked.append((medicine, model_score, "tfidf_cosine"))
        else:
            ranked.append((medicine, fuzzy_score, "character_fuzzy"))
    if requested_strength:
        # An explicit strength is a hard filter so a similar brand with another
        # strength is never presented as a match for the user's stated query.
        ranked = [
            (medicine, score, method) for medicine, score, method in ranked
            if _strength_key(medicine.get("strength")) == requested_strength
        ]
    matches = [(medicine, score, True, "catalog_exact") for medicine, score, _ in ranked if _direct_match(query, medicine)]
    if not matches:
        matches = [(medicine, score, False, method) for medicine, score, method in ranked if score >= 0.58]
        matches.sort(key=lambda pair: pair[1], reverse=True)
        matches = matches[:4]

    out = []
    for medicine, score, exact, match_method in matches:
        medicine_id = str(medicine.get("id", ""))
        medicine_offers = []
        for raw in offers:
            if str(raw.get("med_id", "")) != medicine_id:
                continue
            store = store_by_id.get(str(raw.get("store_id", raw.get("pharmacy_id", ""))))
            if not store:
                continue
            kind = raw.get("kind") or store.get("kind") or "nearby"
            if source != "both" and kind != source:
                continue
            distance = None
            if kind == "nearby" and lat is not None:
                distance = round(_km(lat, lng, float(store["lat"]), float(store["lng"])), 1)
            medicine_offers.append({
                "pharmacy": store.get("name", "Pharmacy"),
                "area": store.get("area", ""),
                "km": distance,
                "source": kind,
                "url": store.get("url", ""),
                "brand_price": float(raw.get("brand_price") or 0) or None,
                "generic_price": float(raw.get("generic_price") or 0),
            })
        if not medicine_offers:
            continue

        medicine_offers.sort(key=lambda offer: (
            (0, offer["km"], offer["generic_price"]) if lat is not None and offer["source"] == "nearby"
            else (1, 0, offer["generic_price"]) if lat is not None
            else (0, 0, offer["generic_price"])
        ))
        brands = [offer["brand_price"] for offer in medicine_offers if offer["brand_price"]]
        generics = [offer["generic_price"] for offer in medicine_offers]
        best_brand, best_generic = (min(brands), min(generics)) if brands else (None, min(generics))
        spread = round((max(brands) - min(brands)) / max(brands) * 100, 1) if brands else 0
        out.append({
            "id": medicine_id,
            "brand": medicine.get("brand", ""),
            "generic_name": medicine.get("generic_name", ""),
            "salt": medicine.get("salt", ""),
            "strength": medicine.get("strength", ""),
            "pack_size": medicine.get("pack_size", ""),
            "generic_label": medicine.get("generic_label", medicine.get("generic_name", "")),
            "who_gmp": str(medicine.get("who_gmp", "false")).lower() in ("yes", "true", "1"),
            "bioequiv_note": medicine.get("bioequiv_note", ""),
            "brand_price_spread_pct": spread,
            "cheapest_brand": best_brand,
            "cheapest_generic": best_generic,
            "generic_savings_pct": round((1 - best_generic / best_brand) * 100, 1) if best_brand else None,
            "match_score": round(score * 100),
            "closest_match": not exact,
            "match_method": match_method,
            "offers": medicine_offers,
        })
    return out
