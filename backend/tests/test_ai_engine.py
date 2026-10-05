import json
import os
import struct
import uuid
import wave
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

import app.db.connection as db_connection
from app.ai.engine import process_message
from app.db.init_db import init_db
from app.main import app
from app.schemas.ai_response import VehicleAction
from app.vehicle.constants import (
    ACTION_MEDIA_PREVIOUS,
    ACTION_RESET_VEHICLE,
    MAX_FAN_SPEED,
    MAX_SEAT_HEATING,
    MAX_TEMPERATURE,
    MAX_VOLUME,
    MIN_TEMPERATURE,
    TEMPERATURE_COMFORT_STEP,
    TEMPERATURE_INTENSE_COMFORT_STEP,
)
from app.vehicle.service import VehicleService
from app.vehicle.state import VehicleState


TEST_ENVIRONMENT = {
    "OPENAI_MODEL": "test-model",
    "OPENAI_TEMPERATURE": "0",
}


@pytest.fixture(autouse=True)
def isolated_sqlite_db(tmp_path, monkeypatch):
    db_path = tmp_path / "app.sqlite3"
    monkeypatch.setattr(db_connection, "DATABASE_PATH", db_path)
    init_db()
    yield
    if db_path.exists():
        db_path.unlink()


def make_tool_call(name: str, arguments: dict) -> SimpleNamespace:
    return SimpleNamespace(
        function=SimpleNamespace(
            name=name,
            arguments=json.dumps(arguments),
        )
    )


def make_client(*tool_calls: SimpleNamespace, content: str | None = None) -> Mock:
    client = Mock()
    client.chat.completions.create.return_value = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content=content,
                    tool_calls=list(tool_calls),
                )
            )
        ]
    )
    return client


def test_no_tool_response_is_allowed_and_has_no_actions():
    client = make_client(content="Salut!")

    with patch.dict(os.environ, TEST_ENVIRONMENT), patch(
        "app.ai.engine.get_client",
        return_value=client,
    ):
        result = process_message("Salut!")

    assert result.allowed is True
    assert result.reply == "Salut!"
    assert result.actions == []


def test_conversation_history_is_forwarded_to_openai():
    client = make_client(content="Am înțeles.")

    with patch.dict(os.environ, TEST_ENVIRONMENT), patch(
        "app.ai.engine.get_client",
        return_value=client,
    ):
        result = process_message(
            "Ce temperatură am setat prima dată?",
            conversation_history=[
                {
                    "role": "user",
                    "content": "Setează temperatura la 20 de grade",
                },
                {
                    "role": "assistant",
                    "content": "Am setat temperatura la 20°C.",
                },
            ],
        )

    request_messages = (
        client.chat.completions.create.call_args.kwargs["messages"]
    )
    assert result.reply == "Am înțeles."
    assert request_messages[1] == {
        "role": "user",
        "content": "Setează temperatura la 20 de grade",
    }
    assert request_messages[2] == {
        "role": "assistant",
        "content": "Am setat temperatura la 20°C.",
    }


def test_memory_restores_all_vehicle_settings_without_openai_guessing():
    client = make_client()
    action_history = [
        VehicleAction(
            type="SET_TEMPERATURE",
            params={"zone": "driver", "value": 24},
        ),
        VehicleAction(
            type="SET_TEMPERATURE",
            params={"zone": "passenger", "value": 24},
        ),
        VehicleAction(type="SET_VOLUME", params={"value": 100}),
        VehicleAction(type="SET_VOLUME", params={"value": 40}),
        VehicleAction(
            type="SET_SEAT_HEATING",
            params={"zone": "driver", "level": 2},
        ),
        VehicleAction(
            type="SET_SEAT_HEATING",
            params={"zone": "passenger", "level": 2},
        ),
        VehicleAction(
            type="SET_SEAT_HEATING",
            params={"zone": "driver", "level": 1},
        ),
        VehicleAction(
            type="SET_SEAT_HEATING",
            params={"zone": "passenger", "level": 1},
        ),
        VehicleAction(type="SET_FAN_SPEED", params={"level": 3}),
        VehicleAction(type="SET_FAN_SPEED", params={"level": 1}),
        VehicleAction(
            type="SET_AMBIENT_LIGHT",
            params={"color": "red"},
        ),
        VehicleAction(
            type="SET_AMBIENT_LIGHT",
            params={"color": "green"},
        ),
    ]
    cases = [
        (
            "Dai temperatura la cat era la inceput",
            {
                "current_temperature": 20,
                "current_passenger_temperature": 20,
            },
            [24, 24],
        ),
        (
            "Dai volumul la cat era la inceput",
            {"current_volume": 40},
            [100],
        ),
        (
            "Dai incalzirea la cat era la inceput",
            {
                "current_driver_seat_heating": 1,
                "current_passenger_seat_heating": 1,
            },
            [2, 2],
        ),
        (
            "Dai ventilatorul la cat era la inceput",
            {"current_fan_speed": 1},
            [3],
        ),
    ]

    for message, state, expected_values in cases:
        with patch.dict(os.environ, TEST_ENVIRONMENT), patch(
            "app.ai.engine.get_client",
            return_value=client,
        ):
            result = process_message(
                message,
                action_history=action_history,
                **state,
            )

        assert result.allowed is True
        assert [
            action.params.get("value", action.params.get("level"))
            for action in result.actions
        ] == expected_values
        client.chat.completions.create.assert_not_called()

    with patch.dict(os.environ, TEST_ENVIRONMENT), patch(
        "app.ai.engine.get_client",
        return_value=client,
    ):
        result = process_message(
            "Dai lumina ambientala la cat era la inceput",
            ambient_light="green",
            action_history=action_history,
        )

    assert result.actions[0].params["color"] == "red"
    client.chat.completions.create.assert_not_called()


def test_memory_without_previous_value_returns_statement_without_question():
    client = make_client()

    with patch.dict(os.environ, TEST_ENVIRONMENT), patch(
        "app.ai.engine.get_client",
        return_value=client,
    ):
        result = process_message(
            "Dai volumul la cat era la inceput",
            action_history=[],
        )

    assert result.allowed is False
    assert result.actions == []
    assert "?" not in result.reply
    client.chat.completions.create.assert_not_called()


def test_repeating_current_ambient_color_returns_already_message():
    client = make_client()

    with patch.dict(os.environ, TEST_ENVIRONMENT), patch(
        "app.ai.engine.get_client",
        return_value=client,
    ):
        result = process_message(
            "Setează lumina ambientală pe mov",
            ambient_light="purple",
        )

    assert result.allowed is True
    assert result.actions == []
    assert result.reply == (
        "Lumina ambientală este deja setată pe culoarea mov."
    )
    client.chat.completions.create.assert_not_called()


def test_below_minimum_fan_speed_reports_that_it_was_stopped():
    client = make_client()

    with patch.dict(os.environ, TEST_ENVIRONMENT), patch(
        "app.ai.engine.get_client",
        return_value=client,
    ):
        result = process_message(
            "Setează ventilatorul la -1",
            current_fan_speed=2,
        )

    assert result.reply == (
        "Nivelul minim al ventilatorului este 0.\n\n"
        "Am oprit ventilatorul."
    )


def test_below_minimum_seat_heating_stops_both_seats_with_one_message():
    client = make_client()

    with patch.dict(os.environ, TEST_ENVIRONMENT), patch(
        "app.ai.engine.get_client",
        return_value=client,
    ):
        result = process_message(
            "Pune încălzirea în scaune la -1",
            current_driver_seat_heating=1,
            current_passenger_seat_heating=3,
        )

    assert result.reply == (
        "Nivelul minim pentru încălzirea scaunelor este 0.\n\n"
        "Am oprit încălzirea în scaune."
    )


def test_signed_temperature_increase_uses_fixed_limit_response():
    client = make_client()

    with patch.dict(os.environ, TEST_ENVIRONMENT), patch(
        "app.ai.engine.get_client",
        return_value=client,
    ):
        result = process_message(
            "Temperatura +10",
            current_temperature=20,
            current_passenger_temperature=21,
        )

    assert result.reply == (
        "Temperatura maximă este 28°C.\n\n"
        "Am setat temperatura șoferului de la 20°C la 28°C.\n"
        "Am setat temperatura pasagerului de la 21°C la 28°C."
    )
    client.chat.completions.create.assert_not_called()


def test_signed_volume_decrease_uses_fixed_minimum_response():
    client = make_client()

    with patch.dict(os.environ, TEST_ENVIRONMENT), patch(
        "app.ai.engine.get_client",
        return_value=client,
    ):
        result = process_message(
            "Volum -100",
            current_volume=50,
        )

    assert result.reply == (
        "Volumul minim este 0%.\n\n"
        "Am setat volumul de la 50% la 0%."
    )
    client.chat.completions.create.assert_not_called()


def test_seat_heating_phrase_without_command_uses_fixed_maximum_response():
    client = make_client()

    with patch.dict(os.environ, TEST_ENVIRONMENT), patch(
        "app.ai.engine.get_client",
        return_value=client,
    ):
        result = process_message(
            "Încălzirea în scaune la treapta 5",
            current_driver_seat_heating=0,
            current_passenger_seat_heating=1,
        )

    assert result.reply == (
        "Nivelul maxim pentru încălzirea scaunelor este 3.\n\n"
        "Am setat încălzirea scaunului șoferului de la nivelul 0 la nivelul 3.\n"
        "Am setat încălzirea scaunului pasagerului de la nivelul 1 la nivelul 3."
    )
    client.chat.completions.create.assert_not_called()


def test_volume_phrase_without_command_uses_fixed_maximum_response():
    client = make_client()

    with patch.dict(os.environ, TEST_ENVIRONMENT), patch(
        "app.ai.engine.get_client",
        return_value=client,
    ):
        result = process_message(
            "Volumul la 2000",
            current_volume=50,
        )

    assert result.reply == (
        "Volumul maxim este 100%.\n\n"
        "Am setat volumul de la 50% la 100%."
    )
    client.chat.completions.create.assert_not_called()


def test_explicit_value_is_recorded_even_when_already_current():
    client = make_client()

    with patch.dict(os.environ, TEST_ENVIRONMENT), patch(
        "app.ai.engine.get_client",
        return_value=client,
    ):
        result = process_message(
            "Setează temperatura șoferului la 20 grade",
            current_temperature=20,
        )

    assert result.allowed is True
    assert result.actions == [
        VehicleAction(
            type="SET_TEMPERATURE",
            params={"zone": "driver", "value": 20},
        )
    ]
    client.chat.completions.create.assert_not_called()


def test_explicit_temperature_above_limit_is_applied_without_confirmation():
    client = make_client()

    with patch.dict(os.environ, TEST_ENVIRONMENT), patch(
        "app.ai.engine.get_client",
        return_value=client,
    ):
        result = process_message(
            "Pune temperatura la 31 de grade",
            current_temperature=20,
            current_passenger_temperature=21,
        )

    assert result.allowed is True
    assert [action.params["value"] for action in result.actions] == [28, 28]
    assert result.reply == (
        "Temperatura maximă este 28°C.\n\n"
        "Am setat temperatura șoferului de la 20°C la 28°C.\n"
        "Am setat temperatura pasagerului de la 21°C la 28°C."
    )
    assert "Vrei" not in result.reply
    client.chat.completions.create.assert_not_called()


def test_explicit_passenger_temperature_below_limit_is_applied_without_confirmation():
    client = make_client()

    with patch.dict(os.environ, TEST_ENVIRONMENT), patch(
        "app.ai.engine.get_client",
        return_value=client,
    ):
        result = process_message(
            "Dai temperatura la pasager 15",
            current_temperature=20,
            current_passenger_temperature=21,
        )

    assert result.allowed is True
    assert len(result.actions) == 1
    assert result.actions[0].params == {"zone": "passenger", "value": 16}
    assert "Temperatura minimă este 16°C." in result.reply
    assert "Am setat temperatura pasagerului de la 21°C la 16°C." in result.reply
    assert "Vrei" not in result.reply
    client.chat.completions.create.assert_not_called()


def test_explicit_volume_above_limit_is_applied_without_confirmation():
    client = make_client()

    with patch.dict(os.environ, TEST_ENVIRONMENT), patch(
        "app.ai.engine.get_client",
        return_value=client,
    ):
        result = process_message("Pune volumul la 200", current_volume=50)

    assert result.allowed is True
    assert result.actions[0].params["value"] == 100
    assert "Vrei" not in result.reply
    client.chat.completions.create.assert_not_called()


def test_explicit_fan_values_without_command_verb_are_processed_in_romanian():
    cases = [
        ("Ventilatorul la -1", 2, 0, "Nivelul minim al ventilatorului este 0."),
        ("Nivelul ventilatorului la -1", 2, 0, "Nivelul minim al ventilatorului este 0."),
        ("Viteza ventilatorului la 5", 2, MAX_FAN_SPEED, f"Nivelul maxim al ventilatorului este {MAX_FAN_SPEED}."),
        (
            "Ventilator la 5",
            2,
            MAX_FAN_SPEED,
            f"Nivelul maxim al ventilatorului este {MAX_FAN_SPEED}.",
        ),
    ]

    for message, current_speed, expected_speed, limit_message in cases:
        client = make_client()

        with patch.dict(os.environ, TEST_ENVIRONMENT), patch(
            "app.ai.engine.get_client",
            return_value=client,
        ):
            result = process_message(message, current_fan_speed=current_speed)

        assert result.allowed is True
        assert result.actions[0].params == {"level": expected_speed}
        assert limit_message in result.reply
        if expected_speed == 0:
            assert "Am oprit ventilatorul." in result.reply
        else:
            assert (
                f"Am setat ventilatorul de la nivelul 2 la nivelul "
                f"{MAX_FAN_SPEED}." in result.reply
            )
        client.chat.completions.create.assert_not_called()


def test_short_numeric_forms_are_processed_for_all_comfort_features():
    cases = [
        (
            "Temperatura la 31",
            {"current_temperature": 20, "current_passenger_temperature": 21},
            [{"zone": "driver", "value": MAX_TEMPERATURE}, {"zone": "passenger", "value": MAX_TEMPERATURE}],
            f"Temperatura maximă este {MAX_TEMPERATURE}°C.",
        ),
        (
            "Volum la 2000",
            {"current_volume": 50},
            [{"value": MAX_VOLUME}],
            f"Volumul maxim este {MAX_VOLUME}%.",
        ),
        (
            "Încălzirea scaunelor la 10",
            {"current_driver_seat_heating": 1, "current_passenger_seat_heating": 2},
            [{"zone": "driver", "level": MAX_SEAT_HEATING}, {"zone": "passenger", "level": MAX_SEAT_HEATING}],
            f"Nivelul maxim pentru încălzirea scaunelor este {MAX_SEAT_HEATING}.",
        ),
    ]

    for message, state, expected_actions, limit_message in cases:
        client = make_client()

        with patch.dict(os.environ, TEST_ENVIRONMENT), patch(
            "app.ai.engine.get_client",
            return_value=client,
        ):
            result = process_message(message, **state)

        assert result.allowed is True
        assert limit_message in result.reply
        assert all(
            any(
                all(action.params.get(key) == value for key, value in expected.items())
                for action in result.actions
            )
            for expected in expected_actions
        )
        client.chat.completions.create.assert_not_called()


def test_first_person_temperature_feeling_uses_active_speaker_with_two_degrees():
    client = make_client()

    with patch.dict(os.environ, TEST_ENVIRONMENT), patch(
        "app.ai.engine.get_client",
        return_value=client,
    ):
        result = process_message(
            "Mi-e frig",
            current_temperature=20,
            current_passenger_temperature=21,
            speaker="passenger",
        )

    assert [action.params["value"] for action in result.actions] == [
        21 + TEMPERATURE_COMFORT_STEP,
    ]
    client.chat.completions.create.assert_not_called()


def test_generic_temperature_feelings_keep_two_degree_adjustment():
    messages = (
        "Ce frig e in masina",
        "E prea cald",
        "E prea rece",
        "Ce cald e in masina",
    )

    for message in messages:
        client = make_client()

        with patch.dict(os.environ, TEST_ENVIRONMENT), patch(
            "app.ai.engine.get_client",
            return_value=client,
        ):
            result = process_message(
                message,
                current_temperature=20,
                current_passenger_temperature=21,
            )

        assert [action.params["value"] for action in result.actions] == [
            (
                20 + TEMPERATURE_COMFORT_STEP
                if "frig" in message or "rece" in message
                else 20 - TEMPERATURE_COMFORT_STEP
            ),
            (
                21 + TEMPERATURE_COMFORT_STEP
                if "frig" in message or "rece" in message
                else 21 - TEMPERATURE_COMFORT_STEP
            ),
        ]
        client.chat.completions.create.assert_not_called()


def test_intensified_temperature_feelings_use_five_degree_adjustment():
    client = make_client()

    with patch.dict(os.environ, TEST_ENVIRONMENT), patch(
        "app.ai.engine.get_client",
        return_value=client,
    ):
        result = process_message(
            "Îmi e foarte frig",
            current_temperature=20,
            current_passenger_temperature=21,
        )

    assert [action.params["value"] for action in result.actions] == [
        20 + TEMPERATURE_INTENSE_COMFORT_STEP,
    ]
    client.chat.completions.create.assert_not_called()


def test_intensified_temperature_feeling_uses_standard_limit_message():
    client = make_client()

    with patch.dict(os.environ, TEST_ENVIRONMENT), patch(
        "app.ai.engine.get_client",
        return_value=client,
    ):
        result = process_message(
            "Îmi este extrem de cald",
            current_temperature=20,
            current_passenger_temperature=20,
            speaker="passenger",
        )

    assert [action.params["value"] for action in result.actions] == [
        MIN_TEMPERATURE,
    ]
    assert result.reply == (
        "Temperatura minimă este 16°C.\n\n"
        "Am setat temperatura pasagerului de la 20°C la 16°C."
    )
    client.chat.completions.create.assert_not_called()


def test_first_person_temperature_command_targets_active_driver_only():
    client = make_client()

    with patch.dict(os.environ, TEST_ENVIRONMENT), patch(
        "app.ai.engine.get_client",
        return_value=client,
    ):
        result = process_message(
            "Setează-mi mie temperatura la 25 grade",
            current_temperature=20,
            current_passenger_temperature=21,
            speaker="driver",
        )

    assert [action.params for action in result.actions] == [
        {"zone": "driver", "value": 25}
    ]
    assert "șoferului" in result.reply
    assert "pasagerului" not in result.reply
    client.chat.completions.create.assert_not_called()


def test_first_person_temperature_limit_targets_active_passenger_only():
    client = make_client()

    with patch.dict(os.environ, TEST_ENVIRONMENT), patch(
        "app.ai.engine.get_client",
        return_value=client,
    ):
        result = process_message(
            "Setează-mi mie temperatura la 35 grade",
            current_temperature=20,
            current_passenger_temperature=21,
            speaker="passenger",
        )

    assert [action.params for action in result.actions] == [
        {"zone": "passenger", "value": MAX_TEMPERATURE}
    ]
    assert result.reply == (
        f"Temperatura maximă este {MAX_TEMPERATURE}°C.\n\n"
        f"Am setat temperatura pasagerului de la 21°C la "
        f"{MAX_TEMPERATURE}°C."
    )
    client.chat.completions.create.assert_not_called()


def test_first_person_seat_heating_command_targets_active_passenger_only():
    client = make_client()

    with patch.dict(os.environ, TEST_ENVIRONMENT), patch(
        "app.ai.engine.get_client",
        return_value=client,
    ):
        result = process_message(
            "Setează-mi mie încălzirea în scaune la nivelul 2",
            current_driver_seat_heating=0,
            current_passenger_seat_heating=1,
            speaker="passenger",
        )

    assert [action.params for action in result.actions] == [
        {"zone": "passenger", "level": 2}
    ]
    assert "pasagerului" in result.reply
    assert "șoferului" not in result.reply
    client.chat.completions.create.assert_not_called()


def test_explicit_values_below_limits_are_clamped():
    cases = [
        (
            "Pune temperatura la -5",
            {"current_temperature": 20, "current_passenger_temperature": 21},
            [16, 16],
        ),
        (
            "Pune volumul la -10",
            {"current_volume": 50},
            [0],
        ),
        (
            "Pune viteza ventilatorului la -1",
            {"current_fan_speed": 2},
            [0],
        ),
        (
            "Pune incalzirea scaunelor la -1",
            {
                "current_driver_seat_heating": 2,
                "current_passenger_seat_heating": 1,
            },
            [0, 0],
        ),
    ]

    for message, state, expected_values in cases:
        client = make_client()

        with patch.dict(os.environ, TEST_ENVIRONMENT), patch(
            "app.ai.engine.get_client",
            return_value=client,
        ):
            result = process_message(message, **state)

        assert result.allowed is True
        assert [
            action.params.get("value", action.params.get("level"))
            for action in result.actions
        ] == expected_values
        client.chat.completions.create.assert_not_called()


def test_unsupported_language_is_rejected_before_openai_is_called():
    with patch("app.ai.engine.get_client") as get_client:
        result = process_message("Quelle est la température?")

    assert result.allowed is False
    assert result.actions == []
    assert "română sau engleză" in result.reply
    get_client.assert_not_called()


def test_mixed_language_is_rejected_before_openai_is_called():
    with patch("app.ai.engine.get_client") as get_client:
        result = process_message("Setează temperatura to 24")

    assert result.allowed is False
    assert result.actions == []
    assert "română sau engleză" in result.reply
    get_client.assert_not_called()


def test_temperature_without_zone_updates_both_zones():
    client = make_client(
        make_tool_call(
            "set_temperature",
            {"zone": "driver", "value": 22},
        ),
        make_tool_call(
            "set_temperature",
            {"zone": "passenger", "value": 23},
        ),
    )

    with patch.dict(os.environ, TEST_ENVIRONMENT), patch(
        "app.ai.engine.get_client",
        return_value=client,
    ):
        result = process_message(
            "Crește temperatura cu 2 grade",
            current_temperature=20,
            current_passenger_temperature=21,
        )

    assert [action.type for action in result.actions] == [
        "SET_TEMPERATURE",
        "SET_TEMPERATURE",
    ]
    assert result.actions[0].params == {"zone": "driver", "value": 22}
    assert result.actions[1].params == {"zone": "passenger", "value": 23}


def test_exact_temperature_without_zone_uses_same_value_for_both_zones():
    client = make_client(
        make_tool_call(
            "set_temperature",
            {"zone": "driver", "value": 24},
        ),
        make_tool_call(
            "set_temperature",
            {"zone": "passenger", "value": 24},
        ),
    )

    with patch.dict(os.environ, TEST_ENVIRONMENT), patch(
        "app.ai.engine.get_client",
        return_value=client,
    ):
        result = process_message(
            "Set the temperature to 24 degrees",
            current_temperature=16,
            current_passenger_temperature=28,
        )

    assert [action.params["value"] for action in result.actions] == [24, 24]


def test_exact_seat_heating_without_zone_uses_same_level_for_both_seats():
    client = make_client(
        make_tool_call(
            "set_seat_heating",
            {"zone": "driver", "level": 2},
        ),
        make_tool_call(
            "set_seat_heating",
            {"zone": "passenger", "level": 2},
        ),
    )

    with patch.dict(os.environ, TEST_ENVIRONMENT), patch(
        "app.ai.engine.get_client",
        return_value=client,
    ):
        result = process_message(
            "Set seat heating to level 2",
            current_driver_seat_heating=1,
            current_passenger_seat_heating=3,
        )

    assert [action.params["level"] for action in result.actions] == [2, 2]


def test_general_temperature_command_rejects_duplicate_zone_calls():
    client = make_client(
        make_tool_call(
            "set_temperature",
            {"zone": "driver", "value": 24},
        ),
        make_tool_call(
            "set_temperature",
            {"zone": "driver", "value": 24},
        ),
        make_tool_call(
            "set_temperature",
            {"zone": "passenger", "value": 24},
        ),
    )

    with patch.dict(os.environ, TEST_ENVIRONMENT), patch(
        "app.ai.engine.get_client",
        return_value=client,
    ):
        result = process_message("Ajustează temperatura la 24 de grade")

    assert result.allowed is False
    assert result.actions == []


def test_generic_temperature_command_uses_driver_speaker_role_only():
    client = make_client(
        make_tool_call(
            "set_temperature",
            {"zone": "driver", "value": 22},
        ),
        make_tool_call(
            "set_temperature",
            {"zone": "passenger", "value": 22},
        ),
    )

    with patch.dict(os.environ, TEST_ENVIRONMENT), patch(
        "app.ai.engine.get_client",
        return_value=client,
    ):
        result = process_message(
            "Setează temperatura la 22 de grade",
            speaker="driver",
            current_temperature=20,
            current_passenger_temperature=21,
        )

    assert result.allowed is True
    assert [action.params["zone"] for action in result.actions] == ["driver"]
    assert result.actions[0].params == {"zone": "driver", "value": 22}


def test_generic_temperature_command_uses_passenger_speaker_role_only():
    client = make_client(
        make_tool_call(
            "set_temperature",
            {"zone": "driver", "value": 22},
        ),
        make_tool_call(
            "set_temperature",
            {"zone": "passenger", "value": 22},
        ),
    )

    with patch.dict(os.environ, TEST_ENVIRONMENT), patch(
        "app.ai.engine.get_client",
        return_value=client,
    ):
        result = process_message(
            "Setează temperatura la 22 de grade",
            speaker="passenger",
            current_temperature=20,
            current_passenger_temperature=21,
        )

    assert result.allowed is True
    assert [action.params["zone"] for action in result.actions] == ["passenger"]
    assert result.actions[0].params == {"zone": "passenger", "value": 22}


def test_explicit_role_for_driver_overrides_speaker_context():
    client = make_client(
        make_tool_call(
            "set_temperature",
            {"zone": "driver", "value": 24},
        ),
        make_tool_call(
            "set_temperature",
            {"zone": "passenger", "value": 24},
        ),
    )

    with patch.dict(os.environ, TEST_ENVIRONMENT), patch(
        "app.ai.engine.get_client",
        return_value=client,
    ):
        result = process_message(
            "Setează temperatura șoferului la 24 de grade",
            speaker="passenger",
            current_temperature=20,
            current_passenger_temperature=21,
        )

    assert result.allowed is True
    assert [action.params["zone"] for action in result.actions] == ["driver"]
    assert result.actions[0].params == {"zone": "driver", "value": 24}


def test_previous_song_generates_previous_action():
    client = make_client(make_tool_call("media_previous", {}))

    with patch.dict(os.environ, TEST_ENVIRONMENT), patch(
        "app.ai.engine.get_client",
        return_value=client,
    ):
        result = process_message("Go to the previous song")

    assert result.allowed is True
    assert result.actions == [
        VehicleAction(type=ACTION_MEDIA_PREVIOUS, params={})
    ]


def test_english_explicit_zone_command_is_not_treated_as_general():
    client = make_client(
        make_tool_call(
            "set_temperature",
            {"zone": "driver", "value": 24},
        )
    )

    with patch.dict(os.environ, TEST_ENVIRONMENT), patch(
        "app.ai.engine.get_client",
        return_value=client,
    ):
        result = process_message(
            "Set the driver's temperature to 24 degrees",
            current_temperature=20,
            current_passenger_temperature=21,
        )

    assert result.allowed is True
    assert result.actions[0].params == {"zone": "driver", "value": 24}


def test_invalid_tool_parameter_is_rejected_without_actions():
    client = make_client(
        make_tool_call("set_volume", {"value": 24.5}),
    )

    with patch.dict(os.environ, TEST_ENVIRONMENT), patch(
        "app.ai.engine.get_client",
        return_value=client,
    ):
        result = process_message("Setează volumul la 24.5")

    assert result.allowed is False
    assert result.actions == []


def test_reset_generates_one_reset_action():
    client = make_client(make_tool_call("reset_vehicle", {}))

    with patch.dict(os.environ, TEST_ENVIRONMENT), patch(
        "app.ai.engine.get_client",
        return_value=client,
    ):
        result = process_message("Resetează tot")

    assert result.allowed is True
    assert result.actions == [
        VehicleAction(type=ACTION_RESET_VEHICLE, params={})
    ]

    service = VehicleService()
    service.set_volume(90)
    service.execute_actions(result.actions)
    assert service.get_state() == VehicleState()


def test_missing_model_is_reported_without_calling_openai():
    client = Mock()

    with patch.dict(os.environ, {}, clear=True), patch(
        "app.ai.engine.get_client",
        return_value=client,
    ):
        result = process_message("Setează volumul la 50")

    assert result.allowed is False
    assert result.actions == []
    client.chat.completions.create.assert_not_called()


def test_temperature_state_query_returns_only_temperature():
    client = make_client(make_tool_call("get_vehicle_state", {}))

    with patch.dict(os.environ, TEST_ENVIRONMENT), patch(
        "app.ai.engine.get_client",
        return_value=client,
    ):
        result = process_message(
            "Cât e temperatura în mașină?",
            current_temperature=22,
            current_passenger_temperature=21,
            current_volume=70,
            current_fan_speed=3,
        )

    assert result.allowed is True
    assert result.reply == "Temperatura este 22°C la șofer și 21°C la pasager."
    assert "Volum" not in result.reply
    assert "Ventilator" not in result.reply


def test_english_driver_state_query_returns_only_driver_temperature():
    client = make_client(make_tool_call("get_vehicle_state", {}))

    with patch.dict(os.environ, TEST_ENVIRONMENT), patch(
        "app.ai.engine.get_client",
        return_value=client,
    ):
        result = process_message(
            "What is the driver's temperature?",
            current_temperature=22,
            current_passenger_temperature=21,
            current_volume=70,
            current_fan_speed=3,
        )

    assert result.reply == "The driver's temperature is 22°C."


def test_english_song_query_returns_only_current_song():
    client = make_client(make_tool_call("get_vehicle_state", {}))

    with patch.dict(os.environ, TEST_ENVIRONMENT), patch(
        "app.ai.engine.get_client",
        return_value=client,
    ):
        result = process_message(
            "What is the current song?",
            current_temperature=22,
            current_song="Chill Mix",
            current_volume=70,
        )

    assert result.reply == 'The current song is "Chill Mix".'


def test_english_ac_query_returns_only_ac_state():
    client = make_client(make_tool_call("get_vehicle_state", {}))

    with patch.dict(os.environ, TEST_ENVIRONMENT), patch(
        "app.ai.engine.get_client",
        return_value=client,
    ):
        result = process_message(
            "Is the air conditioning on?",
            ac_enabled=False,
            current_temperature=22,
            current_volume=70,
        )

    assert result.reply == "Air conditioning is off."


def test_english_vehicle_state_query_returns_full_summary():
    client = make_client(make_tool_call("get_vehicle_state", {}))

    with patch.dict(os.environ, TEST_ENVIRONMENT), patch(
        "app.ai.engine.get_client",
        return_value=client,
    ):
        result = process_message("What is the vehicle state?")

    assert result.reply.startswith("The vehicle state is:")
    assert "Driver temperature" in result.reply
    assert "Volume" in result.reply


def test_seat_heating_state_query_returns_only_seat_heating():
    client = make_client(make_tool_call("get_vehicle_state", {}))

    with patch.dict(os.environ, TEST_ENVIRONMENT), patch(
        "app.ai.engine.get_client",
        return_value=client,
    ):
        result = process_message(
            "Cât e încălzirea în scaune?",
            current_driver_seat_heating=2,
            current_passenger_seat_heating=1,
            current_temperature=25,
            current_volume=70,
        )

    assert result.allowed is True
    assert result.reply == (
        "Încălzirea scaunelor este la nivelul 2 la șofer și "
        "la nivelul 1 la pasager."
    )
    assert "Temperatura" not in result.reply
    assert "Volum" not in result.reply


def test_volume_state_query_returns_only_volume():
    client = make_client(make_tool_call("get_vehicle_state", {}))

    with patch.dict(os.environ, TEST_ENVIRONMENT), patch(
        "app.ai.engine.get_client",
        return_value=client,
    ):
        result = process_message(
            "Cât este volumul?",
            current_volume=65,
            current_temperature=24,
        )

    assert result.allowed is True
    assert result.reply == "Volumul este 65%."
    assert "Temperatura" not in result.reply
    assert "Ventilator" not in result.reply


def test_generic_vehicle_state_query_returns_full_summary():
    client = make_client(make_tool_call("get_vehicle_state", {}))

    with patch.dict(os.environ, TEST_ENVIRONMENT), patch(
        "app.ai.engine.get_client",
        return_value=client,
    ):
        result = process_message("Care este starea mașinii?")

    assert result.allowed is True
    assert result.reply.startswith("Starea mașinii este:")
    assert "Temperatură șofer" in result.reply
    assert "Volum" in result.reply
    assert "Ventilator" in result.reply


def test_english_action_confirmation_is_in_english():
    client = make_client(
        make_tool_call(
            "set_volume",
            {"value": 70},
        )
    )

    with patch.dict(os.environ, TEST_ENVIRONMENT), patch(
        "app.ai.engine.get_client",
        return_value=client,
    ):
        result = process_message("Set the volume to 70", current_volume=50)

    assert result.allowed is True
    assert result.reply == "I set the volume from 50% to 70%."


def test_english_vehicle_state_is_in_english():
    client = make_client(make_tool_call("get_vehicle_state", {}))

    with patch.dict(os.environ, TEST_ENVIRONMENT), patch(
        "app.ai.engine.get_client",
        return_value=client,
    ):
        result = process_message(
            "What is the temperature in the car?",
            current_temperature=22,
            current_passenger_temperature=21,
        )

    assert result.allowed is True
    assert result.reply == (
        "The temperature is 22°C for the driver and 21°C for the passenger."
    )


def make_email(name: str) -> str:
    return f"{name}-{uuid.uuid4().hex[:8]}@example.com"


def make_wav_bytes(freq: int = 440, duration_seconds: float = 0.3) -> bytes:
    buffer = BytesIO()
    sample_rate = 16000
    frames = []
    for index in range(int(sample_rate * duration_seconds)):
        sample = int(
            32767 * 0.25 * __import__("math").sin(
                2 * __import__("math").pi * freq * index / sample_rate
            )
        )
        frames.append(struct.pack("<h", sample))

    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(b"".join(frames))

    return buffer.getvalue()


def make_same_speaker_phrase_bytes(base_freq: int, duration_seconds: float) -> bytes:
    buffer = BytesIO()
    sample_rate = 16000
    frames = []

    for index in range(int(sample_rate * duration_seconds)):
        t = index / sample_rate
        envelope = 0.55 + 0.45 * __import__("math").sin(
            2 * __import__("math").pi * (3.3 + base_freq / 180.0) * t
        )
        carrier = __import__("math").sin(
            2 * __import__("math").pi * (base_freq * (1.0 + 0.08 * __import__("math").sin(2 * __import__("math").pi * 2.3 * t))) * t
        )
        nuance = 0.45 * __import__("math").sin(
            2 * __import__("math").pi * (base_freq * 1.8) * t + 0.8
        )
        sample = int(32767 * 0.18 * (carrier + nuance) * envelope)
        frames.append(struct.pack("<h", max(-32767, min(32767, sample))))

    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(b"".join(frames))

    return buffer.getvalue()


def test_voice_enrollment_and_identify_match_user():
    with TestClient(app) as client:
        user_response = client.post(
            "/users",
            json={
                "name": "Alice",
                "email": make_email("alice"),
                "password": "secret123",
            },
        )
        user_id = user_response.json()["user_id"]

        session_response = client.post(
            "/sessions",
            json={"created_by_user_id": user_id},
        )
        session_id = session_response.json()["session_id"]

        client.post(
            f"/sessions/{session_id}/participants",
            json={"user_id": user_id, "role": "driver"},
        )

        wav_payload = make_wav_bytes()
        enroll_response = client.post(
            f"/users/{user_id}/voice/enroll",
            files=[
                ("files", ("sample-1.wav", wav_payload, "audio/wav")),
                ("files", ("sample-2.wav", wav_payload, "audio/wav")),
                ("files", ("sample-3.wav", wav_payload, "audio/wav")),
            ],
        )

        assert enroll_response.status_code == 200
        assert enroll_response.json()["voice_enrolled"] is True

        identify_response = client.post(
            "/voice/identify",
            data={"session_id": session_id},
            files={"file": ("sample.wav", wav_payload, "audio/wav")},
        )

        assert identify_response.status_code == 200
        assert identify_response.json()["matched"] is True
        assert identify_response.json()["user_id"] == user_id
        assert identify_response.json()["confidence"] >= 0.5

        resolve_response = client.post(
            "/voice/resolve-speaker",
            json={"session_id": session_id, "user_id": user_id},
        )

        assert resolve_response.status_code == 200
        assert resolve_response.json() == {
            "user_id": user_id,
            "session_id": session_id,
            "role": "driver",
        }


def test_voice_identify_filters_by_session_membership():
    with TestClient(app) as client:
        driver_response = client.post(
            "/users",
            json={
                "name": "Alice",
                "email": make_email("alice"),
                "password": "secret123",
            },
        )
        driver_id = driver_response.json()["user_id"]

        outsider_response = client.post(
            "/users",
            json={
                "name": "Mallory",
                "email": make_email("mallory"),
                "password": "secret123",
            },
        )
        outsider_id = outsider_response.json()["user_id"]

        session_response = client.post(
            "/sessions",
            json={"created_by_user_id": driver_id},
        )
        session_id = session_response.json()["session_id"]

        client.post(
            f"/sessions/{session_id}/participants",
            json={"user_id": driver_id, "role": "driver"},
        )

        driver_payload = make_wav_bytes(440, 0.3)
        outsider_payload = make_wav_bytes(680, 0.3)

        client.post(
            f"/users/{driver_id}/voice/enroll",
            files=[
                ("files", ("sample-1.wav", driver_payload, "audio/wav")),
                ("files", ("sample-2.wav", driver_payload, "audio/wav")),
                ("files", ("sample-3.wav", driver_payload, "audio/wav")),
            ],
        )

        client.post(
            f"/users/{outsider_id}/voice/enroll",
            files=[
                ("files", ("sample-1.wav", outsider_payload, "audio/wav")),
                ("files", ("sample-2.wav", outsider_payload, "audio/wav")),
                ("files", ("sample-3.wav", outsider_payload, "audio/wav")),
            ],
        )

        response = client.post(
            "/voice/identify",
            data={"session_id": session_id},
            files={"file": ("match.wav", driver_payload, "audio/wav")},
        )

        assert response.status_code == 200
        assert response.json()["matched"] is True
        assert response.json()["user_id"] == driver_id
        assert response.json()["enrolled_users_count"] == 1

        outsider_match = client.post(
            "/voice/identify",
            data={"session_id": session_id},
            files={"file": ("outsider.wav", outsider_payload, "audio/wav")},
        )

        assert outsider_match.status_code == 200
        assert outsider_match.json()["enrolled_users_count"] == 1
        assert outsider_match.json()["user_id"] != outsider_id


def test_voice_command_payload_uses_session_user_and_resolved_role():
    with TestClient(app) as client:
        user_response = client.post(
            "/users",
            json={
                "name": "Dana",
                "email": make_email("dana"),
                "password": "secret123",
            },
        )
        user_id = user_response.json()["user_id"]

        session_response = client.post(
            "/sessions",
            json={"created_by_user_id": user_id},
        )
        session_id = session_response.json()["session_id"]

        client.post(
            f"/sessions/{session_id}/participants",
            json={"user_id": user_id, "role": "driver"},
        )

        wav_payload = make_wav_bytes(480, 0.3)
        client.post(
            f"/users/{user_id}/voice/enroll",
            files=[
                ("files", ("sample-1.wav", wav_payload, "audio/wav")),
                ("files", ("sample-2.wav", wav_payload, "audio/wav")),
                ("files", ("sample-3.wav", wav_payload, "audio/wav")),
            ],
        )

        response = client.post(
            "/assistant/message",
            json={
                "message": "setează temperatura la 24 de grade",
                "speaker": "driver",
                "input_type": "voice",
                "user_id": user_id,
                "session_id": session_id,
            },
        )

        assert response.status_code == 200
        assert response.json()["state"]["temperature"]["driver"] == 24
        assert response.json()["reply"]


def test_unknown_voice_is_not_matched_and_low_confidence_is_rejected():
    with TestClient(app) as client:
        user_response = client.post(
            "/users",
            json={
                "name": "Bob",
                "email": make_email("bob"),
                "password": "secret123",
            },
        )
        user_id = user_response.json()["user_id"]

        wav_payload = make_wav_bytes(660, 0.3)
        client.post(
            f"/users/{user_id}/voice/enroll",
            files=[
                ("files", ("sample-1.wav", wav_payload, "audio/wav")),
                ("files", ("sample-2.wav", wav_payload, "audio/wav")),
                ("files", ("sample-3.wav", wav_payload, "audio/wav")),
            ],
        )

        other_payload = make_wav_bytes(880, 0.3)
        response = client.post(
            "/voice/identify",
            files={"file": ("unknown.wav", other_payload, "audio/wav")},
        )

        assert response.status_code == 200
        assert response.json()["matched"] is False
        assert response.json()["user_id"] is None
        assert response.json()["confidence"] < 0.5


def test_resolve_speaker_rejects_user_not_in_session():
    with TestClient(app) as client:
        user_response = client.post(
            "/users",
            json={
                "name": "Charlie",
                "email": make_email("charlie"),
                "password": "secret123",
            },
        )
        user_id = user_response.json()["user_id"]

        session_response = client.post(
            "/sessions",
            json={"created_by_user_id": user_id},
        )
        session_id = session_response.json()["session_id"]

        response = client.post(
            "/voice/resolve-speaker",
            json={"session_id": session_id, "user_id": user_id},
        )

        assert response.status_code == 404
        assert response.json()["detail"] == (
            "User is not a participant in this session"
        )


def test_generic_voice_command_supports_driver_and_passenger_roles():
    client = make_client(
        make_tool_call(
            "set_temperature",
            {"zone": "driver", "value": 21},
        ),
    )

    with patch.dict(os.environ, TEST_ENVIRONMENT), patch(
        "app.ai.engine.get_client",
        return_value=client,
    ):
        driver_result = process_message(
            "setează temperatura la 21 de grade",
            speaker="driver",
            current_temperature=20,
            current_passenger_temperature=21,
        )
        passenger_result = process_message(
            "setează temperatura la 21 de grade",
            speaker="passenger",
            current_temperature=20,
            current_passenger_temperature=18,
        )

    assert [action.params["zone"] for action in driver_result.actions] == ["driver"]
    assert [action.params["zone"] for action in passenger_result.actions] == ["passenger"]


def test_explicit_passenger_command_keeps_passenger_target_only():
    client = make_client(
        make_tool_call(
            "set_temperature",
            {"zone": "passenger", "value": 22},
        ),
    )

    with patch.dict(os.environ, TEST_ENVIRONMENT), patch(
        "app.ai.engine.get_client",
        return_value=client,
    ):
        result = process_message(
            "setează temperatura pasagerului la 22",
            speaker="driver",
            current_temperature=20,
            current_passenger_temperature=18,
        )

    assert result.allowed is True
    assert [action.params["zone"] for action in result.actions] == ["passenger"]


def test_generic_voiced_command_does_not_change_both_roles():
    client = make_client(
        make_tool_call(
            "set_temperature",
            {"zone": "driver", "value": 21},
        ),
        make_tool_call(
            "set_temperature",
            {"zone": "passenger", "value": 21},
        ),
    )

    with patch.dict(os.environ, TEST_ENVIRONMENT), patch(
        "app.ai.engine.get_client",
        return_value=client,
    ):
        result = process_message(
            "setează temperatura la 21 de grade",
            speaker="driver",
            current_temperature=20,
            current_passenger_temperature=21,
        )

    assert len(result.actions) == 1
    assert result.actions[0].params == {"zone": "driver", "value": 21}


def test_voice_identify_matches_same_speaker_across_different_phrases():
    with TestClient(app) as client:
        user_response = client.post(
            "/users",
            json={
                "name": "Diana",
                "email": make_email("diana_different_phrase"),
                "password": "secret123",
            },
        )
        user_id = user_response.json()["user_id"]
        session_response = client.post(
            "/sessions",
            json={"created_by_user_id": user_id},
        )
        session_id = session_response.json()["session_id"]
        client.post(
            f"/sessions/{session_id}/participants",
            json={"user_id": user_id, "role": "driver"},
        )

        enrollment_samples = [
            make_same_speaker_phrase_bytes(120, 0.38),
            make_same_speaker_phrase_bytes(160, 0.44),
            make_same_speaker_phrase_bytes(190, 0.36),
        ]
        for index, sample in enumerate(enrollment_samples, start=1):
            client.post(
                f"/users/{user_id}/voice/enroll",
                files=[
                    ("files", (f"sample-{index}-a.wav", sample, "audio/wav")),
                    ("files", (f"sample-{index}-b.wav", sample, "audio/wav")),
                    ("files", (f"sample-{index}-c.wav", sample, "audio/wav")),
                ],
            )

        different_phrase = make_same_speaker_phrase_bytes(260, 0.68)
        response = client.post(
            "/voice/identify",
            data={"session_id": session_id},
            files={"file": ("different-phrase.wav", different_phrase, "audio/wav")},
        )

        assert response.status_code == 200
        assert response.json()["matched"] is True
        assert response.json()["user_id"] == user_id
        assert response.json()["user_name"] == "Diana"


def test_voice_identify_checks_only_session_participants():
    with TestClient(app) as client:
        users = [
            {
                "name": "Alice",
                "email": make_email("alice_global"),
                "password": "secret123",
            },
            {
                "name": "Bob",
                "email": make_email("bob_global"),
                "password": "secret123",
            },
            {
                "name": "Carol",
                "email": make_email("carol_global"),
                "password": "secret123",
            },
        ]

        created_user_ids = []
        for payload in users:
            response = client.post("/users", json=payload)
            created_user_ids.append(response.json()["user_id"])

        session_response = client.post(
            "/sessions",
            json={"created_by_user_id": created_user_ids[0]},
        )
        session_id = session_response.json()["session_id"]

        client.post(
            f"/sessions/{session_id}/participants",
            json={"user_id": created_user_ids[0], "role": "driver"},
        )

        voice_payloads = [
            make_wav_bytes(400, 0.3),
            make_wav_bytes(500, 0.3),
            make_wav_bytes(600, 0.3),
        ]

        for user_id, voice_payload in zip(created_user_ids, voice_payloads):
            client.post(
                f"/users/{user_id}/voice/enroll",
                files=[
                    ("files", ("sample-1.wav", voice_payload, "audio/wav")),
                    ("files", ("sample-2.wav", voice_payload, "audio/wav")),
                    ("files", ("sample-3.wav", voice_payload, "audio/wav")),
                ],
            )

        response = client.post(
            "/voice/identify",
            data={"session_id": session_id},
            files={"file": ("carol.wav", voice_payloads[2], "audio/wav")},
        )

        assert response.status_code == 200
        assert response.json()["user_id"] != created_user_ids[2]
        assert response.json()["enrolled_users_count"] == 1


def test_voice_identify_returns_user_name_and_session_role_in_response():
    with TestClient(app) as client:
        user_response = client.post(
            "/users",
            json={
                "name": "Andrei",
                "email": make_email("andrei_voice_role"),
                "password": "secret123",
            },
        )
        user_id = user_response.json()["user_id"]

        session_response = client.post(
            "/sessions",
            json={"created_by_user_id": user_id},
        )
        session_id = session_response.json()["session_id"]

        client.post(
            f"/sessions/{session_id}/participants",
            json={"user_id": user_id, "role": "passenger"},
        )

        wav_payload = make_wav_bytes(720, 0.3)
        client.post(
            f"/users/{user_id}/voice/enroll",
            files=[
                ("files", ("sample-1.wav", wav_payload, "audio/wav")),
                ("files", ("sample-2.wav", wav_payload, "audio/wav")),
                ("files", ("sample-3.wav", wav_payload, "audio/wav")),
            ],
        )

        response = client.post(
            "/voice/identify",
            data={"session_id": session_id},
            files={"file": ("match.wav", wav_payload, "audio/wav")},
        )

        assert response.status_code == 200
        assert response.json()["matched"] is True
        assert response.json()["user_id"] == user_id
        assert response.json()["user_name"] == "Andrei"
        assert response.json()["role"] == "passenger"
