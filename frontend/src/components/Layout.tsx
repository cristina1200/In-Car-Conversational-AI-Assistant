import { useEffect, useState } from "react";
import type { ReactNode } from "react";

import type {
  SessionRole,
  UserProfile,
} from "../types";

import AccountMenu from "./AccountMenu";

import "./Layout.css";

export type ActiveView =
  | "cabin"
  | "media"
  | "vehicle"
  | "ambient";

interface LayoutProps {
  currentUser: UserProfile | null;
  sessionRole: SessionRole | null;
  onUserChange: (
    user: UserProfile | null
  ) => void;
  onRoleChange: (
    role: SessionRole
  ) => void;
  onEditPreferences: () => void;
  authModeRequest: "login" | "signup" | null;
  onAuthRequestHandled: () => void;
  activeView: ActiveView;
  onViewChange: (
    view: ActiveView
  ) => void;
  children: ReactNode;
}

interface WeatherResponse {
  current?: {
    temperature_2m?: number;
  };
}

function Layout({
  currentUser,
  sessionRole,
  onUserChange,
  onRoleChange,
  onEditPreferences,
  authModeRequest,
  onAuthRequestHandled,
  activeView,
  onViewChange,
  children,
}: LayoutProps) {
  const [currentTime, setCurrentTime] =
    useState(new Date());

  const [temperature, setTemperature] =
    useState("--°C");

  useEffect(() => {
    const intervalId = window.setInterval(() => {
      setCurrentTime(new Date());
    }, 1000);

    return () => {
      window.clearInterval(intervalId);
    };
  }, []);

  useEffect(() => {
    async function loadClujWeather() {
      try {
        const response = await fetch(
          "https://api.open-meteo.com/v1/forecast?latitude=46.7712&longitude=23.6236&current=temperature_2m&timezone=auto"
        );

        if (!response.ok) {
          throw new Error(
            "Weather request failed"
          );
        }

        const data: WeatherResponse =
          await response.json();

        const currentTemperature =
          data.current?.temperature_2m;

        if (
          currentTemperature !== undefined
        ) {
          setTemperature(
            `${Math.round(
              currentTemperature
            )}°C`
          );
        }
      } catch {
        setTemperature("--°C");
      }
    }

    void loadClujWeather();
  }, []);

  const formattedTime =
    currentTime.toLocaleTimeString(
      "ro-RO",
      {
        hour: "2-digit",
        minute: "2-digit",
      }
    );

  return (
    <div className="layout">
      <aside className="layout-sidebar">
        <div className="layout-brand">
          <div
            className="layout-brand-logo"
            aria-label="In-Car AI"
          >
            ✦
          </div>

          <span>In-Car AI</span>
        </div>

        <nav className="layout-navigation">
          <button
            className={`layout-nav-item ${
              activeView === "cabin"
                ? "active"
                : ""
            }`}
            onClick={() =>
              onViewChange("cabin")
            }
          >
            <span className="layout-nav-icon">
              ⌂
            </span>

            <span>Cabin</span>
          </button>

          <button
            className={`layout-nav-item ${
              activeView === "media"
                ? "active"
                : ""
            }`}
            onClick={() =>
              onViewChange("media")
            }
          >
            <span className="layout-nav-icon">
              ♫
            </span>

            <span>Media</span>
          </button>

          <button
            className={`layout-nav-item ${
              activeView === "vehicle"
                ? "active"
                : ""
            }`}
            onClick={() =>
              onViewChange("vehicle")
            }
          >
            <span className="layout-nav-icon">
              ▣
            </span>

            <span>Preferences</span>
          </button>

          <button
            className={`layout-nav-item ${
              activeView === "ambient"
                ? "active"
                : ""
            }`}
            onClick={() =>
              onViewChange("ambient")
            }
          >
            <span className="layout-nav-icon">
              ✦
            </span>

            <span>Ambient light</span>
          </button>
        </nav>
      </aside>

      <div className="layout-content">
        <header className="layout-header">
          <div className="layout-title">
            <h1>In-Car AI Assistant</h1>

            <p className="layout-subtitle">
              Your journey. Smarter. Together.
            </p>
          </div>

          <div className="layout-header-actions">
            <div className="layout-weather">
              <span className="layout-weather-icon">
                ☼
              </span>

              <span>{temperature}</span>
            </div>

            <span className="layout-time">
              {formattedTime}
            </span>

            <AccountMenu
              currentUser={currentUser}
              sessionRole={sessionRole}
              onUserChange={onUserChange}
              onRoleChange={onRoleChange}
              onEditPreferences={onEditPreferences}
              authModeRequest={authModeRequest}
              onAuthRequestHandled={onAuthRequestHandled}
            />
          </div>
        </header>

        <main className="layout-main">
          {children}
        </main>
      </div>
    </div>
  );
}

export default Layout;
