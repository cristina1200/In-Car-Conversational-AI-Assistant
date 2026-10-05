import type {
  SessionRole,
  UserPreferences,
  UserProfile,
  VehicleState,
} from "../types";
import type { ActiveView } from "./Layout";

import MediaPanel from "./MediaPanel";
import VehicleStatus from "./VehicleStatus";
import AmbientLighting from "./AmbientLighting";

import { useAnimatedNumber } from "../hooks/useAnimatedNumber";
import { useEffect, useRef, useState } from "react";
import type { CSSProperties } from "react";

import ClimateDial from "./ClimateDial";
import FanIndicator from "./FanIndicator";
import SeatHeatingIndicator from "./SeatHeatingIndicator";

import "./Cockpit.css";

interface CockpitProps {
  vehicleState: VehicleState;
  isConnected: boolean;
  activeView: ActiveView;
  onCommand: (message: string) => void;
  preferences: UserPreferences;
  currentUser: UserProfile | null;
  onOpenAuth: (mode: "login" | "signup") => void;
  sessionRole: SessionRole;
  currentUserName?: string | null;
  onApplyPreferences: () => void;
}

function Cockpit({
  vehicleState,
  isConnected,
  activeView,
  onCommand,
  preferences,
  currentUser,
  onOpenAuth,
  sessionRole,
  currentUserName,
  onApplyPreferences,
}: CockpitProps) {
  const driverSeatOn =
    vehicleState.seat_heating.driver > 0;

  const passengerSeatOn =
    vehicleState.seat_heating.passenger > 0;

  const isDriver = sessionRole === "driver";

  const animatedVolume = useAnimatedNumber(
  vehicleState.volume
  );

  const [volumeChanged, setVolumeChanged] = useState(false);

  const previousVolumeRef = useRef(vehicleState.volume);

  useEffect(() => {
    const previousVolume = previousVolumeRef.current;
    const currentVolume = vehicleState.volume;

    if (previousVolume !== currentVolume) {
      setVolumeChanged(true);

      const timeout = setTimeout(() => {
        setVolumeChanged(false);
      }, 800);

      previousVolumeRef.current = currentVolume;

      return () => clearTimeout(timeout);
    }

    previousVolumeRef.current = currentVolume;
  }, [vehicleState.volume]);

  const animatedDriverTemperature = useAnimatedNumber(
    vehicleState.temperature.driver
  );

  const animatedPassengerTemperature = useAnimatedNumber(
    vehicleState.temperature.passenger
  );

  const [
    driverTemperatureChanged,
    setDriverTemperatureChanged
  ] = useState(false);

  const [
    passengerTemperatureChanged,
    setPassengerTemperatureChanged
  ] = useState(false);


  const previousDriverTemperatureRef = useRef(
    vehicleState.temperature.driver
  );

  const previousPassengerTemperatureRef = useRef(
    vehicleState.temperature.passenger
  );

  useEffect(() => {
    const previousDriver =
      previousDriverTemperatureRef.current;

    const previousPassenger =
      previousPassengerTemperatureRef.current;

    const currentDriver =
      vehicleState.temperature.driver;

    const currentPassenger =
      vehicleState.temperature.passenger;

    let driverTimeout: ReturnType<typeof setTimeout>;
    let passengerTimeout: ReturnType<typeof setTimeout>;

    if (previousDriver !== currentDriver) {
      setDriverTemperatureChanged(true);

      driverTimeout = setTimeout(() => {
        setDriverTemperatureChanged(false);
      }, 800);
    }

    if (previousPassenger !== currentPassenger) {
      setPassengerTemperatureChanged(true);

      passengerTimeout = setTimeout(() => {
        setPassengerTemperatureChanged(false);
      }, 800);
    }

    previousDriverTemperatureRef.current =
      currentDriver;

    previousPassengerTemperatureRef.current =
      currentPassenger;

    return () => {
      if (driverTimeout) {
        clearTimeout(driverTimeout);
      }
      if (passengerTimeout) {
        clearTimeout(passengerTimeout);
      }
    };
  }, [
    vehicleState.temperature.driver,
    vehicleState.temperature.passenger,
  ]);

  const [fanChanged, setFanChanged] = useState(false);

  const previousFanRef = useRef(vehicleState.fan_speed);

  useEffect(() => {
    const previousFan = previousFanRef.current;
    const currentFan = vehicleState.fan_speed;

    if (previousFan !== currentFan) {
      setFanChanged(true);

      const timeout = setTimeout(() => {
        setFanChanged(false);
      }, 800);

      previousFanRef.current = currentFan;

      return () => clearTimeout(timeout);
    }

    previousFanRef.current = currentFan;
  }, [vehicleState.fan_speed]);

  const [
    driverSeatHeatingChanged,
    setDriverSeatHeatingChanged,
  ] = useState(false);

  const [
    passengerSeatHeatingChanged,
    setPassengerSeatHeatingChanged,
  ] = useState(false);

  const previousDriverSeatHeatingRef = useRef(
    vehicleState.seat_heating.driver
  );

  const previousPassengerSeatHeatingRef = useRef(
    vehicleState.seat_heating.passenger
  );

  useEffect(() => {
    const previousDriver =
      previousDriverSeatHeatingRef.current;

    const previousPassenger =
      previousPassengerSeatHeatingRef.current;

    const currentDriver =
      vehicleState.seat_heating.driver;

    const currentPassenger =
      vehicleState.seat_heating.passenger;

    let driverTimeout: ReturnType<typeof setTimeout>;
    let passengerTimeout: ReturnType<typeof setTimeout>;

    if (previousDriver !== currentDriver) {
      setDriverSeatHeatingChanged(true);

      driverTimeout = setTimeout(() => {
        setDriverSeatHeatingChanged(false);
      }, 800);
    }

    if (previousPassenger !== currentPassenger) {
      setPassengerSeatHeatingChanged(true);

      passengerTimeout = setTimeout(() => {
        setPassengerSeatHeatingChanged(false);
      }, 800);
    }

    previousDriverSeatHeatingRef.current = currentDriver;
    previousPassengerSeatHeatingRef.current =
      currentPassenger;

    return () => {
      if (driverTimeout) {
        clearTimeout(driverTimeout);
      }

      if (passengerTimeout) {
        clearTimeout(passengerTimeout);
      }
    };
  }, [
    vehicleState.seat_heating.driver,
    vehicleState.seat_heating.passenger,
  ]);

  const [ambientChanged, setAmbientChanged] =
    useState(false);

  const previousAmbientRef = useRef(
    vehicleState.ambient_light
  );

  useEffect(() => {
    const previousAmbient =
      previousAmbientRef.current;

    const currentAmbient =
      vehicleState.ambient_light;

    if (previousAmbient !== currentAmbient) {
      setAmbientChanged(true);

      const timeout = setTimeout(() => {
        setAmbientChanged(false);
      }, 800);

      previousAmbientRef.current =
        currentAmbient;

      return () => clearTimeout(timeout);
    }

    previousAmbientRef.current =
      currentAmbient;
  }, [vehicleState.ambient_light]);

  function renderCabinContent() {
    return (
      <>
        <div className="cockpit-info-header">
          <div>
            <span className="cockpit-info-label">
              IN-CAR AI ASSISTANT
            </span>

            <h2>
              Welcome back, {currentUserName ?? currentUser?.name ?? "Guest"}
            </h2>

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
              ? "Online"
              : "Offline"}
          </div>
        </div>

        <div className="cockpit-info-grid">
          <div
            className={`info-item ${
              driverTemperatureChanged || passengerTemperatureChanged ? "info-item-active" : ""
            }`}
          >
            <span
              className={`info-icon ${
                driverTemperatureChanged || passengerTemperatureChanged
                  ?"temperature-icon-active"
                  : ""
              }`}
            >
              ♨
            </span>
            <div>
              <span className="info-title">
                Temperature
              </span>

              <strong>
                {isDriver
                  ? animatedDriverTemperature
                  : animatedPassengerTemperature}°C
              </strong>

              <small>
                {isDriver
                  ? "Driver preference"
                  : "Passenger preference"}
              </small>

              <small>
                AC:{" "}
                {vehicleState.ac_enabled
                  ? "ON"
                  : "OFF"}
              </small>
            </div>
          </div>

          <div
            className={`info-item ${
              driverSeatHeatingChanged ||
              passengerSeatHeatingChanged
                ? "info-item-active"
                : ""
            }`}
          >
            <span className="info-icon">♧</span>

            <div>
              <span className="info-title">
                Seat heating
              </span>

              <strong>
                {isDriver
                  ? driverSeatOn
                    ? "ON"
                    : "OFF"
                  : passengerSeatOn
                    ? "ON"
                    : "OFF"}
              </strong>

              <small>
                {isDriver
                  ? driverSeatOn
                    ? `Driver: Level ${vehicleState.seat_heating.driver}`
                    : "Driver: OFF"
                  : passengerSeatOn
                    ? `Passenger: Level ${vehicleState.seat_heating.passenger}`
                    : "Passenger: OFF"}
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

          <div
            className={`info-item ${
              volumeChanged ? "info-item-active" : ""
            }`}
          >
            <span
              className={`info-icon ${
                volumeChanged ? "volume-icon-active" : ""
              }`}
            >
              ◖
            </span>

            <div>
              <span className="info-title">
                Volume
              </span>

              <strong>
                {animatedVolume}%
              </strong>

              <div className="info-progress">
                <span
                  style={{
                    width: `${animatedVolume}%`,
                  }}
                ></span>
              </div>
            </div>
          </div>

          <div
            className={`info-item ${
              fanChanged ? "info-item-active" : ""
            }`}
          >
            <span
              className={`info-icon fan-icon fan-level-${vehicleState.fan_speed}`}
            >
              ✣
            </span>

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

          <div
            className={`info-item ${
              ambientChanged ? "info-item-active" : ""
            }`}
          >
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
      if (!currentUser) {
        return (
          <div className="guest-preferences">
            <span className="section-label">
              USER PROFILE
            </span>

            <h2>Preferences</h2>

            <p>
              To access your preferences, please create an account or log in.
            </p>

            <div className="guest-preferences-actions">
              <button
                type="button"
                onClick={() => onOpenAuth("signup")}
              >
                Sign up
              </button>

              <button
                type="button"
                onClick={() => onOpenAuth("login")}
              >
                Log in
              </button>
            </div>
          </div>
        );
      }

      return (
       <VehicleStatus
          vehicleState={vehicleState}
          preferences={preferences}
          sessionRole={sessionRole}
          onApplyPreferences={onApplyPreferences}
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

        <div className="ambient-strips">
          <span
            className={`ambient-strip ambient-strip-top-left ${
              ambientChanged ? "ambient-strip-changed" : ""
            }`}
            style={{
              "--ambient-color": vehicleState.ambient_light,
            } as CSSProperties}
          />

          <span
            className={`ambient-strip ambient-strip-top-right ${
              ambientChanged ? "ambient-strip-changed" : ""
            }`}
            style={{
              "--ambient-color": vehicleState.ambient_light,
            } as CSSProperties}
          />

          <span
            className={`ambient-strip ambient-strip-middle ${
              ambientChanged ? "ambient-strip-changed" : ""
            }`}
            style={{
              "--ambient-color":
                vehicleState.ambient_light,
            } as React.CSSProperties}
          />

          <span
            className={`ambient-strip ambient-strip-bottom ${
              ambientChanged ? "ambient-strip-changed" : ""
            }`}
            style={{
              "--ambient-color":
                vehicleState.ambient_light,
            } as React.CSSProperties}
          />

          <span
            className={`ambient-strip ambient-strip-reflection ${
              ambientChanged ? "ambient-strip-changed" : ""
            }`}
            style={{
              "--ambient-color":
                vehicleState.ambient_light,
            } as CSSProperties}
          />
        </div>

        <div className="climate-controls">
          <ClimateDial
            temperature={animatedDriverTemperature}
            label="DRIVER"
            changed={driverTemperatureChanged}
          />

          <FanIndicator
            level={vehicleState.fan_speed}
          />

          <ClimateDial
            temperature={animatedPassengerTemperature}
            label="PASSENGER"
            changed={passengerTemperatureChanged}
          />

          <SeatHeatingIndicator
            level={vehicleState.seat_heating.driver}
            side="driver"
          />

          <SeatHeatingIndicator
            level={vehicleState.seat_heating.passenger}
            side="passenger"
          />
        </div>

      </div>
    </section>
);
}

export default Cockpit;
