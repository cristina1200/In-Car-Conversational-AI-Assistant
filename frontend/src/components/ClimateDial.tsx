import {
  MAX_TEMPERATURE,
  MIN_TEMPERATURE,
} from "../constants";

interface ClimateDialProps {
  temperature: number;
  label: "DRIVER" | "PASSENGER";
  changed: boolean;
}

function ClimateDial({
  temperature,
  label,
  changed,
}: ClimateDialProps) {
  const percentage =
    (temperature - MIN_TEMPERATURE) /
    (MAX_TEMPERATURE - MIN_TEMPERATURE);

  const rotation = -150 + percentage * 240;

  return (
    <div
      className={`climate-dial ${
        changed ? "climate-dial-changed" : ""
      }`}
    >
      <div
        className="climate-dial-indicator"
        style={{
          transform: `rotate(${rotation}deg)`,
        }}
      >
        <span />
      </div>

      <div className="climate-dial-content">
        <strong>{temperature}°C</strong>
        <small>{label}</small>
      </div>
    </div>
  );
}

export default ClimateDial;
