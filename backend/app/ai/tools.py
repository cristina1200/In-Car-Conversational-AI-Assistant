from typing import Any

from app.vehicle.constants import (
    AMBIENT_LIGHTS,
    MAX_FAN_SPEED,
    MAX_SEAT_HEATING,
    MAX_TEMPERATURE,
    MAX_VOLUME,
    MIN_FAN_SPEED,
    MIN_SEAT_HEATING,
    MIN_TEMPERATURE,
    MIN_VOLUME,
    VEHICLE_ZONES,
)


def function_tool(
    name: str,
    description: str,
    properties: dict[str, Any] | None = None,
    required: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": properties or {},
                "required": required or [],
                "additionalProperties": False,
            },
        },
    }


TOOLS = [
    function_tool(
        name="set_temperature",
        description=(
            "Set the requested final temperature for exactly one vehicle zone. "
            f"Allowed zones: {', '.join(VEHICLE_ZONES)}. "
            f"The vehicle range is {MIN_TEMPERATURE}-{MAX_TEMPERATURE} Celsius, "
            "but the requested value may be outside that range. "
            "For a command without a zone, call this tool once per zone. "
            "Always send the requested absolute value before clamping; never "
            "clamp it yourself."
        ),
        properties={
            "zone": {
                "type": "string",
                "enum": list(VEHICLE_ZONES),
            },
            "value": {
                "type": "integer",
                "description": (
                    "Requested absolute temperature in Celsius. It may be "
                    "below the minimum or above the maximum."
                ),
            },
        },
        required=["zone", "value"],
    ),
    function_tool(
        name="set_seat_heating",
        description=(
            "Set the requested final seat-heating level for exactly one vehicle zone. "
            f"Allowed zones: {', '.join(VEHICLE_ZONES)}. "
            f"The vehicle range is {MIN_SEAT_HEATING}-{MAX_SEAT_HEATING}, "
            "but the requested level may be outside that range. "
            "For a command without a zone, call this tool once per zone. "
            "Always send the requested level before clamping."
        ),
        properties={
            "zone": {
                "type": "string",
                "enum": list(VEHICLE_ZONES),
            },
            "level": {
                "type": "integer",
                "description": (
                    "Requested seat-heating level. It may be below the "
                    "minimum or above the maximum."
                ),
            },
        },
        required=["zone", "level"],
    ),
    function_tool(
        name="set_volume",
        description=(
            "Set the requested final global audio volume. "
            f"The vehicle range is {MIN_VOLUME}-{MAX_VOLUME} percent, but "
            "the requested value may be outside that range. "
            "Always send the requested absolute value before clamping."
        ),
        properties={
            "value": {
                "type": "integer",
                "description": (
                    "Requested absolute volume percentage. It may be below "
                    "the minimum or above the maximum."
                ),
            },
        },
        required=["value"],
    ),
    function_tool(
        name="set_fan_speed",
        description=(
            "Set the requested final global fan speed. "
            f"The vehicle range is {MIN_FAN_SPEED}-{MAX_FAN_SPEED}, but the "
            "requested level may be outside that range. "
            "Always send the requested level before clamping."
        ),
        properties={
            "level": {
                "type": "integer",
                "description": (
                    "Requested fan level. It may be below the minimum or "
                    "above the maximum."
                ),
            },
        },
        required=["level"],
    ),
    function_tool(
        name="media_play",
        description="Start or resume the current song without changing other settings.",
    ),
    function_tool(
        name="media_pause",
        description="Pause the current song without changing the current song or other settings.",
    ),
    function_tool(
        name="media_mute",
        description="Mute the audio without stopping playback or changing other settings.",
    ),
    function_tool(
        name="media_unmute",
        description="Unmute the audio without changing other settings.",
    ),
    function_tool(
        name="media_next",
        description="Skip to the next song without changing other vehicle settings.",
    ),
    function_tool(
        name="media_previous",
        description="Go back to the previous song without changing other vehicle settings.",
    ),
    function_tool(
        name="set_ambient_light",
        description=(
            "Set the global ambient light color. "
            f"Allowed values: {', '.join(AMBIENT_LIGHTS)}."
        ),
        properties={
            "color": {
                "type": "string",
                "enum": list(AMBIENT_LIGHTS),
            },
        },
        required=["color"],
    ),
    function_tool(
        name="get_vehicle_state",
        description=(
            "Return the current vehicle state only when the user explicitly "
            "asks about current settings or status."
        ),
    ),
    function_tool(
        name="reset_vehicle",
        description=(
            "Reset the entire vehicle to its default state. Use only when "
            "the user explicitly asks to reset everything."
        ),
    ),
]
