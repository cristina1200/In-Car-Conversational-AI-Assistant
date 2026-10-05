import type { VehicleState } from "../types";
import "./MediaPanel.css";

interface MediaPanelProps {
  vehicleState: VehicleState;
  onCommand: (message: string) => void;
}

function MediaPanel({
  vehicleState,
  onCommand,
}: MediaPanelProps) {
  return (
    <section className="media-panel">
      <div className="media-panel-header">
        <div>
          <span className="section-label">
            MEDIA CONTROL
          </span>

          <h2>Music player</h2>
        </div>

        <span
          className={`media-status ${
            vehicleState.is_playing
              ? "active"
              : "inactive"
          }`}
        >
          {vehicleState.is_playing
            ? "Playing"
            : "Paused"}
        </span>
      </div>

      <div className="media-player">
        <div className="album-art">♫</div>

        <div className="song-details">
          <span className="song-label">
            CURRENT SONG
          </span>

          <strong>
            {vehicleState.current_song}
          </strong>

          <small>
            {vehicleState.is_playing
              ? "Audio enabled"
              : "Playback stopped"}
          </small>
        </div>
      </div>

      <div className="media-controls">
        <button
          onClick={() =>
            onCommand(
              "Redă melodia anterioară"
            )
          }
          aria-label="Previous song"
        >
          ⏮
        </button>

        <button
          className="main-media-button"
          onClick={() =>
            onCommand(
              vehicleState.is_playing
                ? "Pune muzica pe pauză"
                : "Pornește muzica"
            )
          }
          aria-label="Play or pause"
        >
          {vehicleState.is_playing
            ? "Ⅱ"
            : "▶"}
        </button>

        <button
          onClick={() =>
            onCommand(
              "Trece la următoarea melodie"
            )
          }
          aria-label="Next song"
        >
          ⏭
        </button>
      </div>

      <div className="media-actions">
        <button
          onClick={() =>
            onCommand(
              vehicleState.is_muted
                ? "Pornește sunetul"
                : "Oprește sunetul"
            )
          }
        >
          {vehicleState.is_muted
            ? "🔇 Unmute"
            : "🔊 Mute"}
        </button>

        <div className="media-volume">
          <div className="media-volume-heading">
            <span>Volume</span>
            <strong>
              {vehicleState.volume}%
            </strong>
          </div>

          <div className="media-volume-track">
            <span
              style={{
                width: `${vehicleState.volume}%`,
              }}
            />
          </div>
        </div>
      </div>
    </section>
  );
}

export default MediaPanel;