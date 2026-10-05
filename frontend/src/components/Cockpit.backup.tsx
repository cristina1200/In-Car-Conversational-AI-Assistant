import type { VehicleState } from "../types";
import type { ActiveView } from "./Layout";

import MediaPanel from "./MediaPanel";
import VehicleStatus from "./VehicleStatus";
import AmbientLighting from "./AmbientLighting";

import "./Cockpit.css";

interface CockpitProps {
  vehicleState: VehicleState;
  isConnected: boolean;
  activeView: ActiveView;
  onCommand: (message: string) => void;
}

function Cockpit({
  vehicleState,
  isConnected,
  activeView,
  onCommand,
}: CockpitProps) {
  const driverSeatOn =
    vehicleState.seat_heating.driver > 0;

  const passengerSeatOn =
    vehicleState.seat_heating.passenger > 0;

  function renderCabinContent() {
    return (
      <>
        <div className="cockpit-info-header">
          <div>
            <span className="cockpit-info-label">
              IN-CAR AI ASSISTANT
            </span>

            <h2>Welcome back, Cristina</h2>

            <p>Your cabin is ready.</p>
          </div>

          <div
            className={`cockpit-connection ${
              isConnected
                ? "connected"
                : "offline"
            }`}
          >
            <span></span>

            {isConnected
              ? "Connected"
              : "Offline"}
          </div>
        </div>

        <div className="cockpit-info-grid">
          <div className="info-item">
            <span className="info-icon">♨</span>

            <div>
              <span className="info-title">
                Temperature
              </span>

              <strong>
                {vehicleState.temperature.driver}°C
              </strong>

              <small>
                Passenger:{" "}
                {vehicleState.temperature.passenger}°C
              </small>

              <small>
                AC:{" "}
                {vehicleState.ac_enabled
                  ? "ON"
                  : "OFF"}
              </small>
            </div>
          </div>

          <div className="info-item">
            <span className="info-icon">♧</span>

            <div>
              <span className="info-title">
                Seat heating
              </span>

              <strong>
                {driverSeatOn || passengerSeatOn
                  ? "ON"
                  : "OFF"}
              </strong>

              <small>
                Driver:{" "}
                {driverSeatOn
                  ? `Level ${vehicleState.seat_heating.driver}`
                  : "OFF"}
              </small>

              <small>
                Passenger:{" "}
                {passengerSeatOn
                  ? `Level ${vehicleState.seat_heating.passenger}`
                  : "OFF"}
              </small>
            </div>
          </div>

          <div className="info-item">
            <span className="info-icon">♫</span>

            <div>
              <span className="info-title">
                Media
              </span>

              <strong
                className={
                  vehicleState.is_playing
                    ? "state-on"
                    : "state-off"
                }
              >
                {vehicleState.is_playing
                  ? "ON"
                  : "OFF"}
              </strong>

              <small>
                {vehicleState.current_song}
              </small>
            </div>
          </div>

          <div className="info-item">
            <span className="info-icon">◖</span>

            <div>
              <span className="info-title">
                Volume
              </span>

              <strong>
                {vehicleState.volume}%
              </strong>

              <div className="info-progress">
                <span
                  style={{
                    width: `${vehicleState.volume}%`,
                  }}
                ></span>
              </div>
            </div>
          </div>

          <div className="info-item">
            <span className="info-icon">✣</span>

            <div>
              <span className="info-title">
                Fan
              </span>

              <strong>
                Level {vehicleState.fan_speed}
              </strong>

              <small>
                Automatic climate control
              </small>
            </div>
          </div>

          <div className="info-item">
            <span
              className="ambient-status-dot"
              style={{
                backgroundColor:
                  vehicleState.ambient_light,
              }}
            ></span>

            <div>
              <span className="info-title">
                Ambient light
              </span>

              <strong className="light-name">
                {vehicleState.ambient_light}
              </strong>

              <small>
                Interior lighting
              </small>
            </div>
          </div>
        </div>
      </>
    );
  }

  function renderSelectedContent() {
    if (activeView === "media") {
      return (
        <MediaPanel
          vehicleState={vehicleState}
          onCommand={onCommand}
        />
      );
    }

    if (activeView === "vehicle") {
      return (
        <VehicleStatus
          vehicleState={vehicleState}
          sessionRole="driver"
          onApplyPreferences={() => undefined}
        />
      );
    }

    if (activeView === "ambient") {
      return (
        <AmbientLighting
          vehicleState={vehicleState}
          onCommand={onCommand}
        />
      );
    }

    return renderCabinContent();
  }

  return (
    <section className="cockpit">
      <div className="dashboard-stage">
        <div className="cockpit-info-overlay">
          {renderSelectedContent()}
        </div>
      </div>
    </section>
  );
}

export default Cockpit;
