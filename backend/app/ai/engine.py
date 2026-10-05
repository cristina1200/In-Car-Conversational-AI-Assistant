import json
import logging
import os
import re

from dotenv import load_dotenv
from openai import OpenAI

from app.ai.prompts import SYSTEM_PROMPT
from app.ai.safety import (
    LANGUAGE_MIXED,
    LANGUAGE_UNSUPPORTED,
    SUPPORTED_LANGUAGE_ERROR,
    detect_response_language,
    normalize_text,
    safety_check,
)
from app.ai.tools import TOOLS
from app.schemas.ai_response import AIResponse, VehicleAction
from app.vehicle.constants import (
    ACTION_MEDIA_MUTE,
    ACTION_MEDIA_NEXT,
    ACTION_MEDIA_PREVIOUS,
    ACTION_MEDIA_PAUSE,
    ACTION_MEDIA_PLAY,
    ACTION_MEDIA_UNMUTE,
    ACTION_RESET_VEHICLE,
    ACTION_SET_AMBIENT_LIGHT,
    ACTION_SET_FAN_SPEED,
    ACTION_SET_SEAT_HEATING,
    ACTION_SET_TEMPERATURE,
    ACTION_SET_VOLUME,
    AMBIENT_COLOR_ALIASES,
    AMBIENT_COLOR_LABELS_RO,
    AMBIENT_LIGHTS,
    DEFAULT_AC_ENABLED,
    DEFAULT_AMBIENT_LIGHT,
    DEFAULT_CURRENT_SONG,
    DEFAULT_DRIVER_TEMPERATURE,
    DEFAULT_FAN_SPEED,
    DEFAULT_IS_MUTED,
    DEFAULT_IS_PLAYING,
    DEFAULT_PASSENGER_TEMPERATURE,
    DEFAULT_VOLUME,
    MAX_FAN_SPEED,
    MAX_SEAT_HEATING,
    MAX_TEMPERATURE,
    MAX_VOLUME,
    MAX_CONVERSATION_MESSAGES,
    MIN_FAN_SPEED,
    MIN_SEAT_HEATING,
    MIN_TEMPERATURE,
    MIN_VOLUME,
    TEMPERATURE_COMFORT_STEP,
    TEMPERATURE_INTENSE_COMFORT_STEP,
    VEHICLE_ZONES,
)


load_dotenv()

logger = logging.getLogger(__name__)


def get_client() -> OpenAI | None:
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        return None

    return OpenAI(api_key=api_key)


def append_localized(
    replies: list[str],
    language: str,
    romanian: str,
    english: str,
) -> None:
    replies.append(romanian if language == "ro" else english)


def append_limit_notice(
    replies: list[str],
    language: str,
    romanian: str,
    english: str,
) -> None:
    notice = romanian if language == "ro" else english

    if not any(reply.rstrip() == notice for reply in replies):
        replies.append(f"{notice}\n")


def create_temperature_response(
    replies: list[str],
    actions: list[VehicleAction],
    current_value: int,
    requested_value: int,
    zone: str,
    language: str = "ro",
) -> int:
    new_value = max(
        MIN_TEMPERATURE,
        min(MAX_TEMPERATURE, requested_value),
    )
    zone_name_ro = "șoferului" if zone == "driver" else "pasagerului"
    zone_name_en = "the driver" if zone == "driver" else "the passenger"

    actions.append(
        VehicleAction(
            type=ACTION_SET_TEMPERATURE,
            params={"zone": zone, "value": new_value},
        )
    )

    if (
        new_value == current_value
        and MIN_TEMPERATURE <= requested_value <= MAX_TEMPERATURE
    ):
        if current_value == MAX_TEMPERATURE:
            append_localized(
                replies,
                language,
                f"Temperatura {zone_name_ro} este deja la limita maximă de "
                f"{MAX_TEMPERATURE}°C.",
                f"The temperature for {zone_name_en} is already at the "
                f"maximum limit of {MAX_TEMPERATURE}°C.",
            )
        elif current_value == MIN_TEMPERATURE:
            append_localized(
                replies,
                language,
                f"Temperatura {zone_name_ro} este deja la limita minimă de "
                f"{MIN_TEMPERATURE}°C.",
                f"The temperature for {zone_name_en} is already at the "
                f"minimum limit of {MIN_TEMPERATURE}°C.",
            )
        else:
            append_localized(
                replies,
                language,
                f"Temperatura {zone_name_ro} este deja setată la "
                f"{current_value}°C.",
                f"The temperature for {zone_name_en} is already set to "
                f"{current_value}°C.",
            )

        return current_value

    if requested_value > MAX_TEMPERATURE:
        append_limit_notice(
            replies,
            language,
            f"Temperatura maximă este {MAX_TEMPERATURE}°C.",
            f"The maximum temperature is {MAX_TEMPERATURE}°C.",
        )
        append_localized(
            replies,
            language,
            f"Am setat temperatura {zone_name_ro} de la {current_value}°C "
            f"la {MAX_TEMPERATURE}°C.",
            f"I set the temperature for {zone_name_en} from "
            f"{current_value}°C to {MAX_TEMPERATURE}°C.",
        )
    elif requested_value < MIN_TEMPERATURE:
        append_limit_notice(
            replies,
            language,
            f"Temperatura minimă este {MIN_TEMPERATURE}°C.",
            f"The minimum temperature is {MIN_TEMPERATURE}°C.",
        )
        append_localized(
            replies,
            language,
            f"Am setat temperatura {zone_name_ro} de la {current_value}°C "
            f"la {MIN_TEMPERATURE}°C.",
            f"I set the temperature for {zone_name_en} from "
            f"{current_value}°C to {MIN_TEMPERATURE}°C.",
        )
    else:
        append_localized(
            replies,
            language,
            f"Am setat temperatura {zone_name_ro} de la {current_value}°C "
            f"la {new_value}°C.",
            f"I set the temperature for {zone_name_en} from "
            f"{current_value}°C to {new_value}°C.",
        )

    return new_value


def create_volume_response(
    replies: list[str],
    actions: list[VehicleAction],
    current_value: int,
    requested_value: int,
    language: str = "ro",
) -> int:
    new_value = max(MIN_VOLUME, min(MAX_VOLUME, requested_value))

    actions.append(
        VehicleAction(
            type=ACTION_SET_VOLUME,
            params={"value": new_value},
        )
    )

    if (
        new_value == current_value
        and MIN_VOLUME <= requested_value <= MAX_VOLUME
    ):
        if current_value == MAX_VOLUME:
            append_localized(
                replies,
                language,
                f"Volumul este deja la limita maximă de {MAX_VOLUME}%.",
                f"The volume is already at the maximum limit of {MAX_VOLUME}%.",
            )
        elif current_value == MIN_VOLUME:
            append_localized(
                replies,
                language,
                f"Volumul este deja la limita minimă de {MIN_VOLUME}%.",
                f"The volume is already at the minimum limit of {MIN_VOLUME}%.",
            )
        else:
            append_localized(
                replies,
                language,
                f"Volumul este deja setat la {current_value}%.",
                f"The volume is already set to {current_value}%.",
            )

        return current_value

    if requested_value > MAX_VOLUME:
        append_limit_notice(
            replies,
            language,
            f"Volumul maxim este {MAX_VOLUME}%.",
            f"The maximum volume is {MAX_VOLUME}%.",
        )
        append_localized(
            replies,
            language,
            f"Am setat volumul de la {current_value}% la {MAX_VOLUME}%.",
            f"I set the volume from {current_value}% to {MAX_VOLUME}%.",
        )
    elif requested_value < MIN_VOLUME:
        append_limit_notice(
            replies,
            language,
            f"Volumul minim este {MIN_VOLUME}%.",
            f"The minimum volume is {MIN_VOLUME}%.",
        )
        append_localized(
            replies,
            language,
            f"Am setat volumul de la {current_value}% la {MIN_VOLUME}%.",
            f"I set the volume from {current_value}% to {MIN_VOLUME}%.",
        )
    else:
        append_localized(
            replies,
            language,
            f"Am setat volumul de la {current_value}% la {new_value}%.",
            f"I set the volume from {current_value}% to {new_value}%.",
        )

    return new_value


def create_seat_heating_response(
    replies: list[str],
    actions: list[VehicleAction],
    current_value: int,
    requested_value: int,
    zone: str,
    language: str = "ro",
    report_limit: bool = True,
    report_stop: bool = True,
) -> int:
    new_value = max(
        MIN_SEAT_HEATING,
        min(MAX_SEAT_HEATING, requested_value),
    )
    zone_name_ro = "șoferului" if zone == "driver" else "pasagerului"
    zone_name_en = "driver's" if zone == "driver" else "passenger's"
    zone_stop_name_ro = "șofer" if zone == "driver" else "pasager"

    actions.append(
        VehicleAction(
            type=ACTION_SET_SEAT_HEATING,
            params={"zone": zone, "level": new_value},
        )
    )

    if (
        new_value == current_value
        and MIN_SEAT_HEATING <= requested_value <= MAX_SEAT_HEATING
    ):
        append_localized(
            replies,
            language,
            f"Încălzirea scaunului {zone_name_ro} este deja la nivelul "
            f"{current_value}.",
            f"The {zone_name_en} seat heating is already at level "
            f"{current_value}.",
        )
        return current_value

    if requested_value > MAX_SEAT_HEATING:
        if report_limit:
            append_limit_notice(
                replies,
                language,
                f"Nivelul maxim pentru încălzirea scaunelor este "
                f"{MAX_SEAT_HEATING}.",
                f"The maximum seat-heating level is {MAX_SEAT_HEATING}.",
            )
        if report_stop:
            append_localized(
                replies,
                language,
                f"Am setat încălzirea scaunului {zone_name_ro} de la nivelul "
                f"{current_value} la nivelul {MAX_SEAT_HEATING}.",
                f"I set the {zone_name_en} seat heating from level "
                f"{current_value} to level {MAX_SEAT_HEATING}.",
            )
    elif requested_value < MIN_SEAT_HEATING:
        if report_limit:
            append_limit_notice(
                replies,
                language,
                f"Nivelul minim pentru încălzirea scaunelor este "
                f"{MIN_SEAT_HEATING}.",
                f"The minimum seat-heating level is {MIN_SEAT_HEATING}.",
            )
        if report_stop:
            append_localized(
                replies,
                language,
                f"Am oprit încălzirea în scaune pentru {zone_stop_name_ro}.",
                f"I turned off the seat heating for the "
                f"{'driver' if zone == 'driver' else 'passenger'}.",
            )
    elif new_value == MIN_SEAT_HEATING:
        append_localized(
            replies,
            language,
            f"Am oprit încălzirea scaunului {zone_name_ro}.",
            f"I turned off the {zone_name_en} seat heating.",
        )
    else:
        append_localized(
            replies,
            language,
            f"Am setat încălzirea scaunului {zone_name_ro} de la nivelul "
            f"{current_value} la nivelul {new_value}.",
            f"I set the {zone_name_en} seat heating from level "
            f"{current_value} to level {new_value}.",
        )

    return new_value


def create_fan_response(
    replies: list[str],
    actions: list[VehicleAction],
    current_value: int,
    requested_value: int,
    language: str = "ro",
) -> int:
    new_value = max(MIN_FAN_SPEED, min(MAX_FAN_SPEED, requested_value))

    actions.append(
        VehicleAction(
            type=ACTION_SET_FAN_SPEED,
            params={"level": new_value},
        )
    )

    if (
        new_value == current_value
        and MIN_FAN_SPEED <= requested_value <= MAX_FAN_SPEED
    ):
        append_localized(
            replies,
            language,
            f"Ventilatorul este deja la nivelul {current_value}.",
            f"The fan is already at level {current_value}.",
        )
        return current_value

    if requested_value > MAX_FAN_SPEED:
        append_limit_notice(
            replies,
            language,
            f"Nivelul maxim al ventilatorului este {MAX_FAN_SPEED}.",
            f"The maximum fan level is {MAX_FAN_SPEED}.",
        )
        append_localized(
            replies,
            language,
            f"Am setat ventilatorul de la nivelul {current_value} la nivelul "
            f"{MAX_FAN_SPEED}.",
            f"I set the fan from level {current_value} to level "
            f"{MAX_FAN_SPEED}.",
        )
    elif requested_value < MIN_FAN_SPEED:
        append_limit_notice(
            replies,
            language,
            f"Nivelul minim al ventilatorului este {MIN_FAN_SPEED}.",
            f"The minimum fan level is {MIN_FAN_SPEED}.",
        )
        append_localized(
            replies,
            language,
            "Am oprit ventilatorul.",
            "I turned off the fan.",
        )
    elif new_value == MIN_FAN_SPEED:
        append_localized(
            replies,
            language,
            "Am oprit ventilatorul.",
            "I turned off the fan.",
        )
    else:
        append_localized(
            replies,
            language,
            f"Am setat ventilatorul de la nivelul {current_value} la nivelul "
            f"{new_value}.",
            f"I set the fan from level {current_value} to level {new_value}.",
        )

    return new_value

def has_explicit_zone(message: str) -> bool:
    normalized_message = normalize_text(message)

    return (
        "sofer" in normalized_message
        or "pasager" in normalized_message
        or "driver" in normalized_message
        or "passenger" in normalized_message
    )


def detect_state_topics(message: str) -> set[str]:
    """Detect which state categories the user explicitly asks about."""
    text = normalize_text(message)

    if any(
        phrase in text
        for phrase in (
            "starea masinii",
            "starea vehiculului",
            "setarile masinii",
            "setarile actuale",
            "toate setarile",
            "toate informatiile",
            "vehicle state",
            "car status",
            "current settings",
            "all settings",
            "all vehicle settings",
        )
    ):
        return {"all"}

    topics: set[str] = set()

    if (
        "temperatur" in text
        or "temperature" in text
        or "cate grade" in text
        or "ce grade" in text
        or "degrees" in text
    ):
        topics.add("temperature")

    if (
        ("scaun" in text and "incalz" in text)
        or (
            "seat" in text
            and (
                "heating" in text
                or "heat" in text
                or "warm" in text
            )
        )
    ):
        topics.add("seat_heating")

    if "volum" in text or "volume" in text:
        topics.add("volume")

    if (
        "ventilator" in text
        or "viteza ventilator" in text
        or "fan" in text
    ):
        topics.add("fan")

    if (
        "melod" in text
        or "cantec" in text
        or "song" in text
        or "track" in text
        or "ce ascult" in text
        or "ce ruleaza" in text
        or "what is playing" in text
    ):
        topics.add("song")

    if (
        "lumina ambient" in text
        or "ambient light" in text
        or "ambient lighting" in text
        or "ambient color" in text
    ):
        topics.add("ambient_light")

    if (
        "redare" in text
        or "muzica ruleaza" in text
        or "playback" in text
        or "music playing" in text
        or "is the music playing" in text
    ):
        topics.add("playback")

    if "sunet dezactivat" in text or "mute" in text:
        topics.add("mute")

    if (
        "aer conditionat" in text
        or "aerul conditionat" in text
        or "climatizare" in text
        or "air conditioning" in text
        or "climate control" in text
        or any(
            token.strip(".,?!") == "ac"
            for token in text.split()
        )
    ):
        topics.add("ac")

    return topics


def detect_state_zones(message: str) -> set[str]:
    text = normalize_text(message)
    zones: set[str] = set()

    if "sofer" in text or "driver" in text:
        zones.add("driver")
    if "pasager" in text or "passenger" in text:
        zones.add("passenger")

    return zones


def resolve_target_zones(message: str, speaker: str | None) -> list[str]:
    requested_zones = detect_state_zones(message)

    if requested_zones:
        return list(requested_zones)

    if speaker in VEHICLE_ZONES:
        return [speaker]

    return ["driver", "passenger"]

def has_first_person_reference(message: str) -> bool:
    """Detect wording that refers to the currently active cabin role."""
    text = normalize_text(message)

    return bool(
        re.search(
            r"(?:\b(?:eu|mie|mine|mea|meu|imi|sunt)\b|"
            r"(?:^|[\s-])mi\b)",
            text,
        )
    )


def create_state_response(
    topics: set[str],
    zones: set[str],
    temperature_driver: int,
    temperature_passenger: int,
    seat_heating_driver: int,
    seat_heating_passenger: int,
    volume: int,
    fan_speed: int,
    current_song: str,
    is_playing: bool,
    is_muted: bool,
    ambient_light: str,
    ac_enabled: bool,
    language: str = "ro",
) -> str:
    if not topics or "all" in topics:
        if language == "ro":
            return (
                "Starea mașinii este:\n"
                f"Temperatură șofer: {temperature_driver}°C\n"
                f"Temperatură pasager: {temperature_passenger}°C\n"
                f"Încălzire scaun șofer: nivelul {seat_heating_driver}\n"
                f"Încălzire scaun pasager: nivelul {seat_heating_passenger}\n"
                f"Volum: {volume}%\n"
                f"Ventilator: nivelul {fan_speed}\n"
                f"Melodie: {current_song}\n"
                f"Redare activă: {'da' if is_playing else 'nu'}\n"
                f"Sunet dezactivat: {'da' if is_muted else 'nu'}\n"
                f"Aer condiționat: {'pornit' if ac_enabled else 'oprit'}\n"
                f"Lumină ambientală: {ambient_light}"
            )

        return (
            "The vehicle state is:\n"
            f"Driver temperature: {temperature_driver}°C\n"
            f"Passenger temperature: {temperature_passenger}°C\n"
            f"Driver seat heating: level {seat_heating_driver}\n"
            f"Passenger seat heating: level {seat_heating_passenger}\n"
            f"Volume: {volume}%\n"
            f"Fan: level {fan_speed}\n"
            f"Song: {current_song}\n"
            f"Playback active: {'yes' if is_playing else 'no'}\n"
            f"Muted: {'yes' if is_muted else 'no'}\n"
            f"Air conditioning: {'on' if ac_enabled else 'off'}\n"
            f"Ambient light: {ambient_light}"
        )

    replies: list[str] = []

    if "temperature" in topics:
        if zones == {"driver"}:
            append_localized(
                replies,
                language,
                f"Temperatura la șofer este {temperature_driver}°C.",
                f"The driver's temperature is {temperature_driver}°C.",
            )
        elif zones == {"passenger"}:
            append_localized(
                replies,
                language,
                f"Temperatura la pasager este {temperature_passenger}°C.",
                f"The passenger's temperature is {temperature_passenger}°C.",
            )
        else:
            append_localized(
                replies,
                language,
                f"Temperatura este {temperature_driver}°C la șofer și "
                f"{temperature_passenger}°C la pasager.",
                f"The temperature is {temperature_driver}°C for the driver "
                f"and {temperature_passenger}°C for the passenger.",
            )

    if "seat_heating" in topics:
        if zones == {"driver"}:
            append_localized(
                replies,
                language,
                f"Încălzirea scaunului șoferului este la nivelul "
                f"{seat_heating_driver}.",
                f"The driver's seat heating is at level {seat_heating_driver}.",
            )
        elif zones == {"passenger"}:
            append_localized(
                replies,
                language,
                f"Încălzirea scaunului pasagerului este la nivelul "
                f"{seat_heating_passenger}.",
                f"The passenger's seat heating is at level "
                f"{seat_heating_passenger}.",
            )
        else:
            append_localized(
                replies,
                language,
                f"Încălzirea scaunelor este la nivelul {seat_heating_driver} "
                f"la șofer și la nivelul {seat_heating_passenger} la pasager.",
                f"Seat heating is at level {seat_heating_driver} for the "
                f"driver and level {seat_heating_passenger} for the passenger.",
            )

    if "volume" in topics:
        append_localized(
            replies,
            language,
            f"Volumul este {volume}%.",
            f"The volume is {volume}%.",
        )

    if "fan" in topics:
        append_localized(
            replies,
            language,
            f"Ventilatorul este la nivelul {fan_speed}.",
            f"The fan is at level {fan_speed}.",
        )

    if "song" in topics:
        append_localized(
            replies,
            language,
            f"Melodia curentă este „{current_song}”.",
            f'The current song is "{current_song}".',
        )

    if "ambient_light" in topics:
        append_localized(
            replies,
            language,
            f"Lumina ambientală este setată pe {ambient_light}.",
            f"The ambient light is set to {ambient_light}.",
        )

    if "playback" in topics:
        append_localized(
            replies,
            language,
            f"Redarea este {'activă' if is_playing else 'oprită'}.",
            f"Playback is {'active' if is_playing else 'stopped'}.",
        )

    if "mute" in topics:
        append_localized(
            replies,
            language,
            f"Sunetul este {'dezactivat' if is_muted else 'activ'}.",
            f"Sound is {'muted' if is_muted else 'active'}.",
        )

    if "ac" in topics:
        append_localized(
            replies,
            language,
            f"Aerul condiționat este "
            f"{'pornit' if ac_enabled else 'oprit'}.",
            f"Air conditioning is {'on' if ac_enabled else 'off'}.",
        )

    return "\n".join(replies)


def require_integer_parameter(
    params: dict[str, object],
    name: str,
) -> int:
    value = params.get(name)

    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"Parameter '{name}' must be an integer")

    return value


def require_string_parameter(
    params: dict[str, object],
    name: str,
) -> str:
    value = params.get(name)

    if not isinstance(value, str):
        raise ValueError(f"Parameter '{name}' must be a string")

    return value


def process_explicit_numeric_command(
    message: str,
    current_temperature: int,
    current_volume: int,
    current_passenger_temperature: int,
    current_driver_seat_heating: int,
    current_passenger_seat_heating: int,
    current_fan_speed: int,
    language: str,
    speaker: str | None = None,
) -> AIResponse | None:
    """Execute an unambiguous absolute numeric comfort command locally.

    Explicit values must never be turned into confirmation questions. The
    normalizer handles common exact commands and applies the same bounds as
    the regular tool-processing path. Relative and more complex messages
    remain delegated to the OpenAI tool flow.
    """
    text = normalize_text(message)
    values = [
        int(value)
        for value in re.findall(r"(?<![a-z])[+-]?\d+(?![a-z])", text)
    ]
    signed_value_match = re.search(
        r"(?<![a-z])([+-])\s*(\d+)(?![a-z])",
        text,
    )

    if len(values) != 1:
        return None

    if re.search(r"\b(?:cat|ce|what|how)\b", text):
        return None

    if re.search(r"\b(?:cu|by)\b", text):
        return None

    command_words = (
        "pune",
        "da",
        "dai",
        "seteaza",
        "vreau",
        "porneste",
        "regleaza",
        "set",
        "put",
        "change",
        "turn",
    )
    has_command_word = any(
        re.search(rf"\b{word}\b", text)
        for word in command_words
    )
    target_temperature = "temperatura" in text or "temperature" in text
    target_volume = "volum" in text or "volume" in text
    target_seat_heating = (
        ("incalzire" in text and "scaun" in text)
        or "seat heating" in text
    )
    target_fan = "ventilator" in text or re.search(r"\bfan\b", text)
    targets = sum(
        [
            target_temperature,
            target_volume,
            target_seat_heating,
            bool(target_fan),
        ]
    )

    if targets != 1:
        return None

    target_prefix = text.startswith(
        (
            "temperatura",
            "temperature",
            "volum",
            "volume",
            "incalzire",
            "seat heating",
            "heating seat",
            "heating seats",
            "ventilator",
            "fan",
            "fan speed",
            "viteza ventilator",
            "nivel ventilator",
            "nivelul ventilator",
        )
    )
    levelled_target = (
        (target_fan or target_seat_heating)
        and text.startswith(("nivel ", "nivelul ", "viteza "))
    )
    has_numeric_command = (
        len(values) == 1
        and (
            signed_value_match is not None
            or "treapta" in text
            or target_prefix
            or levelled_target
        )
    )
    if not has_command_word and not has_numeric_command:
        return None

    requested_value = values[0]
    relative_delta = (
        int(
            f"{signed_value_match.group(1)}"
            f"{signed_value_match.group(2)}"
        )
        if signed_value_match is not None
        and not re.search(r"\b(?:la|to)\b", text)
        else None
    )

    def resolve_requested_value(current_value: int) -> int:
        if relative_delta is not None:
            return current_value + relative_delta
        return requested_value

    replies: list[str] = []
    actions: list[VehicleAction] = []
    requested_zones = detect_state_zones(message)

    if len(requested_zones) > 1:
        return None

    zones = resolve_target_zones(message, speaker)

    if target_temperature:
        current_values = {
            "driver": current_temperature,
            "passenger": current_passenger_temperature,
        }
        for zone in zones:
            create_temperature_response(
                replies,
                actions,
                current_values[zone],
                resolve_requested_value(current_values[zone]),
                zone,
                language,
            )

    elif target_volume:
        create_volume_response(
            replies,
            actions,
            current_volume,
            resolve_requested_value(current_volume),
            language,
        )

    elif target_seat_heating:
        current_values = {
            "driver": current_driver_seat_heating,
            "passenger": current_passenger_seat_heating,
        }
        combined_stop = (
            all(
                resolve_requested_value(current_values[zone])
                < MIN_SEAT_HEATING
                for zone in zones
            )
            and set(zones) == set(VEHICLE_ZONES)
        )

        if combined_stop:
            append_limit_notice(
                replies,
                language,
                f"Nivelul minim pentru încălzirea scaunelor este "
                f"{MIN_SEAT_HEATING}.",
                f"The minimum seat-heating level is {MIN_SEAT_HEATING}.",
            )

        for zone in zones:
            create_seat_heating_response(
                replies,
                actions,
                current_values[zone],
                resolve_requested_value(current_values[zone]),
                zone,
                language,
                report_limit=not combined_stop,
                report_stop=not combined_stop,
            )

        if combined_stop:
            append_localized(
                replies,
                language,
                "Am oprit încălzirea în scaune.",
                "I turned off the seat heating.",
            )

    else:
        create_fan_response(
            replies,
            actions,
            current_fan_speed,
            resolve_requested_value(current_fan_speed),
            language,
        )

    return AIResponse(
        reply="\n".join(replies),
        actions=actions,
        allowed=True,
    )


def process_temperature_feeling_command(
    message: str,
    current_temperature: int,
    current_passenger_temperature: int,
    language: str,
    speaker: str | None,
) -> AIResponse | None:
    """Translate clear comfort feelings into deterministic temperature changes."""
    text = normalize_text(message)

    if re.search(r"\bnu\b", text):
        return None

    first_person_feeling = re.compile(
        r"\b(?:imi|mi)(?:\s*-\s*|\s+)(?:e|este)\s+"
        r"(?:foarte\s+|extrem\s+de\s+|super\s+|prea\s+|tare\s+|cam\s+)?"
        r"(?:frig|rece|cald)\b"
    )
    cold_requested = bool(
        re.search(r"\b(?:frig|rece)\b", text)
        and (
            first_person_feeling.search(text)
            or any(
                phrase in text
                for phrase in (
                    "sunt inghetat",
                    "tremur de frig",
                    "mor de frig",
                    "ce frig e",
                    "ce rece e",
                    "e frig",
                    "este frig",
                    "e rece",
                    "este rece",
                    "e prea frig",
                    "este prea frig",
                    "e prea rece",
                    "este prea rece",
                )
            )
        )
    )
    hot_requested = bool(
        re.search(r"\bcald\b", text)
        and (
            first_person_feeling.search(text)
            or any(
                phrase in text
                for phrase in (
                    "sunt incins",
                    "ma sufoc de cald",
                    "mor de cald",
                    "ma topesc de cald",
                    "e cald",
                    "este cald",
                    "ce cald e",
                    "e prea cald",
                    "este prea cald",
                )
            )
        )
    )

    if cold_requested == hot_requested:
        return None

    generic_feeling = any(
        phrase in text
        for phrase in (
            "ce frig e",
            "ce rece e",
            "ce cald e",
            "e prea frig",
            "este prea frig",
            "e prea rece",
            "este prea rece",
            "e prea cald",
            "este prea cald",
        )
    )
    intense = not generic_feeling and any(
        re.search(rf"\b{term}\b", text)
        for term in (
            "foarte",
            "extrem",
            "super",
            "prea",
            "tare",
            "inghetat",
            "tremur",
            "mor",
            "sufoc",
            "incins",
            "topesc",
            "very",
            "extremely",
            "freezing",
            "boiling",
        )
    )
    step = (
        TEMPERATURE_INTENSE_COMFORT_STEP
        if intense
        else TEMPERATURE_COMFORT_STEP
    )
    direction = step if cold_requested else -step
    replies: list[str] = []
    actions: list[VehicleAction] = []

    current_values = {
        "driver": current_temperature,
        "passenger": current_passenger_temperature,
    }
    if has_first_person_reference(message):
        zones = [speaker] if speaker in VEHICLE_ZONES else ["driver"]
    else:
        zones = list(VEHICLE_ZONES)

    for zone in zones:
        current_value = current_values[zone]
        create_temperature_response(
            replies,
            actions,
            current_value,
            current_value + direction,
            zone,
            language,
        )

    return AIResponse(
        reply="\n".join(replies),
        actions=actions,
        allowed=True,
    )


def process_explicit_ambient_command(
    message: str,
    language: str,
    current_ambient_light: str = DEFAULT_AMBIENT_LIGHT,
) -> AIResponse | None:
    """Execute a simple, explicit ambient-light command locally."""
    text = normalize_text(message)
    ambient_light_mentioned = (
        "lumina ambientala" in text
        or "ambient light" in text
        or "ambient lighting" in text
    )

    if not ambient_light_mentioned:
        return None

    command_words = ("seteaza", "schimba", "pune", "set", "change", "turn")
    if not any(
        re.search(rf"\b{word}\b", text)
        for word in command_words
    ):
        return None

    other_action_terms = (
        "temperatura",
        "temperature",
        "volum",
        "volume",
        "scaun",
        "seat",
        "ventilator",
        "fan",
        "melodie",
        "song",
        "muzica",
        "music",
        "reset",
    )
    if any(term in text for term in other_action_terms):
        return None

    match = re.search(
        r"(?:lumina ambientala|ambient lighting?|ambient light)"
        r"\s+(?:pe|la|to)\s+([a-z]+)",
        text,
    )
    if match is None:
        return None

    requested_color = match.group(1)
    color = AMBIENT_COLOR_ALIASES.get(requested_color)
    if color is None:
        supported_colors_ro = ", ".join(AMBIENT_COLOR_LABELS_RO.values())
        supported_colors_en = ", ".join(AMBIENT_LIGHTS)
        return AIResponse(
            reply=(
                f"Culoarea solicitată nu este acceptată. Te rog să alegi una "
                f"dintre culorile suportate: {supported_colors_ro}."
                if language == "ro"
                else f"The requested color is not supported. Please choose "
                f"one of the supported colors: {supported_colors_en}."
            ),
            actions=[],
            allowed=False,
        )

    if color == current_ambient_light:
        return AIResponse(
            reply=(
                f"Lumina ambientală este deja setată pe culoarea "
                f"{AMBIENT_COLOR_LABELS_RO[color]}."
                if language == "ro"
                else f"The ambient light is already {color}."
            ),
            actions=[],
            allowed=True,
        )

    return AIResponse(
        reply=(
            f"Am setat lumina ambientală pe {AMBIENT_COLOR_LABELS_RO[color]}."
            if language == "ro"
            else f"I set the ambient light to {color}."
        ),
        actions=[
            VehicleAction(
                type=ACTION_SET_AMBIENT_LIGHT,
                params={"color": color},
            )
        ],
        allowed=True,
    )


def detect_memory_mode(text: str) -> str | None:
    if any(
        re.search(rf"\b{phrase}\b", text)
        for phrase in ("inceput", "initial", "prima", "first")
    ):
        return "first"

    if any(
        re.search(rf"\b{phrase}\b", text)
        for phrase in (
            "anterioara",
            "precedenta",
            "previous",
            "prior",
            "last",
        )
    ):
        return "previous"

    return None


def has_restore_intent(text: str) -> bool:
    return any(
        re.search(rf"\b{phrase}\b", text)
        for phrase in (
            "revino",
            "revin",
            "return",
            "restore",
            "pune",
            "seteaza",
            "set",
            "dai",
            "da",
        )
    )


def historical_action_values(
    action_history: list[VehicleAction],
    action_type: str,
    value_key: str,
    mode: str,
    zone_key: str | None = None,
) -> dict[str, int]:
    values_by_key: dict[str, list[int]] = {}

    for action in action_history:
        if action.type != action_type:
            continue

        value = action.params.get(value_key)
        if isinstance(value, bool) or not isinstance(value, int):
            continue

        key = "global"
        if zone_key is not None:
            zone = action.params.get(zone_key)
            if zone not in VEHICLE_ZONES:
                continue
            key = str(zone)

        values_by_key.setdefault(key, []).append(value)

    selected_values: dict[str, int] = {}
    for key, values in values_by_key.items():
        if mode == "first":
            selected_values[key] = values[0]
        elif len(values) >= 2:
            selected_values[key] = values[-2]

    return selected_values


def memory_unavailable_response(
    feature_ro: str,
    feature_en: str,
    language: str,
) -> AIResponse:
    return AIResponse(
        reply=(
            f"Nu există nicio valoare memorată pentru {feature_ro} în "
            "conversația curentă."
            if language == "ro"
            else f"There is no remembered value for {feature_en} in the current chat."
        ),
        actions=[],
        allowed=False,
    )


def process_memory_command(
    message: str,
    action_history: list[VehicleAction],
    current_temperature: int,
    current_passenger_temperature: int,
    current_driver_seat_heating: int,
    current_passenger_seat_heating: int,
    current_volume: int,
    current_fan_speed: int,
    current_ambient_light: str,
    language: str,
    speaker: str,
) -> AIResponse | None:
    """Restore explicit session values without asking OpenAI to guess them."""
    text = normalize_text(message)
    memory_mode = detect_memory_mode(text)

    if memory_mode is None or not has_restore_intent(text):
        return None

    target_temperature = "temperatur" in text or "temperature" in text
    target_volume = "volum" in text or "volume" in text
    target_seat_heating = (
        ("incalz" in text and "temperatur" not in text)
        or "seat heating" in text
    )
    target_fan = "ventilator" in text or re.search(r"\bfan\b", text)
    target_ambient = (
        "lumina ambient" in text
        or "ambient light" in text
        or "ambient lighting" in text
    )
    targets = sum(
        [
            target_temperature,
            target_volume,
            target_seat_heating,
            bool(target_fan),
            target_ambient,
        ]
    )

    if targets != 1:
        return None

    if target_temperature:
        historical_values = historical_action_values(
            action_history,
            ACTION_SET_TEMPERATURE,
            "value",
            memory_mode,
            "zone",
        )
        if not historical_values:
            return memory_unavailable_response(
                "temperatură",
                "temperature",
                language,
            )

        current_values = {
            "driver": current_temperature,
            "passenger": current_passenger_temperature,
        }
        requested_zones = detect_state_zones(message)
        if not requested_zones and has_first_person_reference(message):
            zones = {speaker} if speaker in VEHICLE_ZONES else set()
        else:
            zones = requested_zones or set(historical_values)
        replies: list[str] = []
        actions: list[VehicleAction] = []

        for zone in ("driver", "passenger"):
            if zone in zones and zone in historical_values:
                create_temperature_response(
                    replies,
                    actions,
                    current_values[zone],
                    historical_values[zone],
                    zone,
                    language,
                )

        if not replies:
            return memory_unavailable_response(
                "temperatură pentru zona solicitată",
                "temperature for the requested zone",
                language,
            )

        return AIResponse(reply="\n".join(replies), actions=actions)

    if target_volume:
        historical_values = historical_action_values(
            action_history,
            ACTION_SET_VOLUME,
            "value",
            memory_mode,
        )
        remembered_value = historical_values.get("global")
        if remembered_value is None:
            return memory_unavailable_response("volum", "volume", language)

        replies: list[str] = []
        actions: list[VehicleAction] = []
        create_volume_response(
            replies,
            actions,
            current_volume,
            remembered_value,
            language,
        )
        return AIResponse(reply="\n".join(replies), actions=actions)

    if target_seat_heating:
        historical_values = historical_action_values(
            action_history,
            ACTION_SET_SEAT_HEATING,
            "level",
            memory_mode,
            "zone",
        )
        current_values = {
            "driver": current_driver_seat_heating,
            "passenger": current_passenger_seat_heating,
        }
        requested_zones = detect_state_zones(message)
        if not requested_zones and has_first_person_reference(message):
            zones = {speaker} if speaker in VEHICLE_ZONES else set()
        else:
            zones = requested_zones or set(historical_values)
        replies = []
        actions = []

        for zone in ("driver", "passenger"):
            if zone in zones and zone in historical_values:
                create_seat_heating_response(
                    replies,
                    actions,
                    current_values[zone],
                    historical_values[zone],
                    zone,
                    language,
                )

        if not replies:
            return memory_unavailable_response(
                "încălzirea scaunelor",
                "seat heating",
                language,
            )

        return AIResponse(reply="\n".join(replies), actions=actions)

    if target_fan:
        historical_values = historical_action_values(
            action_history,
            ACTION_SET_FAN_SPEED,
            "level",
            memory_mode,
        )
        remembered_value = historical_values.get("global")
        if remembered_value is None:
            return memory_unavailable_response("ventilator", "fan", language)

        replies = []
        actions = []
        create_fan_response(
            replies,
            actions,
            current_fan_speed,
            remembered_value,
            language,
        )
        return AIResponse(reply="\n".join(replies), actions=actions)

    colors = [
        action.params.get("color")
        for action in action_history
        if action.type == ACTION_SET_AMBIENT_LIGHT
        and action.params.get("color") in AMBIENT_LIGHTS
    ]
    remembered_color = None
    if colors:
        remembered_color = (
            colors[0]
            if memory_mode == "first"
            else colors[-2] if len(colors) >= 2 else None
        )

    if remembered_color is None:
        return memory_unavailable_response(
            "lumina ambientală",
            "ambient light",
            language,
        )

    if remembered_color == current_ambient_light:
        reply = (
            f"Lumina ambientală este deja setată pe culoarea "
            f"{AMBIENT_COLOR_LABELS_RO[remembered_color]}."
            if language == "ro"
            else f"The ambient light is already {remembered_color}."
        )
        return AIResponse(reply=reply, actions=[])

    return AIResponse(
        reply=(
            f"Am setat lumina ambientală pe "
            f"{AMBIENT_COLOR_LABELS_RO[remembered_color]}."
            if language == "ro"
            else f"I set the ambient light to {remembered_color}."
        ),
        actions=[
            VehicleAction(
                type=ACTION_SET_AMBIENT_LIGHT,
                params={"color": remembered_color},
            )
        ],
    )


def process_forbidden_song_memory_command(
    message: str,
    language: str,
) -> AIResponse | None:
    text = normalize_text(message)
    song_mentioned = (
        "melod" in text
        or "cantec" in text
        or "song" in text
        or "track" in text
    )
    absolute_reference = any(
        re.search(rf"\b{phrase}\b", text)
        for phrase in (
            "prima",
            "inceput",
            "initiala",
            "first",
            "initial",
            "memorata",
            "remembered",
        )
    )

    if not song_mentioned or not absolute_reference:
        return None

    return AIResponse(
        reply=(
            "Pentru melodii sunt disponibile doar comenzile pentru melodia "
            "anterioară sau următoare."
            if language == "ro"
            else "For songs, only previous-song or next-song commands are available."
        ),
        actions=[],
        allowed=False,
    )


def process_media_playback_command(
    message: str,
    language: str,
) -> AIResponse | None:
    normalized_message = re.sub(
        r"[.!?]+$",
        "",
        normalize_text(message),
    ).strip()

    pause_commands = {
        "pune muzica pe pauza",
        "pune muzica in pauza",
        "pune redarea pe pauza",
        "opreste muzica",
        "opreste redarea",
        "pause music",
        "pause the music",
        "pause playback",
        "put music on pause",
        "put the music on pause",
        "put playback on pause",
        "put the playback on pause",
    }

    play_commands = {
        "porneste muzica",
        "porneste redarea",
        "continua muzica",
        "continua redarea",
        "play music",
        "play the music",
        "start music",
        "start the music",
        "turn music on",
        "turn the music on",
        "resume music",
        "resume playback",
    }

    mute_commands = {
        "opreste sunetul",
        "dezactiveaza sunetul",
        "pune pe mute",
        "da mute",
        "muteaza sunetul",
        "mute",
        "mute the sound",
        "mute music",
        "turn sound off",
        "turn the sound off",
    }

    unmute_commands = {
        "porneste sunetul",
        "activeaza sunetul",
        "scoate sunetul de pe mute",
        "scoate de pe mute",
        "unmute",
        "unmute the sound",
        "unmute music",
        "turn sound on",
        "turn the sound on",
    }

    if normalized_message in pause_commands:
        return AIResponse(
            reply=(
                "Am pus muzica pe pauză."
                if language == "ro"
                else "I paused the music."
            ),
            actions=[
                VehicleAction(
                    type=ACTION_MEDIA_PAUSE,
                    params={},
                )
            ],
            allowed=True,
        )

    if normalized_message in play_commands:
        return AIResponse(
            reply=(
                "Am pornit muzica."
                if language == "ro"
                else "I started the music."
            ),
            actions=[
                VehicleAction(
                    type=ACTION_MEDIA_PLAY,
                    params={},
                )
            ],
            allowed=True,
        )

    if normalized_message in mute_commands:
        return AIResponse(
            reply=(
                "Am oprit sunetul."
                if language == "ro"
                else "I muted the sound."
            ),
            actions=[
                VehicleAction(
                    type=ACTION_MEDIA_MUTE,
                    params={},
                )
            ],
            allowed=True,
        )

    if normalized_message in unmute_commands:
        return AIResponse(
            reply=(
                "Am pornit sunetul."
                if language == "ro"
                else "I unmuted the sound."
            ),
            actions=[
                VehicleAction(
                    type=ACTION_MEDIA_UNMUTE,
                    params={},
                )
            ],
            allowed=True,
        )

    return None


def process_message(
    message: str,
    current_temperature: int = DEFAULT_DRIVER_TEMPERATURE,
    current_volume: int = DEFAULT_VOLUME,
    speaker: str | None = None,
    current_passenger_temperature: int = DEFAULT_PASSENGER_TEMPERATURE,
    current_driver_seat_heating: int = MIN_SEAT_HEATING,
    current_passenger_seat_heating: int = MIN_SEAT_HEATING,
    current_fan_speed: int = DEFAULT_FAN_SPEED,
    current_song: str = DEFAULT_CURRENT_SONG,
    is_playing: bool = DEFAULT_IS_PLAYING,
    is_muted: bool = DEFAULT_IS_MUTED,
    ambient_light: str = DEFAULT_AMBIENT_LIGHT,
    ac_enabled: bool = DEFAULT_AC_ENABLED,
    conversation_history: list[dict[str, str]] | None = None,
    action_history: list[VehicleAction] | None = None,
) -> AIResponse:
    response_language = detect_response_language(message)

    if response_language in {LANGUAGE_MIXED, LANGUAGE_UNSUPPORTED}:
        return AIResponse(
            reply=SUPPORTED_LANGUAGE_ERROR,
            actions=[],
            allowed=False,
        )

    safety_response = safety_check(message)

    if safety_response is not None:
        return safety_response

    media_response = process_media_playback_command(
        message,
        response_language,
    )

    if media_response is not None:
        return media_response

    client = get_client()

    if client is None:
        return AIResponse(
            reply=(
                "Cheia OpenAI nu a fost găsită."
                if response_language == "ro"
                else "The OpenAI key was not found."
            ),
            actions=[],
            allowed=False,
        )

    model = os.getenv("OPENAI_MODEL")

    if not model:
        return AIResponse(
            reply=(
                "Modelul OpenAI nu este configurat."
                if response_language == "ro"
                else "The OpenAI model is not configured."
            ),
            actions=[],
            allowed=False,
        )

    temperature_setting = os.getenv("OPENAI_TEMPERATURE")

    if not temperature_setting:
        return AIResponse(
            reply=(
                "Temperatura OpenAI nu este configurată."
                if response_language == "ro"
                else "The OpenAI temperature is not configured."
            ),
            actions=[],
            allowed=False,
        )

    try:
        ai_temperature = float(temperature_setting)
    except ValueError:
        return AIResponse(
            reply=(
                "Temperatura OpenAI nu este validă."
                if response_language == "ro"
                else "The OpenAI temperature is invalid."
            ),
            actions=[],
            allowed=False,
        )

    if not 0 <= ai_temperature <= 2:
        return AIResponse(
            reply=(
                "Temperatura OpenAI trebuie să fie între 0 și 2."
                if response_language == "ro"
                else "The OpenAI temperature must be between 0 and 2."
            ),
            actions=[],
            allowed=False,
        )

    forbidden_song_response = process_forbidden_song_memory_command(
        message,
        response_language,
    )
    if forbidden_song_response is not None:
        return forbidden_song_response

    memory_response = process_memory_command(
        message=message,
        action_history=action_history or [],
        current_temperature=current_temperature,
        current_passenger_temperature=current_passenger_temperature,
        current_driver_seat_heating=current_driver_seat_heating,
        current_passenger_seat_heating=current_passenger_seat_heating,
        current_volume=current_volume,
        current_fan_speed=current_fan_speed,
        current_ambient_light=ambient_light,
        language=response_language,
        speaker=speaker,
    )
    if memory_response is not None:
        return memory_response

    feeling_response = process_temperature_feeling_command(
        message=message,
        current_temperature=current_temperature,
        current_passenger_temperature=current_passenger_temperature,
        language=response_language,
        speaker=speaker,
    )
    if feeling_response is not None:
        return feeling_response

    direct_response = process_explicit_numeric_command(
        message=message,
        current_temperature=current_temperature,
        current_volume=current_volume,
        current_passenger_temperature=current_passenger_temperature,
        current_driver_seat_heating=current_driver_seat_heating,
        current_passenger_seat_heating=current_passenger_seat_heating,
        current_fan_speed=current_fan_speed,
        language=response_language,
        speaker=speaker,
    )
    if direct_response is not None:
        return direct_response

    ambient_response = process_explicit_ambient_command(
        message=message,
        language=response_language,
        current_ambient_light=ambient_light,
    )
    if ambient_response is not None:
        return ambient_response

    response_language_name = (
        "Romanian" if response_language == "ro" else "English"
    )

    user_context = f"""
Current vehicle state:
- driver temperature: {current_temperature}°C
- passenger temperature: {current_passenger_temperature}°C
- driver seat heating: {current_driver_seat_heating}
- passenger seat heating: {current_passenger_seat_heating}
- volume: {current_volume}%
- fan speed: {current_fan_speed}
- current song: {current_song}
- is playing: {is_playing}
- is muted: {is_muted}
- air conditioning enabled: {ac_enabled}
- ambient light: {ambient_light}
- speaker: {speaker}

Required response language: {response_language_name}
Use this language for every user-facing sentence.

User message:
{message}
"""

    try:
        messages = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            }
        ]

        for history_message in (conversation_history or [])[
            -MAX_CONVERSATION_MESSAGES:
        ]:
            role = history_message.get("role")
            content = history_message.get("content", "").strip()

            if role in {"user", "assistant"} and content:
                messages.append(
                    {
                        "role": role,
                        "content": content,
                    }
                )

        messages.append(
            {
                "role": "user",
                "content": user_context,
            }
        )

        response = client.chat.completions.create(
            model=model,
            temperature=ai_temperature,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
        )

        assistant_message = response.choices[0].message
        tool_calls = assistant_message.tool_calls or []

        if not tool_calls:
            return AIResponse(
                reply=(
                    assistant_message.content
                    or (
                        "Nu am putut identifica nicio acțiune pentru mesajul tău."
                        if response_language == "ro"
                        else "I could not identify an action for your message."
                    )
                ),
                actions=[],
                allowed=True,
            )

        reset_tool_calls = [
            tool_call
            for tool_call in tool_calls
            if tool_call.function.name == "reset_vehicle"
        ]

        if reset_tool_calls and len(tool_calls) != 1:
            raise ValueError(
                "Reset must be the only requested vehicle action"
            )

        actions: list[VehicleAction] = []
        replies: list[str] = []

        temperature_driver = current_temperature
        temperature_passenger = current_passenger_temperature
        seat_heating_driver = current_driver_seat_heating
        seat_heating_passenger = current_passenger_seat_heating
        volume = current_volume
        fan_speed = current_fan_speed
        explicit_zone = has_explicit_zone(message)
        state_topics = detect_state_topics(message)
        state_zones = detect_state_zones(message)
        speaker_target_zone = speaker if speaker in VEHICLE_ZONES else None
        temperature_zones_seen: set[str] = set()
        seat_heating_zones_seen: set[str] = set()
        temperature_zone_calls: list[str] = []
        seat_heating_zone_calls: list[str] = []
        for tool_call in tool_calls:
            tool_name = tool_call.function.name
            params = json.loads(tool_call.function.arguments)

            if not isinstance(params, dict):
                raise ValueError("Tool arguments must be a JSON object")

            if tool_name == "get_vehicle_state":
                replies.append(
                    create_state_response(
                        state_topics,
                        state_zones,
                        temperature_driver,
                        temperature_passenger,
                        seat_heating_driver,
                        seat_heating_passenger,
                        volume,
                        fan_speed,
                        current_song,
                        is_playing,
                        is_muted,
                        ambient_light,
                        ac_enabled,
                        response_language,
                    )
                )

            elif tool_name == "set_temperature":
                value = require_integer_parameter(params, "value")
                zone = require_string_parameter(params, "zone")

                if zone not in VEHICLE_ZONES:
                    raise ValueError("Temperature zone is not supported")

                if state_zones and zone not in state_zones:
                    continue
                if not explicit_zone and speaker_target_zone and zone != speaker_target_zone:
                    continue

                temperature_zones_seen.add(zone)
                temperature_zone_calls.append(zone)

                if zone == "passenger":
                    temperature_passenger = create_temperature_response(
                        replies,
                        actions,
                        temperature_passenger,
                        value,
                        "passenger",
                        response_language,
                    )

                else:
                    temperature_driver = create_temperature_response(
                        replies,
                        actions,
                        temperature_driver,
                        value,
                        "driver",
                        response_language,
                    )

            elif tool_name == "set_seat_heating":
                level = require_integer_parameter(params, "level")
                zone = require_string_parameter(params, "zone")

                if zone not in VEHICLE_ZONES:
                    raise ValueError("Seat heating zone is not supported")

                if state_zones and zone not in state_zones:
                    continue
                if not explicit_zone and speaker_target_zone and zone != speaker_target_zone:
                    continue

                seat_heating_zones_seen.add(zone)
                seat_heating_zone_calls.append(zone)

                if zone == "passenger":
                    seat_heating_passenger = create_seat_heating_response(
                        replies,
                        actions,
                        seat_heating_passenger,
                        level,
                        "passenger",
                        response_language,
                    )

                else:
                    seat_heating_driver = create_seat_heating_response(
                        replies,
                        actions,
                        seat_heating_driver,
                        level,
                        "driver",
                        response_language,
                    )

            elif tool_name == "set_volume":
                volume = create_volume_response(
                    replies,
                    actions,
                    volume,
                    require_integer_parameter(params, "value"),
                    response_language,
                )

            elif tool_name == "set_fan_speed":
                fan_speed = create_fan_response(
                    replies,
                    actions,
                    fan_speed,
                    require_integer_parameter(params, "level"),
                    response_language,
                )

            elif tool_name == "media_play":
                actions.append(
                    VehicleAction(type=ACTION_MEDIA_PLAY, params={})
                )
                append_localized(
                    replies,
                    response_language,
                    "Am pornit redarea muzicii.",
                    "I started music playback.",
                )

            elif tool_name == "media_pause":
                actions.append(
                    VehicleAction(type=ACTION_MEDIA_PAUSE, params={})
                )
                append_localized(
                    replies,
                    response_language,
                    "Am pus muzica pe pauză.",
                    "I paused the music.",
                )

            elif tool_name == "media_mute":
                actions.append(
                    VehicleAction(type=ACTION_MEDIA_MUTE, params={})
                )
                append_localized(
                    replies,
                    response_language,
                    "Am oprit sunetul.",
                    "I muted the sound.",
                )

            elif tool_name == "media_unmute":
                actions.append(
                    VehicleAction(type=ACTION_MEDIA_UNMUTE, params={})
                )
                append_localized(
                    replies,
                    response_language,
                    "Am repornit sunetul.",
                    "I unmuted the sound.",
                )

            elif tool_name == "media_next":
                actions.append(
                    VehicleAction(type=ACTION_MEDIA_NEXT, params={})
                )
                append_localized(
                    replies,
                    response_language,
                    "Am trecut la următoarea melodie.",
                    "I skipped to the next song.",
                )

            elif tool_name == "media_previous":
                actions.append(
                    VehicleAction(type=ACTION_MEDIA_PREVIOUS, params={})
                )
                append_localized(
                    replies,
                    response_language,
                    "Am revenit la melodia anterioară.",
                    "I went back to the previous song.",
                )

            elif tool_name == "set_ambient_light":
                requested_color = require_string_parameter(params, "color")
                color = AMBIENT_COLOR_ALIASES.get(
                    normalize_text(requested_color),
                    "",
                )

                if color not in AMBIENT_LIGHTS:
                    raise ValueError("Ambient light color is not supported")

                if color == ambient_light:
                    append_localized(
                        replies,
                        response_language,
                        f"Lumina ambientală este deja setată pe culoarea "
                        f"{AMBIENT_COLOR_LABELS_RO[color]}.",
                        f"The ambient light is already {color}.",
                    )
                else:
                    actions.append(
                        VehicleAction(
                            type=ACTION_SET_AMBIENT_LIGHT,
                            params={"color": color},
                        )
                    )
                    ambient_light = color
                    append_localized(
                        replies,
                        response_language,
                        f"Am setat lumina ambientală pe "
                        f"{AMBIENT_COLOR_LABELS_RO[color]}.",
                        f"I set the ambient light to {color}.",
                    )

            elif tool_name == "reset_vehicle":
                actions.append(
                    VehicleAction(
                        type=ACTION_RESET_VEHICLE,
                        params={},
                    )
                )
                append_localized(
                    replies,
                    response_language,
                    "Am resetat toate setările mașinii.",
                    "I reset all vehicle settings.",
                )

            else:
                raise ValueError(f"Unknown tool: {tool_name}")

        expected_zones = set(resolve_target_zones(message, speaker))

        if not explicit_zone and temperature_zones_seen:
            if (
                temperature_zones_seen != expected_zones
                or len(temperature_zone_calls) != len(expected_zones)
            ):
                raise ValueError(
                    "A temperature command without a zone must target the resolved speaker zone"
                )

        if not explicit_zone and seat_heating_zones_seen:
            if (
                seat_heating_zones_seen != expected_zones
                or len(seat_heating_zone_calls) != len(expected_zones)
            ):
                raise ValueError(
                    "A seat-heating command without a zone must target the resolved speaker zone"
                )

        return AIResponse(
            reply="\n".join(replies),
            actions=actions,
            allowed=True,
        )

    except Exception as error:
        logger.exception("AI request or tool processing failed: %s", error)

        return AIResponse(
            reply=(
                "Nu am putut procesa mesajul tău momentan."
                if response_language == "ro"
                else "I could not process your message right now."
            ),
            actions=[],
            allowed=False,
        )
