import type {
  SessionRole,
  UserPreferences,
  VehicleState,
} from "../types";

import { AMBIENT_COLOR_LABELS_EN } from "../constants";

import "./VehicleStatus.css";

interface VehicleStatusProps {
  vehicleState: VehicleState;
  preferences?: UserPreferences;
  sessionRole: SessionRole;
  onApplyPreferences: () => void;
}

function VehicleStatus({
  vehicleState,
  preferences,
  sessionRole,
  onApplyPreferences,
}: VehicleStatusProps) {
  const displayPreferences: UserPreferences =
    preferences ?? {
      driver_temperature: vehicleState.temperature.driver,
      passenger_temperature: vehicleState.temperature.passenger,
      driver_seat_heating: vehicleState.seat_heating.driver,
      passenger_seat_heating: vehicleState.seat_heating.passenger,
      fan_speed: vehicleState.fan_speed,
      volume: vehicleState.volume,
      ambient_light: vehicleState.ambient_light as UserPreferences["ambient_light"],
    };

  return (
    <section className="vehicle-status">
      <div className="vehicle-preferences-view">
        <span className="section-label">
          USER PROFILE
        </span>

        <h2>My Preferences</h2>

        <p>
          Your saved preferences for the current drive.
        </p>

        <div className="vehicle-preferences-list">
          <div>
            <span>
              {sessionRole === "driver"
                ? "Driver temperature"
                : "Passenger temperature"}
            </span>
            <strong>
              {sessionRole === "driver"
                ? displayPreferences.driver_temperature ?? "-"
                : displayPreferences.passenger_temperature ?? "-"}°C
            </strong>
          </div>

          <div>
            <span>
              {sessionRole === "driver"
                ? "Driver seat heating"
                : "Passenger seat heating"}
            </span>
            <strong>
              Level {sessionRole === "driver"
                ? displayPreferences.driver_seat_heating ?? "-"
                : displayPreferences.passenger_seat_heating ?? "-"}
            </strong>
          </div>

          <div>
            <span>Fan speed</span>
            <strong>
              Nivelul {displayPreferences.fan_speed ?? "-"}
            </strong>
          </div>

          <div>
            <span>Volum</span>
            <strong>{displayPreferences.volume ?? "-"}%</strong>
          </div>

          <div>
            <span>Ambient light</span>
            <strong className="ambient-light-name">
              {AMBIENT_COLOR_LABELS_EN[
                displayPreferences.ambient_light ?? ""
              ] ?? "-"}
            </strong>
          </div>
        </div>

        <button
          type="button"
          className="vehicle-apply-preferences-button"
          onClick={onApplyPreferences}
        >
          Apply Preferences
        </button>
      </div>
    </section>
  );
}

export default VehicleStatus;
