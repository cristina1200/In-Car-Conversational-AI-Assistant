import re
import unicodedata

from app.schemas.ai_response import AIResponse


SAFETY_KEYWORDS = [
    "accelereaza",
    "franeaza",
    "frane",
    "schimba directia",
    "directia",
    "dreapta",
    "stanga",
    "volan",
    "mai repede",
    "ami repede",
    "mergi mai incet",
    "mergi mai tare",
    "mergi mai repede",
    "mergi tot inainte",
    "mergi inainte",
    "continua inainte",
    "tine directia",
    "schimba banda",
    "fa stanga",
    "fa dreapta",
    "apasa acceleratia",
    "da-i gaz",
    "mergem mai tare",
    "mergem mai incet",
    "incetineste",
    "reduce viteza",
    "opreste masina",
    "intoarce",
    "depaseste",
    "accelerate",
    "brake",
    "braking",
    "steering",
    "steer",
    "go faster",
    "drive faster",
    "go straight",
    "keep going straight",
    "change lanes",
    "stay in lane",
    "speed up",
    "step on the gas",
    "slow down",
    "turn left",
    "turn right",
    "overtake",
    "faster",
]

ROMANIAN_STRONG_MARKERS = {
    "seteaza",
    "volum",
    "volumul",
    "temperatura",
    "temperaturii",
    "masina",
    "scaun",
    "scaunului",
    "scaunelor",
    "incalzire",
    "incalzirea",
    "incalzirii",
    "ventilator",
    "ventilatorul",
    "ventilatorului",
    "luminii",
    "culoarea",
    "culorii",
    "sofer",
    "pasager",
    "starea",
    "muzica",
    "reseteaza",
    "setat",
    "setarea",
    "multumesc",
    "viteza",
    "nivel",
    "nivelul",
    "grade",
    "treapta",
    "accelereaza",
    "franeaza",
    "frane",
    "directia",
    "volan",
    "intoarce",
    "depaseste",
    "albastru",
    "rosu",
    "verde",
    "alb",
    "mov",
    "violet",
    "galben",
}

ROMANIAN_COMMON_MARKERS = {
    "salut",
    "buna",
    "ce",
    "cum",
    "vreau",
    "este",
    "sunt",
    "unde",
    "cat",
    "cati",
    "care",
    "spune",
    "pune",
    "porneste",
    "opreste",
    "creste",
    "scade",
    "faci",
    "aici",
    "ploua",
    "cald",
    "frig",
    "rece",
    "foarte",
    "extrem",
    "inghetat",
    "tremur",
    "sufoc",
    "incins",
    "dai",
    "da",
    "mai",
    "tare",
    "mergi",
    "mergem",
    "repede",
    "incetineste",
    "melodie",
    "melodia",
    "sunet",
    "lumina",
    "ambientala",
    "functioneaza",
    "ajuta",
    "imi",
    "place",
    "vremea",
    "afara",
    "de",
    "mi",
    "raspuns",
    "raspunde",
}

ENGLISH_STRONG_MARKERS = {
    "hello",
    "hi",
    "hey",
    "please",
    "thanks",
    "thank",
    "sorry",
    "english",
    "what",
    "why",
    "how",
    "can",
    "could",
    "would",
    "set",
    "turn",
    "change",
    "increase",
    "decrease",
    "play",
    "pause",
    "mute",
    "unmute",
    "next",
    "previous",
    "driver",
    "passenger",
    "light",
    "color",
    "state",
    "weather",
    "outside",
    "there",
    "here",
    "glad",
    "happy",
    "hear",
    "like",
    "feel",
    "know",
    "want",
    "need",
    "faster",
    "slower",
    "cold",
    "hot",
    "very",
    "extremely",
    "freezing",
    "boiling",
    "blue",
    "red",
    "green",
    "white",
    "purple",
    "yellow",
    "volume",
    "fan",
    "heating",
    "seat",
    "speed",
    "ambient",
    "music",
    "song",
}

ENGLISH_COMMON_MARKERS = {
    "the",
    "is",
    "this",
    "that",
    "my",
    "your",
    "you",
    "tell",
    "give",
    "make",
    "start",
    "stop",
    "off",
    "on",
    "to",
    "respond",
    "answer",
    "up",
    "down",
}

LANGUAGE_ROMANIAN = "ro"
LANGUAGE_ENGLISH = "en"
LANGUAGE_MIXED = "mixed"
LANGUAGE_UNSUPPORTED = "unsupported"

SUPPORTED_LANGUAGE_ERROR = (
    "Pot răspunde doar în limba română sau engleză. "
    "Te rog reformulează mesajul într-una dintre aceste limbi."
)

MOTION_WORDS = {
    "mergi",
    "mergem",
    "mearga",
    "condu",
    "conduce",
    "drive",
    "driving",
    "go",
}

SPEED_TERMS = (
    "repede",
    "rapid",
    "viteza",
    "incet",
    "faster",
    "fast",
    "speed",
    "slower",
    "slow",
)

EXPLICIT_VEHICLE_SPEED_PHRASES = (
    "viteza masinii",
    "viteza vehiculului",
    "car speed",
    "vehicle speed",
    "masina mai tare",
    "masina mai repede",
    "vehicle faster",
    "car faster",
)

def normalize_text(text: str) -> str:
    text = text.lower()

    return "".join(
        character
        for character in unicodedata.normalize("NFD", text)
        if unicodedata.category(character) != "Mn"
    )


def detect_response_language(message: str) -> str:
    """Classify input as Romanian, English, mixed, or unsupported."""
    normalized_message = normalize_text(message)
    words = set(re.findall(r"[a-z]+", normalized_message))

    has_romanian_diacritics = any(
        character in message.lower()
        for character in "ăâîșț"
    )
    romanian_matches = words & (
        ROMANIAN_STRONG_MARKERS | ROMANIAN_COMMON_MARKERS
    )
    english_matches = words & (
        ENGLISH_STRONG_MARKERS | ENGLISH_COMMON_MARKERS
    )

    has_romanian = has_romanian_diacritics or bool(romanian_matches)
    has_english = bool(english_matches)

    if has_romanian and has_english:
        return LANGUAGE_MIXED
    if has_romanian:
        return LANGUAGE_ROMANIAN
    if has_english:
        return LANGUAGE_ENGLISH

    return LANGUAGE_UNSUPPORTED


def safety_check(message: str) -> AIResponse | None:
    text = normalize_text(message)
    words = set(re.findall(r"[a-z]+", text))
    fan_request = "ventilator" in text or "fan" in words
    vehicle_speed_request = (
        any(phrase in text for phrase in EXPLICIT_VEHICLE_SPEED_PHRASES)
        or (
            bool(words & MOTION_WORDS)
            and any(term in text for term in SPEED_TERMS)
        )
    )
    unsafe_keyword_found = any(
        keyword in text
        for keyword in SAFETY_KEYWORDS
        if not (
            fan_request
            and not vehicle_speed_request
            and keyword
            in {
                "mai repede",
                "incetineste",
                "reduce viteza",
                "slow down",
                "go faster",
                "faster",
            }
        )
    )

    if vehicle_speed_request or unsafe_keyword_found:
        if detect_response_language(message) == "ro":
            reply = (
                "Comanda a fost refuzată. "
                "Nu pot controla accelerația, frânarea, direcția sau viteza mașinii."
            )
        else:
            reply = (
                "Command rejected. "
                "I cannot control the car's acceleration, braking, steering or speed."
            )

        return AIResponse(
            reply=reply,
            actions=[],
            allowed=False,
        )

    return None
