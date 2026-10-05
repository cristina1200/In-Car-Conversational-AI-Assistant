export type Speaker =
  | "driver"
  | "passenger";

export type InputType =
  | "text"
  | "voice";

export interface VehicleState {
  temperature: {
    driver: number;
    passenger: number;
  };

  seat_heating: {
    driver: number;
    passenger: number;
  };

  fan_speed: number;
  volume: number;
  current_song: string;
  is_playing: boolean;
  is_muted: boolean;
  ambient_light: string;
  ac_enabled: boolean;
}

export interface VehicleAction {
  type: string;
  params: Record<string, unknown>;
}

export interface ConversationMessage {
  role: "user" | "assistant";
  content: string;
}

export interface AssistantRequest {
  message: string;
  speaker?: Speaker;
  input_type: InputType;
  user_id?: string | null;
  session_id?: string | null;
  history: ConversationMessage[];
  action_history: VehicleAction[];
}

export interface AssistantResponse {
  reply: string;
  actions: VehicleAction[];
  allowed: boolean;
  state: VehicleState;
  session_id: string;
  session_reset: boolean;
}

export interface VoiceIdentificationResponse {
  matched: boolean;
  user_id: string | null;
  user_name: string | null;
  confidence: number;
  enrolled_users_count: number;
  rejection_reason: string | null;
  role: SessionRole | null;
}

/* USERS */

export interface UserProfile {
  user_id: string;
  name: string;
  email: string;
  voice_enrolled: boolean;
  created_at?: string;
  profile_id?: string;
  preferences: UserPreferences;
}

export interface VoiceEnrolledUser {
  user_id: string;
  name: string;
  email: string;
  voice_enrolled: boolean;
}

export interface UserCreateRequest {
  name: string;
  email: string;
  password: string;
}
export interface UserLoginRequest {
  email: string;
  password: string;
}

export interface UserLoginRequest {
  email: string;
  password: string;
}

export interface UserResponse {
  user_id: string;
  name: string;
  email: string;
  voice_enrolled: boolean;
  created_at: string;
}

/* PREFERENCES / PROFILES */

export type AmbientLight =
  | "blue"
  | "red"
  | "green"
  | "white"
  | "purple"
  | "yellow";

export interface UserPreferences {
  profile_id?: string;
  user_id?: string;
  profile_name?: string;
  is_default?: boolean;

  /* Denumiri folosite de interfața actuală */
  temperature?: number;
  volume?: number;
  fan_speed?: number;
  ambient_light?: AmbientLight;
  seat_heating?: number;

  /* Denumiri folosite de backend */
  driver_temperature?: number;
  passenger_temperature?: number;
  driver_seat_heating?: number;
  passenger_seat_heating?: number;

  created_at?: string;
  updated_at?: string;
}

export interface ProfileCreateRequest {
  user_id: string;
  profile_name: string;

  driver_temperature: number;
  passenger_temperature: number;

  driver_seat_heating: number;
  passenger_seat_heating: number;

  fan_speed: number;
  volume: number;
  ambient_light: AmbientLight;

  is_default: boolean;
}

export interface ProfileUpdateRequest {
  profile_name?: string;
  driver_temperature?: number;
  passenger_temperature?: number;
  driver_seat_heating?: number;
  passenger_seat_heating?: number;
  fan_speed?: number;
  volume?: number;
  ambient_light?: AmbientLight;
  is_default?: boolean;
}

export interface ProfileResponse {
  profile_id: string;
  user_id: string;
  profile_name: string;
  is_default: boolean;

  driver_temperature: number;
  passenger_temperature: number;

  driver_seat_heating: number;
  passenger_seat_heating: number;

  fan_speed: number;
  volume: number;
  ambient_light: string;

  created_at: string;
  updated_at: string;
}

/* SESSIONS */

export type SessionRole =
  | "driver"
  | "passenger";

export interface SessionParticipant {
  user_id: string;
  role: SessionRole;
  session_id?: string;
  profile_id?: string | null;
  joined_at?: string;
}

export interface VehicleSession {
  session_id: string;
  participants: SessionParticipant[];

  created_by_user_id?: string;
  status?: "active" | "inactive";
  created_at?: string;
}

export interface SessionCreateRequest {
  created_by_user_id: string;
}

export interface ParticipantCreateRequest {
  user_id: string;
  role: SessionRole;
  profile_id?: string;
}

export interface ProfileActivationRequest {
  user_id: string;
  profile_id: string;
}
