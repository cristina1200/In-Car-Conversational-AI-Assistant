from typing import Literal

from pydantic import BaseModel, Field

from app.vehicle.constants import (
    DEFAULT_AC_ENABLED,
    DEFAULT_AMBIENT_LIGHT,
    DEFAULT_CURRENT_SONG,
    DEFAULT_DRIVER_TEMPERATURE,
    DEFAULT_DRIVER_SEAT_HEATING,
    DEFAULT_FAN_SPEED,
    DEFAULT_IS_MUTED,
    DEFAULT_IS_PLAYING,
    DEFAULT_PASSENGER_TEMPERATURE,
    DEFAULT_PASSENGER_SEAT_HEATING,
    DEFAULT_VOLUME,
    MAX_FAN_SPEED,
    MAX_SEAT_HEATING,
    MAX_TEMPERATURE,
    MAX_VOLUME,
    MIN_FAN_SPEED,
    MIN_SEAT_HEATING,
    MIN_TEMPERATURE,
    MIN_VOLUME,
    AMBIENT_LIGHTS,
)


AmbientLightColor = Literal[*AMBIENT_LIGHTS]


class TemperatureState(BaseModel):
    driver: int = Field(
        default=DEFAULT_DRIVER_TEMPERATURE,
        ge=MIN_TEMPERATURE,
        le=MAX_TEMPERATURE,
    )
    passenger: int = Field(
        default=DEFAULT_PASSENGER_TEMPERATURE,
        ge=MIN_TEMPERATURE,
        le=MAX_TEMPERATURE,
    )


class SeatHeatingState(BaseModel):
    driver: int = Field(
        default=DEFAULT_DRIVER_SEAT_HEATING,
        ge=MIN_SEAT_HEATING,
        le=MAX_SEAT_HEATING,
    )
    passenger: int = Field(
        default=DEFAULT_PASSENGER_SEAT_HEATING,
        ge=MIN_SEAT_HEATING,
        le=MAX_SEAT_HEATING,
    )


class VehicleState(BaseModel):
    temperature: TemperatureState = Field(
        default_factory=TemperatureState
    )

    seat_heating: SeatHeatingState = Field(
        default_factory=SeatHeatingState
    )

    fan_speed: int = Field(
        default=DEFAULT_FAN_SPEED,
        ge=MIN_FAN_SPEED,
        le=MAX_FAN_SPEED,
    )
    volume: int = Field(
        default=DEFAULT_VOLUME,
        ge=MIN_VOLUME,
        le=MAX_VOLUME,
    )

    current_song: str = DEFAULT_CURRENT_SONG
    is_playing: bool = DEFAULT_IS_PLAYING
    is_muted: bool = DEFAULT_IS_MUTED

    ambient_light: AmbientLightColor = DEFAULT_AMBIENT_LIGHT
    ac_enabled: bool = DEFAULT_AC_ENABLED
