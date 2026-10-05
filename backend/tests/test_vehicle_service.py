import pytest

from app.schemas.ai_response import VehicleAction
from app.vehicle.service import VehicleService


def test_initial_vehicle_state():
    service = VehicleService()

    state = service.get_state()

    assert state.volume == 50
    assert state.temperature.driver == 20
    assert state.temperature.passenger == 20
    assert state.seat_heating.driver == 0
    assert state.seat_heating.passenger == 0


def test_set_volume():
    service = VehicleService()

    state = service.set_volume(60)

    assert state.volume == 60


def test_set_driver_temperature():
    service = VehicleService()

    state = service.set_temperature("driver", 24)

    assert state.temperature.driver == 24


def test_set_passenger_temperature():
    service = VehicleService()

    state = service.set_temperature("passenger", 25)

    assert state.temperature.passenger == 25


def test_reset_vehicle_state():
    service = VehicleService()

    service.set_volume(80)
    service.set_temperature("driver", 25)
    service.set_seat_heating("passenger", 3)

    state = service.reset()

    assert state.volume == 50
    assert state.temperature.driver == 20
    assert state.temperature.passenger == 20
    assert state.seat_heating.driver == 0
    assert state.seat_heating.passenger == 0


def test_invalid_volume():
    service = VehicleService()

    with pytest.raises(
        ValueError,
        match="Volume must be between 0 and 100",
    ):
        service.set_volume(150)


def test_invalid_temperature():
    service = VehicleService()

    with pytest.raises(
        ValueError,
        match="Temperature must be between 16 and 28",
    ):
        service.set_temperature("driver", 40)


def test_invalid_temperature_zone():
    service = VehicleService()

    with pytest.raises(
        ValueError,
        match="Zone must be driver or passenger",
    ):
        service.set_temperature("rear", 22)


def test_execute_set_volume_action():
    service = VehicleService()

    action = VehicleAction(
        type="SET_VOLUME",
        params={"value": 60},
    )

    state = service.execute_action(action)

    assert state.volume == 60


def test_execute_set_temperature_action():
    service = VehicleService()

    action = VehicleAction(
        type="SET_TEMPERATURE",
        params={
            "zone": "driver",
            "value": 24,
        },
    )

    state = service.execute_action(action)

    assert state.temperature.driver == 24


def test_execute_unsupported_action():
    service = VehicleService()

    action = VehicleAction(
        type="ACCELERATE",
        params={"value": 120},
    )

    with pytest.raises(
        ValueError,
        match="Unsupported action",
    ):
        service.execute_action(action)


def test_execute_action_with_invalid_volume():
    service = VehicleService()

    action = VehicleAction(
        type="SET_VOLUME",
        params={"value": 150},
    )

    with pytest.raises(
        ValueError,
        match="Volume must be between 0 and 100",
    ):
        service.execute_action(action)


def test_execute_multiple_actions():
    service = VehicleService()

    actions = [
        VehicleAction(
            type="SET_TEMPERATURE",
            params={
                "zone": "driver",
                "value": 24,
            },
        ),
        VehicleAction(
            type="SET_VOLUME",
            params={
                "value": 20,
            },
        ),
    ]

    state = service.execute_actions(actions)

    assert state.temperature.driver == 24
    assert state.volume == 20


def test_set_driver_seat_heating():
    service = VehicleService()

    state = service.set_seat_heating("driver", 2)

    assert state.seat_heating.driver == 2
    assert state.seat_heating.passenger == 0


def test_set_passenger_seat_heating():
    service = VehicleService()

    state = service.set_seat_heating("passenger", 3)

    assert state.seat_heating.passenger == 3
    assert state.seat_heating.driver == 0


def test_turn_off_driver_seat_heating():
    service = VehicleService()

    service.set_seat_heating("driver", 3)
    state = service.set_seat_heating("driver", 0)

    assert state.seat_heating.driver == 0


def test_invalid_seat_heating_level():
    service = VehicleService()

    with pytest.raises(
        ValueError,
        match="Seat heating level must be between 0 and 3",
    ):
        service.set_seat_heating("driver", 4)


def test_invalid_seat_heating_zone():
    service = VehicleService()

    with pytest.raises(
        ValueError,
        match="Seat heating zone must be driver or passenger",
    ):
        service.set_seat_heating("rear", 2)


def test_execute_seat_heating_action():
    service = VehicleService()

    action = VehicleAction(
        type="SET_SEAT_HEATING",
        params={
            "zone": "passenger",
            "level": 2,
        },
    )

    state = service.execute_action(action)

    assert state.seat_heating.passenger == 2


def test_execute_seat_heating_action_with_invalid_level():
    service = VehicleService()

    action = VehicleAction(
        type="SET_SEAT_HEATING",
        params={
            "zone": "driver",
            "level": 5,
        },
    )

    with pytest.raises(
        ValueError,
        match="Seat heating level must be between 0 and 3",
    ):
        service.execute_action(action)

def test_pause_music():
    service = VehicleService()

    state = service.pause_music()

    assert state.is_playing is False
    assert state.current_song == "Good Vibes"


def test_play_music_after_pause():
    service = VehicleService()

    service.pause_music()
    state = service.play_music()

    assert state.is_playing is True


def test_mute_music_without_pausing():
    service = VehicleService()

    state = service.mute_music()

    assert state.is_muted is True
    assert state.is_playing is True


def test_unmute_music():
    service = VehicleService()

    service.mute_music()
    state = service.unmute_music()

    assert state.is_muted is False


def test_next_track():
    service = VehicleService()

    state = service.next_track()

    assert state.current_song == "Morning Drive"
    assert state.is_playing is True


def test_next_track_wraps_playlist():
    service = VehicleService()

    for _ in range(4):
        service.next_track()

    state = service.get_state()

    assert state.current_song == "Good Vibes"


def test_previous_track():
    service = VehicleService()

    state = service.previous_track()

    assert state.current_song == "Road Trip"
    assert state.is_playing is True


def test_previous_track_wraps_playlist():
    service = VehicleService()

    for _ in range(4):
        service.previous_track()

    state = service.get_state()

    assert state.current_song == "Good Vibes"


def test_execute_pause_music_action():
    service = VehicleService()

    action = VehicleAction(type="MEDIA_PAUSE")

    state = service.execute_action(action)

    assert state.is_playing is False


def test_execute_mute_music_action():
    service = VehicleService()

    action = VehicleAction(type="MEDIA_MUTE")

    state = service.execute_action(action)

    assert state.is_muted is True


def test_execute_unmute_music_action():
    service = VehicleService()

    service.mute_music()

    action = VehicleAction(type="MEDIA_UNMUTE")

    state = service.execute_action(action)

    assert state.is_muted is False


def test_execute_next_track_action():
    service = VehicleService()

    action = VehicleAction(type="MEDIA_NEXT")

    state = service.execute_action(action)

    assert state.current_song == "Morning Drive"


def test_execute_previous_track_action():
    service = VehicleService()

    action = VehicleAction(type="MEDIA_PREVIOUS")

    state = service.execute_action(action)

    assert state.current_song == "Road Trip"

def test_set_ambient_light():
    service = VehicleService()

    state = service.set_ambient_light("purple")

    assert state.ambient_light == "purple"


def test_ambient_light_is_global():
    service = VehicleService()

    state = service.set_ambient_light("red")

    assert state.ambient_light == "red"


def test_invalid_ambient_light():
    service = VehicleService()

    with pytest.raises(
        ValueError,
        match="Ambient light color is not supported",
    ):
        service.set_ambient_light("orange")


def test_execute_ambient_light_action():
    service = VehicleService()

    action = VehicleAction(
        type="SET_AMBIENT_LIGHT",
        params={
            "color": "green",
        },
    )

    state = service.execute_action(action)

    assert state.ambient_light == "green"


def test_execute_ambient_light_action_with_invalid_color():
    service = VehicleService()

    action = VehicleAction(
        type="SET_AMBIENT_LIGHT",
        params={
            "color": "orange",
        },
    )

    with pytest.raises(
        ValueError,
        match="Ambient light color is not supported",
    ):
        service.execute_action(action)

def test_reset_restores_all_vehicle_features():
    service = VehicleService()

    service.set_volume(80)
    service.set_temperature("driver", 25)
    service.set_temperature("passenger", 26)
    service.set_seat_heating("driver", 3)
    service.set_seat_heating("passenger", 2)
    service.pause_music()
    service.mute_music()
    service.next_track()
    service.set_ambient_light("purple")

    state = service.reset()

    assert state.volume == 50
    assert state.temperature.driver == 20
    assert state.temperature.passenger == 20
    assert state.seat_heating.driver == 0
    assert state.seat_heating.passenger == 0
    assert state.is_playing is True
    assert state.is_muted is False
    assert state.current_song == "Good Vibes"
    assert state.ambient_light == "blue"


def test_execute_multiple_vehicle_actions():
    service = VehicleService()

    actions = [
        VehicleAction(
            type="SET_TEMPERATURE",
            params={
                "zone": "passenger",
                "value": 24,
            },
        ),
        VehicleAction(
            type="SET_SEAT_HEATING",
            params={
                "zone": "driver",
                "level": 2,
            },
        ),
        VehicleAction(
            type="SET_VOLUME",
            params={
                "value": 70,
            },
        ),
        VehicleAction(
            type="MEDIA_PAUSE",
        ),
        VehicleAction(
            type="MEDIA_MUTE",
        ),
        VehicleAction(
            type="SET_AMBIENT_LIGHT",
            params={
                "color": "purple",
            },
        ),
    ]

    state = service.execute_actions(actions)

    assert state.temperature.passenger == 24
    assert state.seat_heating.driver == 2
    assert state.volume == 70
    assert state.is_playing is False
    assert state.is_muted is True
    assert state.ambient_light == "purple"

def test_initial_fan_speed():
    service = VehicleService()

    state = service.get_state()

    assert state.fan_speed == 2


def test_set_fan_speed():
    service = VehicleService()

    state = service.set_fan_speed(3)

    assert state.fan_speed == 3


def test_turn_off_fan():
    service = VehicleService()

    service.set_fan_speed(3)
    state = service.set_fan_speed(0)

    assert state.fan_speed == 0


def test_invalid_fan_speed():
    service = VehicleService()

    with pytest.raises(
        ValueError,
        match="Fan speed must be between 0 and 3",
    ):
        service.set_fan_speed(4)


def test_execute_fan_speed_action():
    service = VehicleService()

    action = VehicleAction(
        type="SET_FAN_SPEED",
        params={
            "level": 3,
        },
    )

    state = service.execute_action(action)

    assert state.fan_speed == 3


def test_execute_fan_speed_action_with_invalid_level():
    service = VehicleService()

    action = VehicleAction(
        type="SET_FAN_SPEED",
        params={
            "level": 5,
        },
    )

    with pytest.raises(
        ValueError,
        match="Fan speed must be between 0 and 3",
    ):
        service.execute_action(action)
