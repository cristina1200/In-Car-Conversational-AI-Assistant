interface FanIndicatorProps {
  level: number;
}

function FanIndicator({ level }: FanIndicatorProps) {
  const maxLevel = 3;
  const percentage = (level / maxLevel) * 100;

  return (
    <div className="fan-indicator">
      {/* Glow peste iconița existentă în imagine */}
      <div
        className={`fan-icon-glow fan-glow-${level}`}
      />

      <div className="fan-level-track">
        <div
          className="fan-level-fill"
          style={{
            width: `${percentage}%`,
          }}
        />
      </div>

      <span className="fan-level-label">
        {level === 0 ? "OFF" : `LEVEL ${level}`}
      </span>
    </div>
  );
}

export default FanIndicator;