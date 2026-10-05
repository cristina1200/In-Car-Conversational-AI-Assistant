import type {
  SessionRole,
  UserPreferences,
  UserProfile,
  VehicleSession,
} from "../types";

const USER_KEY =
  "in-car-ai.current-user";

const SESSION_KEY =
  "in-car-ai.current-session";

function createId(): string {
  if (
    typeof crypto !== "undefined" &&
    "randomUUID" in crypto
  ) {
    return crypto.randomUUID();
  }

  return `local-${Date.now()}-${Math.random()
    .toString(36)
    .slice(2)}`;
}

export function loadLocalUser(): UserProfile | null {
  const rawUser =
    localStorage.getItem(USER_KEY);

  if (!rawUser) {
    return null;
  }

  try {
    return JSON.parse(rawUser) as UserProfile;
  } catch {
    localStorage.removeItem(USER_KEY);
    return null;
  }
}

export function saveLocalUser(
  user: UserProfile
): void {
  localStorage.setItem(
    USER_KEY,
    JSON.stringify(user)
  );
}

export function clearAuthPersistence(): void {
  const storageTargets = [
    localStorage,
    sessionStorage,
  ];

  for (const storage of storageTargets) {
    [
      USER_KEY,
      "in-car-ai.current-role",
      "in-car-ai.session-id",
      "in-car-ai.user-id",
      "in-car-ai.voice-profile",
    ].forEach((key) => storage.removeItem(key));
  }
}

export function clearLocalUser(): void {
  localStorage.removeItem(USER_KEY);
}

export function createLocalUser(
  name: string,
  email: string,
  userId?: string
): UserProfile {
  const user: UserProfile = {
    user_id: userId ?? createId(),
    name,
    email,
    voice_enrolled: false,
    preferences: {},
  };

  saveLocalUser(user);

  return user;
}

export function updateLocalPreferences(
  user: UserProfile,
  preferences: UserPreferences
): UserProfile {
  const updatedUser: UserProfile = {
    ...user,
    preferences: {
      ...user.preferences,
      ...preferences,
    },
  };

  saveLocalUser(updatedUser);

  return updatedUser;
}

export function loadLocalSession(): VehicleSession {
  const rawSession =
    localStorage.getItem(SESSION_KEY);

  if (rawSession) {
    try {
      return JSON.parse(
        rawSession
      ) as VehicleSession;
    } catch {
      localStorage.removeItem(SESSION_KEY);
    }
  }

  const newSession: VehicleSession = {
    session_id: createId(),
    participants: [],
    status: "active",
    created_at: new Date().toISOString(),
  };

  saveLocalSession(newSession);

  return newSession;
}

export function saveLocalSession(
  session: VehicleSession
): void {
  localStorage.setItem(
    SESSION_KEY,
    JSON.stringify(session)
  );
}

export function clearLocalSession(): void {
  localStorage.removeItem(SESSION_KEY);
}

export function setLocalSessionRole(
  session: VehicleSession,
  userId: string,
  role: SessionRole
): VehicleSession {
  const otherParticipants =
    session.participants.filter(
      (participant) =>
        participant.user_id !== userId
    );

  if (role === "driver") {
    otherParticipants.forEach(
      (participant) => {
        if (participant.role === "driver") {
          participant.role = "passenger";
        }
      }
    );
  }

  const updatedSession: VehicleSession = {
    ...session,
    participants: [
      ...otherParticipants,
      {
        user_id: userId,
        role,
      },
    ],
  };

  saveLocalSession(updatedSession);

  return updatedSession;
}
