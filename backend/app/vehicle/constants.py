from typing import Final


# TEMPERATURA
MIN_TEMPERATURE: Final = 16
MAX_TEMPERATURE: Final = 28
TEMPERATURE_COMFORT_STEP: Final = 2
TEMPERATURE_INTENSE_COMFORT_STEP: Final = 5

# VOLUM
MIN_VOLUME: Final = 0
MAX_VOLUME: Final = 100

MIN_FAN_SPEED: Final = 0
MAX_FAN_SPEED: Final = 3

MIN_SEAT_HEATING: Final = 0
MAX_SEAT_HEATING: Final = 3

DEFAULT_DRIVER_TEMPERATURE: Final = 20
DEFAULT_PASSENGER_TEMPERATURE: Final = 20
DEFAULT_DRIVER_SEAT_HEATING: Final = MIN_SEAT_HEATING
DEFAULT_PASSENGER_SEAT_HEATING: Final = MIN_SEAT_HEATING
DEFAULT_VOLUME: Final = 50
DEFAULT_FAN_SPEED: Final = 2
DEFAULT_AMBIENT_LIGHT: Final = "blue"
DEFAULT_CURRENT_SONG: Final = "Good Vibes"
DEFAULT_IS_PLAYING: Final = True
DEFAULT_IS_MUTED: Final = False
DEFAULT_AC_ENABLED: Final = True

VEHICLE_ZONES: Final = ("driver", "passenger")
AMBIENT_LIGHTS: Final = (
    "blue",
    "red",
    "green",
    "white",
    "purple",
    "yellow",
)

AMBIENT_COLOR_ALIASES: Final = {
    "blue": "blue",
    "albastru": "blue",
    "red": "red",
    "roșu": "red",
    "rosu": "red",
    "green": "green",
    "verde": "green",
    "white": "white",
    "alb": "white",
    "purple": "purple",
    "mov": "purple",
    "violet": "purple",
    "yellow": "yellow",
    "galben": "yellow",
}

AMBIENT_COLOR_LABELS_RO: Final = {
    "blue": "albastru",
    "red": "roșu",
    "green": "verde",
    "white": "alb",
    "purple": "mov",
    "yellow": "galben",
}

PLAYLIST: Final = (
    "Good Vibes",
    "Morning Drive",
    "Chill Mix",
    "Road Trip",
)

MAX_AUDIO_BYTES: Final = 10 * 1024 * 1024
MAX_CONVERSATION_MESSAGES: Final = 20

ACTION_SET_TEMPERATURE: Final = "SET_TEMPERATURE"
ACTION_SET_SEAT_HEATING: Final = "SET_SEAT_HEATING"
ACTION_SET_VOLUME: Final = "SET_VOLUME"
ACTION_SET_FAN_SPEED: Final = "SET_FAN_SPEED"
ACTION_MEDIA_PLAY: Final = "MEDIA_PLAY"
ACTION_MEDIA_PAUSE: Final = "MEDIA_PAUSE"
ACTION_MEDIA_MUTE: Final = "MEDIA_MUTE"
ACTION_MEDIA_UNMUTE: Final = "MEDIA_UNMUTE"
ACTION_MEDIA_NEXT: Final = "MEDIA_NEXT"
ACTION_MEDIA_PREVIOUS: Final = "MEDIA_PREVIOUS"
ACTION_SET_AMBIENT_LIGHT: Final = "SET_AMBIENT_LIGHT"
ACTION_RESET_VEHICLE: Final = "RESET_VEHICLE"
