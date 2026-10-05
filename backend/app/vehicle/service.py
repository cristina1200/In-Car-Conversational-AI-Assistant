from app.schemas.ai_response import VehicleAction
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
    AMBIENT_LIGHTS,
    MAX_FAN_SPEED,
    MAX_SEAT_HEATING,
    MAX_TEMPERATURE,
    MAX_VOLUME,
    MIN_FAN_SPEED,
    MIN_SEAT_HEATING,
    MIN_TEMPERATURE,
    MIN_VOLUME,
    PLAYLIST,
    VEHICLE_ZONES,
)
from app.vehicle.state import VehicleState


class VehicleService:
    PLAYLIST = PLAYLIST
    ALLOWED_AMBIENT_LIGHTS = frozenset(AMBIENT_LIGHTS)

    def __init__(self):
        self.state = VehicleState()

    def get_state(self) -> VehicleState:
        return self.state

    def reset(self) -> VehicleState:
        self.state = VehicleState()
        return self.state

    @staticmethod
    def _validate_range(
        value: int,
        minimum: int,
        maximum: int,
        label: str,
    ) -> None:
        if value < minimum or value > maximum:
            raise ValueError(
                f"{label} must be between {minimum} and {maximum}"
            )

    def set_volume(self, value: int) -> VehicleState:
        self._validate_range(
            value,
            MIN_VOLUME,
            MAX_VOLUME,
            "Volume",
        )

        self.state.volume = value
        return self.state

    def set_temperature(self, zone: str, value: int) -> VehicleState:
        if zone not in VEHICLE_ZONES:
            raise ValueError("Zone must be driver or passenger")

        self._validate_range(
            value,
            MIN_TEMPERATURE,
            MAX_TEMPERATURE,
            "Temperature",
        )

        if zone == "driver":
            self.state.temperature.driver = value
        else:
            self.state.temperature.passenger = value

        return self.state

    def set_seat_heating(self, zone: str, level: int) -> VehicleState:
        if zone not in VEHICLE_ZONES:
            raise ValueError(
                "Seat heating zone must be driver or passenger"
            )

        self._validate_range(
            level,
            MIN_SEAT_HEATING,
            MAX_SEAT_HEATING,
            "Seat heating level",
        )

        if zone == "driver":
            self.state.seat_heating.driver = level
        else:
            self.state.seat_heating.passenger = level

        return self.state

    def set_fan_speed(self, level: int) -> VehicleState:
        self._validate_range(
            level,
            MIN_FAN_SPEED,
            MAX_FAN_SPEED,
            "Fan speed",
        )

        self.state.fan_speed = level
        return self.state

    def play_music(self) -> VehicleState:
        self.state.is_playing = True
        return self.state

    def pause_music(self) -> VehicleState:
        self.state.is_playing = False
        return self.state

    def mute_music(self) -> VehicleState:
        self.state.is_muted = True
        return self.state

    def unmute_music(self) -> VehicleState:
        self.state.is_muted = False
        return self.state

    def next_track(self) -> VehicleState:
        current_index = self.PLAYLIST.index(self.state.current_song)
        next_index = (current_index + 1) % len(self.PLAYLIST)

        self.state.current_song = self.PLAYLIST[next_index]
        self.state.is_playing = True

        return self.state

    def previous_track(self) -> VehicleState:
        current_index = self.PLAYLIST.index(self.state.current_song)
        previous_index = (current_index - 1) % len(self.PLAYLIST)

        self.state.current_song = self.PLAYLIST[previous_index]
        self.state.is_playing = True

        return self.state

    def set_ambient_light(self, color: str) -> VehicleState:
        normalized_color = AMBIENT_COLOR_ALIASES.get(color.strip().lower())

        if normalized_color not in self.ALLOWED_AMBIENT_LIGHTS:
            raise ValueError(
                "Ambient light color is not supported"
            )

        self.state.ambient_light = normalized_color
        return self.state

    def execute_action(self, action: VehicleAction) -> VehicleState:
        if action.type == ACTION_SET_VOLUME:
            value = action.params.get("value")

            if not isinstance(value, int):
                raise ValueError("Volume value must be an integer")

            return self.set_volume(value)

        if action.type == ACTION_SET_TEMPERATURE:
            zone = action.params.get("zone")
            value = action.params.get("value")

            if not isinstance(zone, str):
                raise ValueError(
                    "Temperature zone must be a string"
                )

            if not isinstance(value, int):
                raise ValueError(
                    "Temperature value must be an integer"
                )

            return self.set_temperature(zone, value)

        if action.type == ACTION_SET_SEAT_HEATING:
            zone = action.params.get("zone")
            level = action.params.get("level")

            if not isinstance(zone, str):
                raise ValueError(
                    "Seat heating zone must be a string"
                )

            if not isinstance(level, int):
                raise ValueError(
                    "Seat heating level must be an integer"
                )

            return self.set_seat_heating(zone, level)

        if action.type == ACTION_SET_FAN_SPEED:
            level = action.params.get("level")

            if not isinstance(level, int):
                raise ValueError(
                    "Fan speed level must be an integer"
                )

            return self.set_fan_speed(level)

        if action.type == ACTION_MEDIA_PLAY:
            return self.play_music()

        if action.type == ACTION_MEDIA_PAUSE:
            return self.pause_music()

        if action.type == ACTION_MEDIA_MUTE:
            return self.mute_music()

        if action.type == ACTION_MEDIA_UNMUTE:
            return self.unmute_music()

        if action.type == ACTION_MEDIA_NEXT:
            return self.next_track()

        if action.type == ACTION_MEDIA_PREVIOUS:
            return self.previous_track()

        if action.type == ACTION_SET_AMBIENT_LIGHT:
            color = action.params.get("color")

            if not isinstance(color, str):
                raise ValueError(
                    "Ambient light color must be a string"
                )

            return self.set_ambient_light(color)

        if action.type == ACTION_RESET_VEHICLE:
            return self.reset()

        raise ValueError(f"Unsupported action: {action.type}")

    def execute_actions(
        self,
        actions: list[VehicleAction],
    ) -> VehicleState:
        for action in actions:
            self.execute_action(action)

        return self.state
