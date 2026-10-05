import sqlite3
import uuid
from datetime import datetime, timezone

from app.repositories.profile_repository import ProfileRepository
from app.schemas.profile import ProfileCreate, ProfileResponse, ProfileUpdate
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
)


class ProfileUserNotFoundError(LookupError):
    pass


class ProfileNotFoundError(LookupError):
    pass


class ProfileOwnershipError(LookupError):
    pass


class ProfileService:
    def __init__(self, repository: ProfileRepository | None = None):
        self.repository = repository or ProfileRepository()

    def create_profile(self, profile: ProfileCreate) -> ProfileResponse:
        self._validate_user(profile.user_id)
        values = profile.model_dump()
        values["profile_name"] = values["profile_name"].strip()
        values["ambient_light"] = values["ambient_light"].strip().lower()
        self._synchronize_zone_preferences(values)
        self._validate_values(values)

        existing_profiles = self.repository.list_by_user_id(profile.user_id)
        if not existing_profiles:
            values["is_default"] = True

        now = datetime.now(timezone.utc).isoformat()

        try:
            row = self.repository.create_profile(
                profile_id=str(uuid.uuid4()),
                created_at=now,
                updated_at=now,
                replace_existing_defaults=values["is_default"],
                **values,
            )
        except sqlite3.IntegrityError as error:
            raise ValueError("Profile could not be created") from error

        return self._to_response(row)

    def list_profiles(self, user_id: str) -> list[ProfileResponse]:
        self._validate_user(user_id)
        return [
            self._to_response(row)
            for row in self.repository.list_by_user_id(user_id)
        ]

    def get_profile(
        self,
        *,
        profile_id: str,
        user_id: str,
    ) -> ProfileResponse:
        self._validate_user(user_id)
        row = self.repository.get_by_id(profile_id)

        if row is None or row["user_id"] != user_id:
            raise ProfileNotFoundError("Profile not found")

        return self._to_response(row)

    def update_profile(
        self,
        *,
        profile_id: str,
        user_id: str,
        profile: ProfileUpdate,
    ) -> ProfileResponse:
        self._validate_user(user_id)
        current = self.repository.get_by_id(profile_id)

        if current is None or current["user_id"] != user_id:
            raise ProfileNotFoundError("Profile not found")

        updates = profile.model_dump(exclude_unset=True)
        if "profile_name" in updates:
            updates["profile_name"] = updates["profile_name"].strip()
        if "ambient_light" in updates:
            updates["ambient_light"] = updates["ambient_light"].strip().lower()
        self._synchronize_zone_preferences(updates)

        merged_values = {
            column: current[column]
            for column in (
                "profile_name",
                "driver_temperature",
                "passenger_temperature",
                "driver_seat_heating",
                "passenger_seat_heating",
                "fan_speed",
                "volume",
                "ambient_light",
            )
        }
        merged_values.update(
            {
                key: value
                for key, value in updates.items()
                if key != "is_default"
            }
        )
        self._validate_values(merged_values)

        updated_at = datetime.now(timezone.utc).isoformat()
        row = self.repository.update_profile(
            profile_id=profile_id,
            user_id=user_id,
            updates=updates,
            updated_at=updated_at,
        )

        if row is None:
            raise ProfileNotFoundError("Profile not found")

        return self._to_response(row)

    def _validate_user(self, user_id: str) -> None:
        if not self.repository.user_exists(user_id):
            raise ProfileUserNotFoundError("User not found")

    @staticmethod
    def _validate_values(values: dict[str, object]) -> None:
        profile_name = values["profile_name"]
        if not isinstance(profile_name, str) or not profile_name:
            raise ValueError("Profile name is required")

        ranges = {
            "driver_temperature": (MIN_TEMPERATURE, MAX_TEMPERATURE),
            "passenger_temperature": (MIN_TEMPERATURE, MAX_TEMPERATURE),
            "driver_seat_heating": (MIN_SEAT_HEATING, MAX_SEAT_HEATING),
            "passenger_seat_heating": (MIN_SEAT_HEATING, MAX_SEAT_HEATING),
            "fan_speed": (MIN_FAN_SPEED, MAX_FAN_SPEED),
            "volume": (MIN_VOLUME, MAX_VOLUME),
        }
        for field, (minimum, maximum) in ranges.items():
            value = values[field]
            if not isinstance(value, int) or not minimum <= value <= maximum:
                raise ValueError(
                    f"{field} must be between {minimum} and {maximum}"
                )

        if values["ambient_light"] not in AMBIENT_LIGHTS:
            raise ValueError("Ambient light color is not supported")

    @staticmethod
    def _synchronize_zone_preferences(values: dict[str, object]) -> None:
        """Keep one user's comfort preferences identical in both zones."""
        if "driver_temperature" in values:
            values["passenger_temperature"] = values["driver_temperature"]
        elif "passenger_temperature" in values:
            values["driver_temperature"] = values["passenger_temperature"]

        if "driver_seat_heating" in values:
            values["passenger_seat_heating"] = values["driver_seat_heating"]
        elif "passenger_seat_heating" in values:
            values["driver_seat_heating"] = values["passenger_seat_heating"]

    @staticmethod
    def _to_response(row: sqlite3.Row) -> ProfileResponse:
        return ProfileResponse(
            profile_id=row["profile_id"],
            user_id=row["user_id"],
            profile_name=row["profile_name"],
            is_default=bool(row["is_default"]),
            driver_temperature=row["driver_temperature"],
            passenger_temperature=row["passenger_temperature"],
            driver_seat_heating=row["driver_seat_heating"],
            passenger_seat_heating=row["passenger_seat_heating"],
            fan_speed=row["fan_speed"],
            volume=row["volume"],
            ambient_light=row["ambient_light"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
