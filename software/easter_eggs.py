"""
Echo IRIS - Easter Eggs
Regex-based detection for special voice triggers.

Usage:
    from easter_eggs import check_easter_eggs
    result = check_easter_eggs(text)
    if result:
        # result is a dict with keys: type, sound, response, speaker
        # type: "grade", "21", "race"
        # sound: easter egg sound name for SoundManager, or None
        # response: text for Piper to speak, or None (21 has no speech)
        # speaker: Piper speaker ID override, or None for default
"""

import re

# Grade easter egg: matches "grade", "grades", "grading" but not "upgrade", "gradient"
GRADE_PATTERN = re.compile(
    r"(?<!\w)(?:what(?:'?s| is| would)?\s+(?:the |my |our |your )?)?grade[sd]?\b|(?<!\w)grading\b",
    re.IGNORECASE,
)

# 9+10 easter egg: matches "nine plus ten", "9 plus 10", "what's nine plus ten", etc.
NINE_TEN_PATTERN = re.compile(
    r"(?:nine|9)\s*(?:plus|posts|\+)\s*(?:ten|10)",
    re.IGNORECASE,
)

# Race easter egg: matches utterances containing "race" and "delivery" and "robot"
RACE_PATTERN_RACE = re.compile(r"\brace\b", re.IGNORECASE)
RACE_PATTERN_DELIVERY = re.compile(r"\bdeliver(?:y|ies)?\b", re.IGNORECASE)
RACE_PATTERN_ROBOT = re.compile(r"\brobot\b", re.IGNORECASE)

GRADE_RESPONSE = (
    "I am an advanced artificial intelligence running on a Raspberry Pi "
    "inside a toy Jeep. I do not receive grades. But if I did, I would "
    "obviously get an A plus."
)
GRADE_SPEAKER = 17

RACE_RESPONSE = "Vroom."
RACE_SPEAKER = None  # use default speaker


def check_easter_eggs(text):
    """Check recognized text for easter egg triggers.
    Returns a dict if triggered, None otherwise.

    Dict keys:
        type (str): "grade", "21", or "race"
        sound (str or None): SoundManager easter egg key ("21", "race", or None)
        response (str or None): text for Piper, or None for sound-only eggs
        speaker (int or None): Piper speaker ID override, or None for default
    """
    # Check 9+10 first (most specific)
    if NINE_TEN_PATTERN.search(text):
        return {
            "type": "21",
            "sound": "21",
            "response": None,
            "speaker": None,
        }

    # Check race (requires all three keywords)
    if (RACE_PATTERN_RACE.search(text)
            and RACE_PATTERN_DELIVERY.search(text)
            and RACE_PATTERN_ROBOT.search(text)):
        return {
            "type": "race",
            "sound": "race",
            "response": RACE_RESPONSE,
            "speaker": RACE_SPEAKER,
        }

    # Check grade last (broadest match)
    if GRADE_PATTERN.search(text):
        return {
            "type": "grade",
            "sound": None,
            "response": GRADE_RESPONSE,
            "speaker": GRADE_SPEAKER,
        }

    return None
