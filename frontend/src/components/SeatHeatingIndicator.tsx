interface SeatHeatingIndicatorProps {
  level: number;
  side: "driver" | "passenger";
}

function SeatHeatingIndicator({
  level,
  side,
}: SeatHeatingIndicatorProps) {
  return (
    <div
      className={`seat-heating-indicator seat-heating-${side}`}
    >
      <span
        className={`seat-arc seat-arc-1 ${
          level >= 1 ? "active" : ""
        }`}
      />

      <span
        className={`seat-arc seat-arc-2 ${
          level >= 2 ? "active" : ""
        }`}
      />

      <span
        className={`seat-arc seat-arc-3 ${
          level >= 3 ? "active" : ""
        }`}
      />
    </div>
  );
}

export default SeatHeatingIndicator;