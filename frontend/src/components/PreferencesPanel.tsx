import { useState } from "react";

import type {
  AmbientLight,
  SessionRole,
  UserPreferences,
  VehicleState,
} from "../types";

import {
  MAX_FAN_SPEED,
  MAX_SEAT_HEATING,
  MAX_TEMPERATURE,
  MAX_VOLUME,
  MIN_FAN_SPEED,
  MIN_SEAT_HEATING,
  MIN_TEMPERATURE,
  MIN_VOLUME,
} from "../constants";

import "./PreferencesPanel.css";

interface PreferencesPanelProps {
  vehicleState: VehicleState;
  preferences: UserPreferences;
  sessionRole: SessionRole;
  isOpen: boolean;
  onApply: (preferences: UserPreferences) => void;
  onClose: () => void;
}

function PreferencesPanel({
  vehicleState,
  preferences,
  sessionRole,
  isOpen,
  onApply,
  onClose,
}: PreferencesPanelProps) {
  const [driverTemperature, setDriverTemperature] =
    useState(
      preferences.driver_temperature ??
        preferences.passenger_temperature ??
        vehicleState.temperature.driver
    );
  const [passengerTemperature, setPassengerTemperature] =
    useState(
      preferences.driver_temperature ??
        preferences.passenger_temperature ??
        vehicleState.temperature.passenger
    );
  const [driverSeatHeating, setDriverSeatHeating] =
    useState(
      preferences.driver_seat_heating ??
        preferences.passenger_seat_heating ??
        vehicleState.seat_heating.driver
    );
  const [passengerSeatHeating, setPassengerSeatHeating] =
    useState(
      preferences.driver_seat_heating ??
        preferences.passenger_seat_heating ??
        vehicleState.seat_heating.passenger
    );
  const [fanSpeed, setFanSpeed] =
    useState(preferences.fan_speed ?? vehicleState.fan_speed);
  const [volume, setVolume] =
    useState(preferences.volume ?? vehicleState.volume);
  const [ambientLight, setAmbientLight] =
    useState<AmbientLight>(
      preferences.ambient_light ??
        (vehicleState.ambient_light as AmbientLight)
    );

  if (!isOpen) {
    return null;
  }

  const isDriver = sessionRole === "driver";

  function applyPreferences() {
    onApply({
      driver_temperature: driverTemperature,
      passenger_temperature: passengerTemperature,
      driver_seat_heating: driverSeatHeating,
      passenger_seat_heating: passengerSeatHeating,
      fan_speed: fanSpeed,
      volume,
      ambient_light: ambientLight,
    });

    onClose();
  }

  return (
    <div className="preferences-modal-backdrop">
      <section
        className="preferences-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="preferences-title"
      >
        <div className="preferences-header">
          <div>
            <span className="section-label">
              USER PROFILE
            </span>
            <h2 id="preferences-title">
              Edit Preferences
            </h2>
            <p>
              Set your preferences for the current drive.
            </p>
          </div>

          <button
            type="button"
            className="preferences-close"
            onClick={onClose}
            aria-label="Close preferences"
          >
            ×
          </button>
        </div>

        <div className="preferences-fields">
          <label>
            {isDriver
              ? "Driver temperature"
              : "Passenger temperature"}
            <input
              type="number"
              min={MIN_TEMPERATURE}
              max={MAX_TEMPERATURE}
              value={
                isDriver
                  ? driverTemperature
                  : passengerTemperature
              }
              onChange={(event) => {
                const value = Number(event.target.value);

                setDriverTemperature(value);
                setPassengerTemperature(value);
              }}
            />
          </label>

          <label>
            {isDriver
              ? "Driver seat heating"
              : "Passenger seat heating"}
            <select
              value={
                isDriver
                  ? driverSeatHeating
                  : passengerSeatHeating
              }
              onChange={(event) => {
                const value = Number(event.target.value);

                setDriverSeatHeating(value);
                setPassengerSeatHeating(value);
              }}
            >
              {Array.from(
                { length: MAX_SEAT_HEATING - MIN_SEAT_HEATING + 1 },
                (_, index) => {
                  const level = MIN_SEAT_HEATING + index;

                  return (
                    <option key={level} value={level}>
                      {level === MIN_SEAT_HEATING ? "Off" : `Level ${level}`}
                    </option>
                  );
                }
              )}
            </select>
          </label>

          <label>
            Fan speed
            <select
              value={fanSpeed}
              onChange={(event) =>
                setFanSpeed(Number(event.target.value))
              }
            >
              {Array.from(
                { length: MAX_FAN_SPEED - MIN_FAN_SPEED + 1 },
                (_, index) => {
                  const level = MIN_FAN_SPEED + index;

                  return (
                    <option key={level} value={level}>
                      Level {level}
                    </option>
                  );
                }
              )}
            </select>
          </label>

          <label>
            Volume
            <input
              type="number"
              min={MIN_VOLUME}
              max={MAX_VOLUME}
              value={volume}
              onChange={(event) =>
                setVolume(Number(event.target.value))
              }
            />
          </label>

          <label>
            Ambient light
            <select
              value={ambientLight}
              onChange={(event) =>
                setAmbientLight(
                  event.target.value as AmbientLight
                )
              }
            >
              <option value="blue">Blue</option>
              <option value="red">Red</option>
              <option value="green">Green</option>
              <option value="white">White</option>
              <option value="purple">Purple</option>
              <option value="yellow">Yellow</option>
            </select>
          </label>
        </div>

        <button
          type="button"
          className="preferences-save"
          onClick={applyPreferences}
        >
          Save Preferences
        </button>
      </section>
    </div>
  );
}

export default PreferencesPanel;
