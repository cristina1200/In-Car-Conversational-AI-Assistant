export const MIN_TEMPERATURE = 16;
export const MAX_TEMPERATURE = 28;

export const MIN_VOLUME = 0;
export const MAX_VOLUME = 100;

export const MIN_FAN_SPEED = 0;
export const MAX_FAN_SPEED = 3;

export const MIN_SEAT_HEATING = 0;
export const MAX_SEAT_HEATING = 3;

export const DEFAULT_DRIVER_TEMPERATURE = 20;
export const DEFAULT_PASSENGER_TEMPERATURE = 20;
export const DEFAULT_DRIVER_SEAT_HEATING = MIN_SEAT_HEATING;
export const DEFAULT_PASSENGER_SEAT_HEATING = MIN_SEAT_HEATING;
export const DEFAULT_FAN_SPEED = 2;
export const DEFAULT_VOLUME = 50;
export const DEFAULT_AMBIENT_LIGHT = "blue" as const;
export const DEFAULT_CURRENT_SONG = "Good Vibes";
export const DEFAULT_IS_PLAYING = false;
export const DEFAULT_IS_MUTED = false;
export const DEFAULT_AC_ENABLED = true;

export const AMBIENT_COLORS = [
  { value: "blue", label: "Blue", command: "albastru" },
  { value: "red", label: "Red", command: "roșu" },
  { value: "green", label: "Green", command: "verde" },
  { value: "white", label: "White", command: "alb" },
  { value: "purple", label: "Purple", command: "mov" },
  { value: "yellow", label: "Yellow", command: "galben" },
] as const;

export const AMBIENT_COLOR_LABELS_EN: Record<string, string> =
  Object.fromEntries(
    AMBIENT_COLORS.map(({ value, label }) => [value, label])
  );

export const AMBIENT_COLOR_LABELS_RO: Record<string, string> =
  Object.fromEntries(
    AMBIENT_COLORS.map(({ value, command }) => [value, command])
  );
