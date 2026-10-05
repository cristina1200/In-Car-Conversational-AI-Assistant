import type { VehicleState } from "../types";
import { AMBIENT_COLORS } from "../constants";
import "./AmbientLighting.css";

interface AmbientLightingProps {
  vehicleState: VehicleState;
  onCommand: (message: string) => void;
}

function AmbientLighting({
  vehicleState,
  onCommand,
}: AmbientLightingProps) {
  const currentColor =
    AMBIENT_COLORS.find(
      (color) => color.value === vehicleState.ambient_light
    )?.label ?? vehicleState.ambient_light;

  return (
    <section className="ambient-lighting">
      <div className="ambient-lighting-header">
        <div>
          <span className="section-label">
            AMBIENT LIGHTING
          </span>

          <h2>Interior lighting</h2>
        </div>

        {/* <span
          className="ambient-preview"
          style={{
            backgroundColor:
              vehicleState.ambient_light,
          }}
        ></span> */}
      </div>

      <div className="ambient-current">
        <span
          className="ambient-current-dot"
          style={{
            backgroundColor:
              vehicleState.ambient_light,
          }}
        ></span>

        <div>
          <span>Current color</span>
          <strong>{currentColor}</strong>
        </div>
      </div>

      <div className="ambient-colors">
        {AMBIENT_COLORS.map((color) => {
          const isSelected =
            vehicleState.ambient_light === color.value;

          return (
            <button
              key={color.value}
              className={`ambient-color-button ${
                isSelected ? "selected" : ""
              }`}
              onClick={() =>
                onCommand(
                  `Setează lumina ambientală pe ${color.command}`
                )
              }
            >
              <span
                className="ambient-color-circle"
                style={{ backgroundColor: color.value }}
              ></span>

              <span>
                {color.label}
              </span>

              {isSelected && (
                <span className="ambient-check">
                  ✓
                </span>
              )}
            </button>
          );
        })}
      </div>

      <p className="ambient-description">
        Choose a color for the interior ambient
        lighting.
      </p>
    </section>
  );
}

export default AmbientLighting;
