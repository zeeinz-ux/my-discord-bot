from enum import Enum


class IntentType(Enum):
    CHAT = "chat"
    SEARCH = "search"
    ACADEMIC = "academic"
    CODING = "coding"
    RESEARCH = "research"


ACADEMIC_KEYWORDS = [
    "jurnal",
    "skripsi",
    "referensi",
    "doi",
    "penelitian",
]

CODING_KEYWORDS = [
    "error",
    "bug",
    "debug",
    "python",
    "javascript",
]

SEARCH_KEYWORDS = [
    "carikan",
    "cari",
    "search",
    "temukan",
]

RESEARCH_KEYWORDS = [
    "bandingkan",
    "analisis",
    "review",
]


def detect_intent(message: str) -> IntentType:
    text = message.lower()

    if any(word in text for word in ACADEMIC_KEYWORDS):
        return IntentType.ACADEMIC

    if any(word in text for word in CODING_KEYWORDS):
        return IntentType.CODING

    if any(word in text for word in RESEARCH_KEYWORDS):
        return IntentType.RESEARCH

    if any(word in text for word in SEARCH_KEYWORDS):
        return IntentType.SEARCH

    return IntentType.CHAT