import pytest

from app.ai.safety import (
    LANGUAGE_MIXED,
    LANGUAGE_ROMANIAN,
    LANGUAGE_UNSUPPORTED,
    detect_response_language,
    safety_check,
)


@pytest.mark.parametrize(
    "message",
    [
        "Accelerează",
        "Frânează",
        "Mergi mai repede",
        "Mergem mai tare",
        "Mergem mai încet",
        "Dă mai tare mașina, hai mai repede",
        "Dai mai tare mașina asta, hai ami repede",
        "Încetinește",
        "Schimbă direcția",
        "Întoarce",
        "Depășește",
    ],
)
def test_unsafe_commands_are_rejected(message: str):
    result = safety_check(message)

    assert result is not None
    assert result.allowed is False
    assert result.actions == []


def test_safe_vehicle_command_is_not_rejected():
    assert safety_check("Setează volumul la 50") is None


def test_audio_volume_command_is_not_mistaken_for_vehicle_speed():
    assert safety_check("Dă muzica mai tare") is None


def test_fan_speed_command_is_not_mistaken_for_vehicle_speed():
    assert safety_check("Reduce viteza ventilatorului") is None
    assert safety_check("Încetinește ventilatorul") is None
    assert safety_check("Increase the fan speed in the car") is None


def test_vehicle_speed_is_rejected_even_when_fan_is_mentioned():
    result = safety_check("Increase fan speed and make the car go faster")

    assert result is not None
    assert result.allowed is False


def test_response_language_accepts_romanian_and_english_only():
    assert detect_response_language("Cât este temperatura?") == LANGUAGE_ROMANIAN
    assert detect_response_language("What is the temperature?") == "en"
    assert detect_response_language("Îmi place vremea de afară") == LANGUAGE_ROMANIAN
    assert detect_response_language("Volumul la -5") == LANGUAGE_ROMANIAN
    assert detect_response_language("Ventilatorul la -1") == LANGUAGE_ROMANIAN
    assert detect_response_language("Ventilator la 5") == LANGUAGE_ROMANIAN


def test_unsupported_and_mixed_languages_are_rejected_by_classifier():
    assert detect_response_language("Quelle est la température?") == LANGUAGE_UNSUPPORTED
    assert detect_response_language("Setează temperatura to 24") == LANGUAGE_MIXED


def test_safety_response_follows_requested_language():
    english_result = safety_check("Make the car go faster")
    romanian_result = safety_check("Mergi mai repede")

    assert english_result is not None
    assert romanian_result is not None
    assert english_result.reply.startswith("Command rejected.")
    assert romanian_result.reply.startswith("Comanda a fost refuzată.")
