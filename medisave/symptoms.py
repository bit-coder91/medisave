"""Offline symptom phrase matching with cautious, source-linked self-care guidance.

This is a small intent matcher, not a diagnostic or treatment model. It never
selects a medicine or dosage from a symptom query.
"""
import re
from difflib import SequenceMatcher


GUIDES = [
    {
        "id": "cold_cough",
        "title": "Cold and cough",
        "aliases": (
            "cold", "common cold", "cough", "dry cough", "chesty cough",
            "cough and cold", "cold and cough", "sore throat", "runny nose",
            "blocked nose", "stuffy nose", "sneezing",
        ),
        "summary": "A search cannot tell whether these symptoms are a cold, flu, allergy, or another illness.",
        "self_care": [
            "Rest and drink fluids. A warm drink may soothe a cough; do not give honey to a child under 1 year.",
            "Ask a pharmacist before choosing a cough or cold product. Check active ingredients to avoid taking the same ingredient in more than one product.",
        ],
        "red_flags": [
            "Difficulty breathing, chest pain, coughing up blood, or feeling very unwell.",
            "Symptoms that worsen quickly, a high fever lasting more than 3 days, cold symptoms not improving after 10 days, or a cough lasting more than 3 weeks.",
        ],
        "sources": [
            {"label": "NHS: Common cold", "url": "https://www.nhs.uk/conditions/common-cold/"},
            {"label": "NHS: Cough", "url": "https://www.nhs.uk/symptoms/cough/"},
        ],
    },
    {
        "id": "headache",
        "title": "Headache",
        "aliases": ("headache", "head ache", "head pain", "pain in my head", "migraine"),
        "summary": "Headache can have many causes. This page cannot identify the cause or tell you which medicine to take.",
        "self_care": [
            "Drink water, rest, and try not to skip meals.",
            "If headaches keep returning, get worse, or do not improve, speak with a healthcare professional.",
        ],
        "red_flags": [
            "A sudden, extremely painful headache.",
            "Weakness or numbness, trouble speaking, walking or balancing, confusion, seizure, or loss of vision.",
            "A headache after a head injury, or with a very high fever and stiff neck, light sensitivity, or a rash that does not fade when pressed.",
        ],
        "sources": [
            {"label": "NHS: Headaches", "url": "https://www.nhs.uk/symptoms/headaches/"},
        ],
    },
    {
        "id": "neck_pain",
        "title": "Neck pain",
        "aliases": ("neck pain", "neck ache", "stiff neck", "sore neck", "pain in my neck"),
        "summary": "This is general information for a new neck problem, not an assessment of an injury or its cause.",
        "self_care": [
            "Try gentle movement and regular breaks from one position. A wrapped heat or cold pack may help.",
            "Do not drive or cycle if pain stops you moving your neck safely.",
        ],
        "red_flags": [
            "Severe pain that starts suddenly or gets worse quickly.",
            "New or worsening arm or leg weakness, numbness or pins and needles, or problems with balance or walking.",
            "Neck pain after a significant injury, or with a severe headache or fever.",
        ],
        "sources": [
            {"label": "NHS: Neck pain", "url": "https://www.nhs.uk/symptoms/neck-pain-and-stiff-neck/"},
            {"label": "NHS inform: Neck problems", "url": "https://www.nhsinform.scot/illnesses-and-conditions/muscle-bone-and-joints/neck-and-back-problems-and-conditions/neck-problems/"},
        ],
    },
    {
        "id": "sprain_strain",
        "title": "Sprain or strain",
        "aliases": (
            "sprain", "sprained ankle", "sprained wrist", "twisted ankle",
            "rolled ankle", "strain", "pulled muscle", "muscle strain",
        ),
        "summary": "A search cannot confirm whether an injury is a sprain, strain, or fracture.",
        "self_care": [
            "For a recent mild injury, protect and rest the area. A cold pack wrapped in cloth, comfortable support, and raising the area may help with swelling.",
            "Ask a pharmacist or clinician what care is suitable for you, especially before using a medicine.",
        ],
        "red_flags": [
            "Severe or worsening pain or swelling, difficulty moving the joint, or being unable to put weight on it.",
            "A changed shape, numbness or tingling, or skin that becomes blue, grey, or cold after the injury.",
        ],
        "sources": [
            {"label": "NHS: Sprains and strains", "url": "https://www.nhs.uk/conditions/sprains-and-strains/"},
        ],
    },
    {
        "id": "fever",
        "title": "Fever",
        "aliases": ("fever", "high temperature", "running a temperature", "chills", "shivering"),
        "summary": "Fever has many possible causes. Age, pregnancy, and existing health conditions can change how quickly someone needs care.",
        "self_care": [
            "Rest, drink fluids, and monitor how you feel. For a baby or child, contact a healthcare professional if you are unsure what to do.",
            "Ask a pharmacist or clinician before using a fever medicine, especially for a child or if you take other medicines.",
        ],
        "red_flags": [
            "Difficulty breathing, confusion or unusual drowsiness, a seizure, or a rash that does not fade when pressed.",
            "A stiff neck with fever or headache, or feeling very unwell or rapidly worse.",
        ],
        "sources": [
            {"label": "NHS: Fever in adults", "url": "https://www.nhs.uk/symptoms/fever-in-adults/"},
            {"label": "NHS: Fever in children", "url": "https://www.nhs.uk/symptoms/fever-in-children/"},
        ],
    },
]

EMERGENCY_PHRASES = (
    "difficulty breathing", "trouble breathing", "hard to breathe", "cannot breathe",
    "cant breathe", "shortness of breath", "chest pain", "coughing blood",
    "coughing up blood", "unconscious", "cannot wake", "cant wake", "seizure",
    "sudden severe headache", "worst headache", "face droop", "facial droop",
    "slurred speech", "one sided weakness", "one side weakness",
)
NEGATIONS = {"no", "not", "without", "never", "denies"}


def _norm(text):
    return re.sub(r"[^a-z0-9]+", " ", str(text or "").lower()).strip()


def _contains_phrase(text, phrase):
    return f" {phrase} " in f" {text} "


def _is_negated(text, phrase):
    before = text.split(phrase, 1)[0].split()
    return any(word in NEGATIONS for word in before[-3:])


def _emergency_match(text):
    for phrase in EMERGENCY_PHRASES:
        if _contains_phrase(text, phrase) and not _is_negated(text, phrase):
            return phrase

    # These combinations are more concerning together than as isolated words.
    combos = (
        (("stiff neck",), ("fever", "high temperature", "headache", "rash")),
        (("neck pain", "neck ache"), ("weakness", "numbness", "pins and needles", "balance problem", "difficulty walking")),
        (("sprain", "strain", "ankle", "wrist"), ("unable to bear weight", "cannot put weight", "cannot walk", "can t walk", "deformed", "numbness", "blue skin")),
    )
    for topics, signs in combos:
        has_topic = any(_contains_phrase(text, phrase) and not _is_negated(text, phrase) for phrase in topics)
        sign = next((phrase for phrase in signs if _contains_phrase(text, phrase) and not _is_negated(text, phrase)), "")
        if has_topic and sign:
            return sign
    return ""


def _topic_match(text, aliases):
    best = (0.0, "")
    for alias in aliases:
        if _contains_phrase(text, alias):
            return 1.0, alias
        alias_words = alias.split()
        text_words = text.split()
        if len(alias_words) > 1 and all(word in text_words for word in alias_words):
            return 0.96, alias
        # Handle small misspellings of longer symptom words without fuzzy-matching
        # short, ambiguous words such as "cold" or "neck".
        if len(alias_words) == 1 and len(alias) >= 6:
            score = max((SequenceMatcher(None, word, alias).ratio() for word in text_words), default=0.0)
            if score > best[0]:
                best = (score, alias)
    return best if best[0] >= 0.84 else (0.0, "")


def symptom_guidance(query):
    """Return a matched self-care guide or an emergency warning, if recognized."""
    text = _norm(query)
    if len(text) < 2:
        return None

    urgent_match = _emergency_match(text)
    ranked = [(_topic_match(text, item["aliases"])[0], item) for item in GUIDES]
    ranked.sort(key=lambda row: row[0], reverse=True)
    guide = ranked[0][1] if ranked and ranked[0][0] else None

    if guide:
        result = {key: value for key, value in guide.items() if key != "aliases"}
        result["urgent_match"] = urgent_match
        return result
    if urgent_match:
        return {
            "id": "urgent",
            "title": "Possible emergency warning sign",
            "summary": "A search cannot assess an emergency. Get urgent medical help now if this symptom is happening.",
            "self_care": [],
            "red_flags": ["Difficulty breathing, severe chest pain, loss of consciousness, seizure, sudden one-sided weakness, or another life-threatening emergency."],
            "sources": [],
            "urgent_match": urgent_match,
        }
    return None
