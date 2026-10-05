from typing import Literal

from pydantic import BaseModel, Field

from app.vehicle.constants import (
    DEFAULT_DRIVER_TEMPERATURE,
    DEFAULT_DRIVER_SEAT_HEATING,
    DEFAULT_AMBIENT_LIGHT,
    DEFAULT_PASSENGER_TEMPERATURE,
    DEFAULT_PASSENGER_SEAT_HEATING,
    DEFAULT_FAN_SPEED,
    DEFAULT_VOLUME,
    AMBIENT_LIGHTS,
    MAX_FAN_SPEED,
    MAX_SEAT_HEATING,
    MAX_TEMPERATURE,
    MAX_VOLUME,
    MIN_FAN_SPEED,
    MIN_SEAT_HEATING,
    MIN_TEMPERATURE,
    MIN_VOLUME,
)


AmbientLight = Literal[*AMBIENT_LIGHTS]


class ProfileCreate(BaseModel):
    user_id: str = Field(min_length=1)
    profile_name: str = Field(min_length=1)
    driver_temperature: int = Field(
        default=DEFAULT_DRIVER_TEMPERATURE,
        ge=MIN_TEMPERATURE,
        le=MAX_TEMPERATURE,
    )
    passenger_temperature: int = Field(
        default=DEFAULT_PASSENGER_TEMPERATURE,
        ge=MIN_TEMPERATURE,
        le=MAX_TEMPERATURE,
    )
    driver_seat_heating: int = Field(
        default=DEFAULT_DRIVER_SEAT_HEATING,
        ge=MIN_SEAT_HEATING,
        le=MAX_SEAT_HEATING,
    )
    passenger_seat_heating: int = Field(
        default=DEFAULT_PASSENGER_SEAT_HEATING,
        ge=MIN_SEAT_HEATING,
        le=MAX_SEAT_HEATING,
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
    ambient_light: AmbientLight = DEFAULT_AMBIENT_LIGHT
    is_default: bool = False


class ProfileUpdate(BaseModel):
    profile_name: str | None = Field(default=None, min_length=1)
    driver_temperature: int | None = Field(
        default=None,
        ge=MIN_TEMPERATURE,
        le=MAX_TEMPERATURE,
    )
    passenger_temperature: int | None = Field(
        default=None,
        ge=MIN_TEMPERATURE,
        le=MAX_TEMPERATURE,
    )
    driver_seat_heating: int | None = Field(
        default=None,
        ge=MIN_SEAT_HEATING,
        le=MAX_SEAT_HEATING,
    )
    passenger_seat_heating: int | None = Field(
        default=None,
        ge=MIN_SEAT_HEATING,
        le=MAX_SEAT_HEATING,
    )
    fan_speed: int | None = Field(
        default=None,
        ge=MIN_FAN_SPEED,
        le=MAX_FAN_SPEED,
    )
    volume: int | None = Field(
        default=None,
        ge=MIN_VOLUME,
        le=MAX_VOLUME,
    )
    ambient_light: AmbientLight | None = None
    is_default: bool | None = None


class ProfileResponse(BaseModel):
    profile_id: str
    user_id: str
    profile_name: str
    is_default: bool
    driver_temperature: int
    passenger_temperature: int
    driver_seat_heating: int
    passenger_seat_heating: int
    fan_speed: int
    volume: int
    ambient_light: str
    created_at: str
    updated_at: str
